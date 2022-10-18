import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Union

from eth_typing import HexStr
from web3 import Web3
from web3.contract import Contract

from simple_arbitrage.markets.types.EthMarket import (
    CallDetails,
    EthMarket,
    MultipleCallData,
    ProtocolType,
)
from simple_arbitrage.utils.abi import UNISWAP_PAIR_ABI
from simple_arbitrage.utils.addresses import WETH_ADDRESS

WEB3_INFURA_PROJECT_ID = os.environ.get("WEB3_INFURA_PROJECT_ID")
provider = Web3.WebsocketProvider(
    f"wss://mainnet.infura.io/ws/v3/{WEB3_INFURA_PROJECT_ID}",
)
w3 = Web3(provider)


class UniswappyV2EthPair(EthMarket):
    uniswap_interface: Contract = w3.eth.contract(WETH_ADDRESS, abi=UNISWAP_PAIR_ABI)  # type: ignore[call-overload]

    def __init__(self, market_address: str, tokens: list[str], protocol: str):
        super().__init__(
            market_address, tokens, protocol, ProtocolType.CONSTANT_PRODUCT
        )
        self._token_balances: dict[str, float] = dict()

    def receive_directly(self, token_address: str) -> bool:
        return token_address in self._token_balances

    def prepare_receive(
        self,
        token_address: str,
        amount_in: float,
    ) -> list[CallDetails]:
        if not self._token_balances[token_address]:
            raise RuntimeError(
                f"Market does not operate on token {token_address}",
            )

        if amount_in <= 0:
            raise RuntimeError(f"Invalid amount: {amount_in}")

        # No preparation necessary
        return []

    def get_balance(self, token_address: str) -> float:
        balance = self._token_balances[token_address]
        if balance is None:
            raise RuntimeError(f"Bad token {token_address} balance is None")
        return balance

    def set_reserves_via_ordered_balances(self, balances: list[float]):
        self.set_reserves_via_matching_array(self.tokens, balances)

    def set_reserves_via_matching_array(self, tokens: list[str], balances: list[float]):
        token_balances = dict(zip(tokens, balances))
        if token_balances != self._token_balances:
            self._token_balances = token_balances

    def get_tokens_in(self, token_in: str, token_out: str, amount_out: float) -> float:
        reserve_in = self._token_balances[token_in]
        reserve_out = self._token_balances[token_out]
        return self.get_amount_in(reserve_in, reserve_out, amount_out)

    def get_tokens_out(self, token_in: str, token_out: str, amount_in: float) -> float:
        reserve_in = self._token_balances[token_in]
        reserve_out = self._token_balances[token_out]
        return self.get_amount_out(reserve_in, reserve_out, amount_in)

    def get_amount_in(
        self,
        reserve_in: float,
        reserve_out: float,
        amount_out: float,
    ) -> float:
        numerator: float = reserve_in * amount_out * 1000
        denominator: float = (reserve_out - amount_out) * 997
        return numerator / denominator + 1

    def get_amount_out(
        self,
        reserve_in: float,
        reserve_out: float,
        amount_in: float,
    ) -> float:
        amount_in_with_fee: float = amount_in * 997
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 1000) + amount_in_with_fee
        return numerator / denominator

    def sell_tokens_to_next_market(
        self, token_in: str, amount_in: float, eth_market: EthMarket
    ) -> MultipleCallData:
        if eth_market.receive_directly(token_in):
            exchange_call = self.sell_tokens(
                token_in, amount_in, eth_market.market_address
            )
            return MultipleCallData(targets=[self.market_address], data=[exchange_call])

    def sell_tokens(
        self, token_in: str, amount_in: float, recipient: str
    ) -> Union[bytes, HexStr]:

        amount_0_out = 0.0
        amount_1_out = 0.0
        if token_in == self.tokens[0]:
            token_out = self.tokens[1]
            amount_1_out = self.get_tokens_out(token_in, token_out, amount_in)

        elif token_in == self.tokens[1]:
            token_out = self.tokens[0]
            amount_0_out = self.get_tokens_out(token_in, token_out, amount_in)

        else:
            raise RuntimeError(f"Bad token input address: {token_in}")

        populated_transaction = self.uniswap_interface.functions.swap(
            int(amount_0_out), int(amount_1_out), recipient, bytes([])
        ).build_transaction()

        if populated_transaction is None or populated_transaction["data"] is None:
            raise RuntimeError("Failed to build transaction")

        return populated_transaction["data"]


@dataclass()
class GroupedMarkets:
    markets_by_token: dict[str, list[UniswappyV2EthPair]]
    all_market_pairs: Iterable[UniswappyV2EthPair]

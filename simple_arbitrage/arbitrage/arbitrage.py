import logging
from asyncio.log import logger
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Optional

import sympy
from flashbots import Flashbots
from web3 import Web3, middleware
from web3.contract import Contract
from web3.gas_strategies.time_based import construct_time_based_gas_price_strategy

from simple_arbitrage.markets.types.EthMarket import EthMarket
from simple_arbitrage.utils.addresses import WETH_ADDRESS
from simple_arbitrage.utils.util import ETHER


@dataclass()
class CrossedMarketDetails:
    profit: float
    volume: float
    token_address: str
    buy_from_market: EthMarket
    sell_to_market: EthMarket

    def __repr__(self):
        buy_tokens = self.buy_from_market.tokens
        sell_tokens = self.sell_to_market.tokens
        return (
            f"Profit: {(self.profit)} Volume: {(self.volume)}\n"
            + f"{self.buy_from_market.protocol} ({self.buy_from_market.market_address})\n"
            + f"  {buy_tokens[0]} => {buy_tokens[1]}\n"
            + f"{self.sell_to_market.protocol} ({self.sell_to_market.market_address})\n"
            + f"  {sell_tokens[0]} => {sell_tokens[1]}\n"
            + "\n"
        )


@dataclass()
class MarketsByToken:
    markets_by_token: dict[str, list[EthMarket]]


TEST_VOLUMES = [
    ETHER / 100,
    ETHER / 10,
    ETHER / 6,
    ETHER / 4,
    ETHER / 2,
    ETHER / 1,
    ETHER * 2,
    ETHER * 5,
    ETHER * 10,
]


class Arbitrage:
    def __init__(self, executor_wallet, flashbots_provider, bundle_executor_contract):
        self.executor_wallet = executor_wallet
        self.flashbots_provider: Flashbots = flashbots_provider
        self.bundle_executor_contract: Contract = bundle_executor_contract
        w3 = Web3()
        gas_price_stragegy = construct_time_based_gas_price_strategy(1)
        w3.eth.set_gas_price_strategy(gas_price_stragegy)
        w3.middleware_onion.add(middleware.time_based_cache_middleware)

    def take_crossed_markets(
        self,
        best_crossed_markets: list[CrossedMarketDetails],
        block_number: int,
        miner_reward_percentage: int,
    ):

        for best_crossed_market in best_crossed_markets:
            logging.info(f"Best Crossed Market: {best_crossed_market}\n")
            logging.info(
                f"Send this much WETH {best_crossed_market.volume}, get this much profit {best_crossed_market.profit}"
            )

            buy_calls = best_crossed_market.buy_from_market.sell_tokens_to_next_market(
                WETH_ADDRESS,
                best_crossed_market.volume,
                best_crossed_market.sell_to_market,
            )
            inter = best_crossed_market.buy_from_market.get_tokens_out(
                WETH_ADDRESS,
                best_crossed_market.token_address,
                best_crossed_market.volume,
            )
            sell_call_data = best_crossed_market.sell_to_market.sell_tokens(
                best_crossed_market.token_address,
                inter,
                self.bundle_executor_contract.address,
            )
            targets: list[str] = buy_calls.targets + [
                best_crossed_market.sell_to_market.market_address
            ]
            payloads: list[str] = buy_calls.data + [sell_call_data]
            logging.info(f"Targets: {targets}, Payloads: {payloads}")
            miner_reward = (best_crossed_market.profit * miner_reward_percentage) / 100

            transaction = self.bundle_executor_contract.functions.uniswapWeth(
                int(best_crossed_market.volume), int(miner_reward), targets, payloads
            )

            try:
                estimate_gas = transaction.estimate_gas()
                if estimate_gas > 1400000:
                    logging.info(
                        f"EstimateGas succeeded, but suspiciously large: {estimate_gas}"
                    )
                    continue

                estimate_gas * 2

            except Exception:
                logging.warning(f"Estimate gas failure for {best_crossed_market}")
                continue

            bundled_transactions = [
                {
                    "signer": self.executor_wallet,
                    "transaction": transaction.build_transaction(),
                }
            ]
            logger.info(f"Bundled transactions: {bundled_transactions}")
            signed_bundle = self.flashbots_provider.sign_bundle(bundled_transactions)
            simulation = self.flashbots_provider.simulate(
                bundled_transactions, block_number + 1
            )

            if "error" in simulation or simulation["firstRevert"] is not None:
                logger.error(
                    f"Simulation error on token {best_crossed_market.token_address}, skipping..."
                )
                continue

            logger.info(
                f"Submitting bundle, profit sent to miner: {simulation['coinbaseDiff']},\
                 effective gas price: {simulation['coinbaseDiff']/simulation['totalGasUsed']} GWEI"
            )

            for target_block_number in [block_number + 1, block_number + 2]:
                self.flashbots_provider.sendRawBundle(
                    signed_bundle, target_block_number
                )
            return


def evaluate_markets(
    markets_by_token: dict[str, list[EthMarket]],
) -> Iterable[CrossedMarketDetails]:
    """get best crossed markets for each non WETH token, sorted by profit desc"""
    best_crossed_markets: list[CrossedMarketDetails] = []

    for token_address in markets_by_token:
        markets: list[EthMarket] = markets_by_token[token_address]
        priced_markets = list(_get_priced_markets(markets, token_address))

        crossed_markets: list[tuple[EthMarket, EthMarket]] = []

        for priced_market in priced_markets:
            for pm in priced_markets:
                if pm["sell_token_price"] > priced_market["buy_token_price"]:
                    crossed_markets.append(
                        (priced_market["eth_market"], pm["eth_market"]),
                    )

        logger.info(f"crossed markets len: {len(crossed_markets)}")
        best_crossed_market: Optional[CrossedMarketDetails] = get_best_crossed_market(
            crossed_markets,
            token_address,
        )
        if best_crossed_market and best_crossed_market.profit > ETHER / 1000:
            best_crossed_markets.append(best_crossed_market)

    best_crossed_markets.sort(key=lambda x: x.profit, reverse=True)
    return best_crossed_markets


def _calc_optimal_size_and_profit(
    buy_from_market: EthMarket, sell_to_market: EthMarket, token_address: str
) -> tuple[float, float]:

    size = sympy.Symbol("size")
    tokens_out_from_buying_size = buy_from_market.get_tokens_out(
        WETH_ADDRESS,
        token_address,
        size,
    )

    proceeds_from_selling_tokens = sell_to_market.get_tokens_out(
        token_address,
        WETH_ADDRESS,
        tokens_out_from_buying_size,
    )

    objective = proceeds_from_selling_tokens - size
    obj_diff = sympy.diff(objective, size)
    result: list = sympy.solve(obj_diff, size)
    optimal_size = sympy.N(max([sympy.re(i) for i in result]))
    profit = sympy.N(objective.subs({size: optimal_size}))

    return optimal_size, profit


def get_best_crossed_market(
    crossed_markets: list[tuple[EthMarket, EthMarket]],
    token_address: str,
) -> Optional[CrossedMarketDetails]:
    """get the most profitable crossed market for a single non WETH token

    Args:
        crossed_markets (list[tuple[EthMarket, EthMarket]]): profitable crossed markets for a single non WETH token
        token_address (str): non WETH token
    """
    best_crossed_market: Optional[CrossedMarketDetails] = None

    for crossed_market in crossed_markets:
        sell_to_market = crossed_market[0]
        buy_from_market = crossed_market[1]

        optimal_size, profit = _calc_optimal_size_and_profit(
            buy_from_market, sell_to_market, token_address
        )

        if best_crossed_market:
            if profit > best_crossed_market.profit:

                best_crossed_market = CrossedMarketDetails(
                    volume=optimal_size,
                    profit=profit,
                    token_address=token_address,
                    sell_to_market=sell_to_market,
                    buy_from_market=buy_from_market,
                )
        else:

            best_crossed_market = CrossedMarketDetails(
                volume=optimal_size,
                profit=profit,
                token_address=token_address,
                sell_to_market=sell_to_market,
                buy_from_market=buy_from_market,
            )
    return best_crossed_market


def _get_priced_markets(markets: list[EthMarket], token_address: str) -> Iterable[dict]:
    for market in markets:
        yield {
            "eth_market": market,
            "buy_token_price": market.get_tokens_in(
                token_address,
                WETH_ADDRESS,
                ETHER / 100,
            ),  # how many tokens needed to get 0.01 ETH
            "sell_token_price": market.get_tokens_out(
                WETH_ADDRESS,
                token_address,
                ETHER / 100,
            ),  # how many tokens we get from 0.01 ETH - If sell > buy then profit
        }

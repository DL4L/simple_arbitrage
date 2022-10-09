from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ProtocolType(str, Enum):
    CONSTANT_PRODUCT = "constant product"


@dataclass()
class TokenBalances:
    balances: dict[str, float]


@dataclass()
class MultipleCallData:
    targets: list[str]
    data: list[str]


@dataclass()
class CallDetails:
    target: str
    data: str
    value: float


class EthMarket(ABC):
    def get_tokens(self) -> list[str]:
        return self.tokens

    def get_market_address(self) -> str:
        return self.market_address

    def get_protocol(self) -> str:
        return self.protocol

    def __init__(
        self,
        market_address: str,
        tokens: list[str],
        protocol: str,
        protocol_type: ProtocolType,
    ):
        self.market_address: str = market_address
        self.tokens: list[str] = tokens
        self.protocol: str = protocol
        self.protocol_type: ProtocolType = protocol_type

    def __repr__(self) -> str:
        return f"token 1: {self.tokens[0]}, token 2: {self.tokens[1]} protocol: {self.protocol}--{self.protocol_type}"

    @abstractmethod
    def get_tokens_out(
        self, token_in: str, token_out: str, amount_in: Decimal
    ) -> Decimal:
        ...

    @abstractmethod
    def get_tokens_in(
        self, token_in: str, token_out: str, amount_out: Decimal
    ) -> Decimal:
        ...

    @abstractmethod
    def sell_tokens_to_next_market(
        self, token_in: str, amount_in: Decimal, eth_market: EthMarket
    ) -> MultipleCallData:
        ...

    @abstractmethod
    def sell_tokens(self, token_in: str, amount_in: Decimal, recipient: str) -> str:
        ...

    @abstractmethod
    def receive_directly(self, token_address: str) -> bool:
        ...

    @abstractmethod
    def prepare_receive(
        self, token_address: str, amount_in: Decimal
    ) -> list[CallDetails]:
        ...

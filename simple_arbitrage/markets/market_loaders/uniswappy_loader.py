import logging
from collections import defaultdict
from collections.abc import Iterable
from itertools import chain

from eth_typing.evm import ChecksumAddress
from web3 import HTTPProvider, Web3

from simple_arbitrage.markets.types.uniswappy_v2_eth_pair import (
    GroupedMarkets,
    UniswappyV2EthPair,
)
from simple_arbitrage.utils.abi import UNISWAP_QUERY_ABI
from simple_arbitrage.utils.addresses import (
    UNISWAP_LOOKUP_CONTRACT_ADDRESS,
    WETH_ADDRESS,
)
from simple_arbitrage.utils.util import ETHER

logger = logging.getLogger(__name__)

# batch count limit helpful for testing, loading entire set of uniswap markets takes a long time to load
BATCH_COUNT_LIMIT = 100
UNISWAP_BATCH_SIZE = 100

# Not necessary, slightly speeds up loading initialization when we know tokens are bad
# Estimate gas will ensure we aren't submitting bad bundles, but bad tokens waste time
BLACKLIST_TOKENS = ["0xD75EA151a61d06868E31F8988D28DFE5E9df57B4"]


def _get_uniswappy_markets(
    provider: HTTPProvider,
    factory_address: ChecksumAddress,
) -> list[UniswappyV2EthPair]:
    w3 = Web3(provider)
    uniswap_query = w3.eth.contract(  # type: ignore[call-overload]
        UNISWAP_LOOKUP_CONTRACT_ADDRESS,
        abi=UNISWAP_QUERY_ABI,
    )
    market_pairs = []
    for i in range(0, BATCH_COUNT_LIMIT * UNISWAP_BATCH_SIZE, UNISWAP_BATCH_SIZE):

        pairs = uniswap_query.caller.getPairsByIndexRange(
            factory_address,
            i,
            i + UNISWAP_BATCH_SIZE,
        )
        logger.info(f"batch: {len(pairs)}")
        for token1, token2, market_address in pairs:

            if token1 == WETH_ADDRESS:
                token_address = token2
            elif token2 == WETH_ADDRESS:
                token_address = token1
            else:
                continue

            if token_address not in BLACKLIST_TOKENS:
                uniswappy_v2_eth_pair = UniswappyV2EthPair(
                    market_address,
                    [token1, token2],
                    "",
                )
                market_pairs.append(uniswappy_v2_eth_pair)

        if len(pairs) < UNISWAP_BATCH_SIZE:
            break
    logger.info(f"pairs from exchange: {len(market_pairs)}")
    return market_pairs


def _group_markets_by_token(
    pairs: Iterable[UniswappyV2EthPair],
) -> dict[str, list[UniswappyV2EthPair]]:
    markets_by_token = defaultdict(list)
    for pair in pairs:
        non_weth_token = (
            pair.tokens[1] if pair.tokens[0] == WETH_ADDRESS else pair.tokens[0]
        )
        markets_by_token[non_weth_token].append(pair)

    return markets_by_token


def _get_markets_by_token_filtered_min_weth_balance(
    pairs: Iterable[UniswappyV2EthPair],
) -> dict[str, list[UniswappyV2EthPair]]:
    filtered_pairs = [pair for pair in pairs if pair.get_balance(WETH_ADDRESS) >= ETHER]
    logger.info(f"len filtered pairs: {len(filtered_pairs)}")
    markets_by_token = _group_markets_by_token(filtered_pairs)
    return markets_by_token


def update_reserves(
    provider: HTTPProvider,
    all_market_pairs: Iterable[UniswappyV2EthPair],
):
    w3 = Web3(provider)
    uniswap_query = w3.eth.contract(  # type: ignore[call-overload]
        UNISWAP_LOOKUP_CONTRACT_ADDRESS,
        abi=UNISWAP_QUERY_ABI,
    )
    pair_addresses = [pair.market_address for pair in all_market_pairs]
    logger.info(f"Updating markets, count {len(pair_addresses)}")

    reserves: list[list[float]] = uniswap_query.caller.getReservesByPairs(
        pair_addresses,
    )

    for index, pair in enumerate(all_market_pairs):
        reserve = reserves[index]
        pair.set_reserves_via_ordered_balances([reserve[0], reserve[1]])


def get_uniswap_markets_by_token(
    provider: HTTPProvider,
    factory_addresses: list[ChecksumAddress],
) -> GroupedMarkets:
    all_pairs = [
        _get_uniswappy_markets(provider, factory_address)
        for factory_address in factory_addresses
    ]

    markets_by_token_all = _group_markets_by_token(
        chain.from_iterable(all_pairs),
    )
    markets_by_token = {
        token: markets
        for token, markets in markets_by_token_all.items()
        if len(markets) > 1
    }

    all_market_pairs = list(chain.from_iterable(markets_by_token.values()))

    update_reserves(provider, all_market_pairs)

    filtered_markets_by_token = _get_markets_by_token_filtered_min_weth_balance(
        all_market_pairs,
    )
    logger.info(f"filtered markets by token: {len(filtered_markets_by_token)}")
    return GroupedMarkets(filtered_markets_by_token, all_market_pairs)

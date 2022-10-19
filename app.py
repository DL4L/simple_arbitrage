import logging
import os
import sys

from flashbots import flashbot
from web3 import Web3
from web3._utils.filters import BlockFilter

from simple_arbitrage.arbitrage.arbitrage import Arbitrage, evaluate_markets
from simple_arbitrage.markets.market_loaders.uniswappy_loader import (
    GroupedMarkets,
    get_uniswap_markets_by_token,
    update_reserves,
)
from simple_arbitrage.utils.abi import BUNDLE_EXECUTOR_ABI
from simple_arbitrage.utils.addresses import FACTORY_ADDRESSES

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(module)-20s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

PRIVATE_KEY = os.environ.get("PRIVATE_KEY")

ETHEREUM_RPC_URL = os.environ.get("ETHEREUM_RPC_URL")
BUNDLE_EXECUTOR_ADDRESS = os.environ.get("BUNDLE_EXECUTOR_ADDRESS")

FLASHBOTS_RELAY_SIGNING_KEY = os.environ.get("FLASHBOTS_RELAY_SIGNING_KEY")


MINER_REWARD_PERCENTAGE = os.environ.get("MINER_REWARD_PERCENTAGE") or 80

# HEALTHCHECK_URL = process.env.HEALTHCHECK_URL || ""

USE_GOERLI = False

provider = Web3.WebsocketProvider(ETHEREUM_RPC_URL)
w3 = Web3(provider)


arbitrage_signing_wallet = w3.eth.account.from_key(PRIVATE_KEY)
flashbots_relay_signing_wallet = w3.eth.account.from_key(
    FLASHBOTS_RELAY_SIGNING_KEY,
)

if USE_GOERLI:
    flashbot(
        w3,
        flashbots_relay_signing_wallet,
        "https://relay-goerli.flashbots.net",
    )
else:
    flashbot(w3, flashbots_relay_signing_wallet)


def main():
    logger.info(f"Searcher Wallet Address: {arbitrage_signing_wallet}")
    logger.info(
        f"Flashbots Relay Signing Wallet Address: {flashbots_relay_signing_wallet}",
    )

    arbitrage = Arbitrage(
        arbitrage_signing_wallet,
        w3.flashbots,
        w3.eth.contract(BUNDLE_EXECUTOR_ADDRESS, abi=BUNDLE_EXECUTOR_ABI),
    )
    markets: GroupedMarkets = get_uniswap_markets_by_token(
        provider,
        FACTORY_ADDRESSES,
    )

    block_filter: BlockFilter = w3.eth.filter("latest")
    while True:
        for event in block_filter.get_new_entries():
            logger.info("NEW BLOCK")
            block_number = w3.eth.block_number
            logger.info(f"Block Number: {block_number}")

            update_reserves(provider, markets.all_market_pairs)

            best_crossed_markets = evaluate_markets(
                markets.markets_by_token,
            )

            if len(best_crossed_markets) == 0:
                logger.info("No crossed markets")
            else:
                arbitrage.take_crossed_markets(
                    best_crossed_markets, block_number, MINER_REWARD_PERCENTAGE
                )


if __name__ == "__main__":
    main()

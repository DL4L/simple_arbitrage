import logging
import os
import sys
import time

from flashbots import flashbot
from web3 import Web3

from simple_arbitrage.arbitrage.arbitrage import Arbitrage
from simple_arbitrage.markets.market_loaders.uniswappy_loader import (
    GroupedMarkets,
    get_uniswap_markets_by_token,
    update_reserves,
)
from simple_arbitrage.utils.abi import BUNDLE_EXECUTOR_ABI
from simple_arbitrage.utils.addresses import FACTORY_ADDRESSES

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

ETHEREUM_RPC_URL = os.environ["ETHEREUM_RPC_URL"]
PRIVATE_KEY = (
    os.environ.get("PRIVATE_KEY")
    or "0xb98377c4857cd336787ec5b73e79960dc624354d980c6eacc059fd3dc44f2f38"
)
WEB3_INFURA_PROJECT_ID = os.environ.get("WEB3_INFURA_PROJECT_ID")
BUNDLE_EXECUTOR_ADDRESS = (
    os.environ.get("BUNDLE_EXECUTOR_ADDRESS")
    or "0xd9145CCE52D386f254917e481eB44e9943F39138"
)

FLASHBOTS_RELAY_SIGNING_KEY = (
    os.environ.get("FLASHBOTS_RELAY_SIGNING_KEY")
    or "0xe8b8ed353a1254f2dbd194344827fe217bd30ea5de2246bcd4702516700987f5"
)

MINER_REWARD_PERCENTAGE = os.environ.get("MINER_REWARD_PERCENTAGE") or "80"

# HEALTHCHECK_URL = process.env.HEALTHCHECK_URL || ""

USE_GOERLI = False

provider = Web3.WebsocketProvider(
    f"wss://mainnet.infura.io/ws/v3/{WEB3_INFURA_PROJECT_ID}",
)
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

    block_filter = w3.eth.filter("latest")
    while True:
        for event in block_filter.get_new_entries():
            logger.info("NEW Block")
            logger.info("-" * 100)
            update_reserves(provider, markets.all_market_pairs)
            best_crossed_markets = arbitrage.evaluate_markets(
                markets.markets_by_token,
            )
            if len(best_crossed_markets) == 0:
                logger.info("No crossed markets")

            for crossed_market in best_crossed_markets:
                logger.info(crossed_market)
        time.sleep(1)


if __name__ == "__main__":
    main()

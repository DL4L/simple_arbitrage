import json
import os
import subprocess
import unittest
from collections.abc import Iterable

from web3 import Web3

from simple_arbitrage.arbitrage.arbitrage import CrossedMarketDetails, evaluate_markets
from simple_arbitrage.arbitrage.tests.util import swap_exact_eth_for_tokens
from simple_arbitrage.markets.market_loaders.uniswappy_loader import update_reserves
from simple_arbitrage.markets.types.uniswappy_v2_eth_pair import UniswappyV2EthPair
from simple_arbitrage.utils.addresses import WETH_ADDRESS
from simple_arbitrage.utils.util import ETHER

MARKET_ADDRESS = "0x0000000000000000000000000000000000000001"
TOKEN_ADDRESS_1 = "0x000000000000000000000000000000000000000a"
TOKEN_ADDRESS_2 = "0x000000000000000000000000000000000000000b"
PROTOCOL_NAME_1 = "TEST_1"
PROTOCOL_NAME_2 = "TEST_2"


class TestArbitrage(unittest.TestCase):
    def test_expected_profit_arb(self):
        """single non weth token, 1 crossed market"""
        grouped_weth_markets = [
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_1,
            ),
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_2,
            ),
        ]
        grouped_weth_markets[0].set_reserves_via_ordered_balances(
            [ETHER * 2, ETHER],
        )
        grouped_weth_markets[1].set_reserves_via_ordered_balances(
            [
                ETHER,
                ETHER,
            ]
        )
        markets_by_token = {TOKEN_ADDRESS_1: grouped_weth_markets}
        best_crossed_markets: Iterable[CrossedMarketDetails] = evaluate_markets(
            markets_by_token
        )

        self.assertAlmostEqual(
            best_crossed_markets[0].profit, 5.63065806062303e16, delta=32
        )
        self.assertAlmostEqual(
            best_crossed_markets[0].volume, 1.3734286415893498e17, delta=32
        )

    def test_expected_profit_arb_multiple_crossed_markets(self):
        """single non weth token, multiple crossed market"""
        grouped_weth_markets = [
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_1,
            ),
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_2,
            ),
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_2,
            ),
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_2,
            ),
        ]
        grouped_weth_markets[0].set_reserves_via_ordered_balances(
            [ETHER * 2, ETHER],
        )
        grouped_weth_markets[1].set_reserves_via_ordered_balances(
            [
                ETHER * 1.75,
                ETHER,
            ]
        )
        grouped_weth_markets[2].set_reserves_via_ordered_balances(
            [
                ETHER * 1.5,
                ETHER,
            ]
        )
        grouped_weth_markets[3].set_reserves_via_ordered_balances(
            [
                ETHER,
                ETHER,
            ]
        )
        markets_by_token = {TOKEN_ADDRESS_1: grouped_weth_markets}
        best_crossed_markets: Iterable[CrossedMarketDetails] = evaluate_markets(
            markets_by_token
        )

        self.assertAlmostEqual(
            best_crossed_markets[0].profit, 5.63065806062303e16, delta=32
        )
        self.assertAlmostEqual(
            best_crossed_markets[0].volume, 1.3734286415893498e17, delta=32
        )

    def test_no_expected_profit_single_token(self):
        grouped_weth_markets = [
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_1,
            ),
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_1,
            ),
        ]
        grouped_weth_markets[0].set_reserves_via_ordered_balances(
            [
                ETHER,
                ETHER,
            ]
        )
        grouped_weth_markets[1].set_reserves_via_ordered_balances(
            [
                ETHER,
                ETHER,
            ]
        )
        markets_by_token = {TOKEN_ADDRESS_1: grouped_weth_markets}
        best_crossed_markets = evaluate_markets(markets_by_token)

        self.assertEqual(best_crossed_markets, [])

    def test_expected_profit_arb_two_tokens(self):
        """two non weth tokens, 2 crossed markets"""
        grouped_weth_markets_1 = [
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_1,
            ),
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_1, WETH_ADDRESS],
                PROTOCOL_NAME_2,
            ),
        ]
        grouped_weth_markets_1[0].set_reserves_via_ordered_balances(
            [ETHER * 20, ETHER * 10],
        )
        grouped_weth_markets_1[1].set_reserves_via_ordered_balances(
            [
                ETHER * 17.5,
                ETHER * 10,
            ]
        )
        grouped_weth_markets_2 = [
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_2, WETH_ADDRESS],
                PROTOCOL_NAME_1,
            ),
            UniswappyV2EthPair(
                MARKET_ADDRESS,
                [TOKEN_ADDRESS_2, WETH_ADDRESS],
                PROTOCOL_NAME_2,
            ),
        ]
        grouped_weth_markets_2[0].set_reserves_via_ordered_balances(
            [ETHER * 550, ETHER * 100],
        )
        grouped_weth_markets_2[1].set_reserves_via_ordered_balances(
            [
                ETHER * 175,
                ETHER * 100,
            ]
        )
        markets_by_token = {
            TOKEN_ADDRESS_1: grouped_weth_markets_1,
            TOKEN_ADDRESS_2: grouped_weth_markets_2,
        }
        best_crossed_markets: Iterable[CrossedMarketDetails] = evaluate_markets(
            markets_by_token
        )

        self.assertAlmostEqual(
            best_crossed_markets[0].profit / 10**18, 14.2936196087198, places=8
        )
        self.assertAlmostEqual(
            best_crossed_markets[0].volume / 10**18, 18.623800568266198, places=8
        )
        self.assertAlmostEqual(
            best_crossed_markets[1].profit / 10**18, 0.0203216095572519, places=8
        )
        self.assertAlmostEqual(
            best_crossed_markets[1].volume / 10**18, 0.308661581182677, places=8
        )


USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
INFURA_PROJECT_ID = os.environ.get("WEB3_INFURA_PROJECT_ID")


class TestArbitrageMainnetFork(unittest.TestCase):
    def setUp(self) -> None:
        os.system("kill -15 $(lsof -ti:8545)")
        self.process = subprocess.Popen(
            [
                "ganache-cli",
                "--fork",
                f"https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}@15737814",
                "--account_keys_path",
                "simple_arbitrage/arbitrage/tests/keys.json",
                "--defaultBalanceEther",
                "10000",
            ],
            stdout=subprocess.PIPE,
        )
        while True:
            line = str(self.process.stdout.readline())
            if "error" in line.lower():
                raise RuntimeError(f"Could not fork mainnet: {line}")
            if "RPC Listening on" in line:
                break

        self.provider = Web3.HTTPProvider("http://localhost:8545")
        self.w3 = Web3(self.provider)

        with open("simple_arbitrage/arbitrage/tests/keys.json") as f:
            d = json.load(f)

        self.account: str = self.w3.toChecksumAddress(
            list(d["private_keys"].items())[0][0]
        )
        self.private_key: bytes = self.w3.toBytes(
            text=list(d["private_keys"].items())[0][1]
        )

    def tearDown(self) -> None:
        self.process.kill()

    def test_pools_unbalanced(self):

        weth_usdc_uni = UniswappyV2EthPair(
            market_address="0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc",
            tokens=[USDC, WETH_ADDRESS],
            protocol="Uniswap V2",
        )

        weth_usdc_sushi = UniswappyV2EthPair(
            market_address="0x397FF1542f962076d0BFE58eA045FfA2d347ACa0",
            tokens=[USDC, WETH_ADDRESS],
            protocol="SushiSwap",
        )

        update_reserves(
            provider=self.provider, all_market_pairs=[weth_usdc_uni, weth_usdc_sushi]
        )

        markets_by_token = {USDC: [weth_usdc_uni, weth_usdc_sushi]}
        best_crossed_markets: Iterable[CrossedMarketDetails] = evaluate_markets(
            markets_by_token
        )
        self.assertEqual(best_crossed_markets, [])

        swap_exact_eth_for_tokens(
            self.w3, weth_usdc_uni, 10**21, self.account, self.private_key
        )
        # unbalance pools with a 1000eth trade, then update reserves

        update_reserves(
            provider=self.provider, all_market_pairs=[weth_usdc_uni, weth_usdc_sushi]
        )

        best_crossed_markets: Iterable[CrossedMarketDetails] = evaluate_markets(
            markets_by_token
        )
        self.assertAlmostEqual(
            best_crossed_markets[0].profit / 10**18, 8.00918548336306, places=8
        )
        self.assertAlmostEqual(
            best_crossed_markets[0].volume / 10**18, 326.129855482162, places=8
        )

import unittest
from collections.abc import Iterable

from simple_arbitrage.arbitrage.arbitrage import CrossedMarketDetails, evaluate_markets
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
        print(best_crossed_markets)
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

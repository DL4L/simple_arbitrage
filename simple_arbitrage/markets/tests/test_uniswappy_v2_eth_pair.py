import os
import subprocess
import unittest

from web3 import Web3

from simple_arbitrage.markets.market_loaders.uniswappy_loader import update_reserves
from simple_arbitrage.markets.types.uniswappy_v2_eth_pair import UniswappyV2EthPair
from simple_arbitrage.utils.addresses import WETH_ADDRESS

USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
INFURA_PROJECT_ID = os.environ.get("WEB3_INFURA_PROJECT_ID")


class TestUniswappyPair(unittest.TestCase):
    def setUp(self) -> None:
        os.system("kill -15 $(lsof -ti:8545)")
        self.process = subprocess.Popen(
            [
                "ganache-cli",
                "--fork",
                f"https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}@15737814",
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

    def tearDown(self) -> None:
        self.process.kill()

    def test_sell_to_next_market(self):

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

        res = weth_usdc_uni.sell_tokens_to_next_market(
            WETH_ADDRESS, 10**18, weth_usdc_sushi
        )
        decoded_input = weth_usdc_uni.uniswap_interface.decode_function_input(
            res.data[0]
        )
        self.assertDictEqual(
            decoded_input[1],
            {
                "amount0Out": 1272068043,
                "amount1Out": 0,
                "to": "0x397FF1542f962076d0BFE58eA045FfA2d347ACa0",
                "data": b"",
            },
        )

import os
import time

from web3 import Web3

from simple_arbitrage.markets.types.EthMarket import EthMarket
from simple_arbitrage.utils.abi import UNISWAP_ROUTER_ABI
from simple_arbitrage.utils.addresses import UNISWAP_ROUTER_ADDRESS

WETH_ADDRESS = os.environ.get("WETH_ADDRESS")


def swap_exact_eth_for_tokens(
    w3: Web3, market: EthMarket, amount_in: int, account: str, private_key: str
):
    uniswap_router = w3.eth.contract(UNISWAP_ROUTER_ADDRESS, abi=UNISWAP_ROUTER_ABI)

    path = [WETH_ADDRESS] + [
        address for address in market.tokens if address != WETH_ADDRESS
    ]
    func = uniswap_router.functions.swapExactETHForTokens(
        0, path, account, int(time.time() + 60)
    )
    tx_params = {
        "from": account,
        "value": amount_in,
        "nonce": w3.eth.get_transaction_count(account),
    }
    transaction = func.build_transaction(tx_params)  # type: ignore[arg-type]
    signed_tx = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    return w3.eth.send_raw_transaction(signed_tx.rawTransaction)

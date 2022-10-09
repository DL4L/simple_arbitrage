from web3 import Web3

UNISWAP_LOOKUP_CONTRACT_ADDRESS = "0x5EF1009b9FCD4fec3094a5564047e190D72Bd511"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
SUSHISWAP_FACTORY_ADDRESS = "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac"
UNISWAP_FACTORY_ADDRESS = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
CRO_FACTORY_ADDRESS = "0x9DEB29c9a4c7A88a3C0257393b7f3335338D9A9D"
ZEUS_FACTORY_ADDRESS = "0xbdda21dd8da31d5bee0c9bb886c044ebb9b8906a"
LUA_FACTORY_ADDRESS = "0x0388c1e0f210abae597b7de712b9510c6c36c857"

FACTORY_ADDRESSES = [
    CRO_FACTORY_ADDRESS,
    ZEUS_FACTORY_ADDRESS,
    LUA_FACTORY_ADDRESS,
    SUSHISWAP_FACTORY_ADDRESS,
    UNISWAP_FACTORY_ADDRESS,
]

FACTORY_ADDRESSES = [
    Web3.toChecksumAddress(
        address,
    )
    for address in FACTORY_ADDRESSES
]

UNISWAP_ROUTER_ADDRESS = Web3.toChecksumAddress(
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
)
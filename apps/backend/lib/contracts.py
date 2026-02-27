"""Polymarket contract addresses and ABIs (Polygon Mainnet)."""

CONTRACTS = {
    "USDC_E": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "CTF": "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",
    "CTF_EXCHANGE": "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
    "NEG_RISK_CTF_EXCHANGE": "0xC5d563A36AE78145C45a50134d48A1215220f80a",
    "NEG_RISK_ADAPTER": "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",
    "SAFE_PROXY_FACTORY": "0xaacfeea03eb1561c4e67d661e40682bd20e3541b",
    "PROXY_WALLET_FACTORY": "0xaB45c5A4B0c941a2F231C04C3f49182e1A254052",
}

# Polygon chain ID
POLYGON_CHAIN_ID = 137

# ABI for getting proxy wallet address from CTF Exchange
PROXY_WALLET_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_addr", "type": "address"}],
        "name": "getPolyProxyWalletAddress",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
]

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]

CTF_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_operator", "type": "address"},
        ],
        "name": "isApprovedForAll",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_operator", "type": "address"},
            {"name": "_approved", "type": "bool"},
        ],
        "name": "setApprovalForAll",
        "outputs": [],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "collateralToken", "type": "address"},
            {"name": "parentCollectionId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "partition", "type": "uint256[]"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "splitPosition",
        "outputs": [],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_id", "type": "uint256"},
        ],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "collateralToken", "type": "address"},
            {"name": "parentCollectionId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "partition", "type": "uint256[]"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "mergePositions",
        "outputs": [],
        "type": "function",
    },
]

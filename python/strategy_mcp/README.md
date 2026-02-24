# Strategy MCP (Python)

Provides strategy tools for agents with live market data from Polymarket + Gnosis/Omen.

## Run MCP server

```bash
cd python/strategy_mcp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python mcp_server.py
```

## Run HTTP bridge for Fastify integration

```bash
cd python/strategy_mcp
source .venv/bin/activate
uvicorn bridge_api:app --host 0.0.0.0 --port 8787 --reload
```

## Environment variables

- `POLYMARKET_GAMMA_BASE_URL` (default: `https://gamma-api.polymarket.com`)
- `GNOSIS_OMEN_SUBGRAPH_URL` (default: `https://api.thegraph.com/subgraphs/name/protofire/omen-xdai`)

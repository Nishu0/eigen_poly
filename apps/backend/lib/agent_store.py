"""Agent store — JSON-file backed registration storage for MVP."""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


DEFAULT_STORE_PATH = os.path.expanduser("~/.eigenpoly/agents.json")


@dataclass
class Agent:
    """Registered agent record."""

    agent_id: str
    wallet_address: str
    api_key_hash: str
    polygon_safe: str
    solana_vault: str
    scopes: list[str]
    created_at: str


class AgentStore:
    """File-backed agent store. Thread-safe for single-process use."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get("AGENT_STORE_PATH", DEFAULT_STORE_PATH)
        self._agents: dict[str, Agent] = {}
        self._key_index: dict[str, str] = {}  # api_key_hash -> agent_id
        self._load()

    def _load(self) -> None:
        """Load agents from disk."""
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                for agent_id, record in data.get("agents", {}).items():
                    agent = Agent(**record)
                    self._agents[agent_id] = agent
                    self._key_index[agent.api_key_hash] = agent_id
            except (json.JSONDecodeError, KeyError):
                pass  # Start fresh if corrupt

    def _save(self) -> None:
        """Persist agents to disk."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        data = {"agents": {aid: asdict(a) for aid, a in self._agents.items()}}
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def register(
        self,
        agent_id: str,
        wallet_address: str,
        api_key_hash: str,
        polygon_safe: str = "",
        solana_vault: str = "",
    ) -> Agent:
        """Register a new agent. Raises ValueError if already exists."""
        if agent_id in self._agents:
            raise ValueError(f"Agent already registered: {agent_id}")

        agent = Agent(
            agent_id=agent_id,
            wallet_address=wallet_address.lower(),
            api_key_hash=api_key_hash,
            polygon_safe=polygon_safe,
            solana_vault=solana_vault,
            scopes=["trade", "balance", "markets"],
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._agents[agent_id] = agent
        self._key_index[api_key_hash] = agent_id
        self._save()
        return agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Lookup agent by ID."""
        return self._agents.get(agent_id)

    def get_agent_by_key_hash(self, api_key_hash: str) -> Optional[Agent]:
        """Lookup agent by hashed API key."""
        agent_id = self._key_index.get(api_key_hash)
        if agent_id:
            return self._agents.get(agent_id)
        return None

    def list_agents(self) -> list[Agent]:
        """Return all registered agents."""
        return list(self._agents.values())

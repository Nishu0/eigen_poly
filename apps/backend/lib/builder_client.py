"""Builder Relayer Client — gasless order execution via Polymarket builders.

Uses py-builder-relayer-client and py-builder-signing-sdk for
order placement through the builder relayer infrastructure.

Env vars:
  BUILDER_API_KEY      — Builder API key
  BUILDER_SECRET       — Builder API secret
  BUILDER_PASS_PHRASE  — Builder passphrase
  RELAYER_URL          — Relayer endpoint (default: https://relayer.polymarket.com)
"""

import os
from typing import Optional


def _has_builder_creds() -> bool:
    """Check if builder credentials are configured."""
    return bool(
        os.environ.get("BUILDER_API_KEY")
        and os.environ.get("BUILDER_SECRET")
        and os.environ.get("BUILDER_PASS_PHRASE")
    )


class BuilderClient:
    """Wrapper for Polymarket Builder Relayer."""

    def __init__(self, private_key: str, address: str):
        self.private_key = private_key
        self.address = address
        self._client = None

    @property
    def is_available(self) -> bool:
        """Check if builder relayer is configured."""
        return _has_builder_creds()

    def _init_client(self):
        """Initialize the builder relayer client."""
        if not self.is_available:
            raise RuntimeError("Builder credentials not configured")

        try:
            from py_builder_relayer_client import BuilderRelayerClient
        except ImportError:
            raise ImportError(
                "py-builder-relayer-client not installed. "
                "Run: pip install py-builder-relayer-client"
            )

        relayer_url = os.environ.get("RELAYER_URL", "https://relayer.polymarket.com")

        self._client = BuilderRelayerClient(
            relayer_url=relayer_url,
            chain_id=137,
            private_key=self.private_key,
            builder_api_key=os.environ["BUILDER_API_KEY"],
            builder_secret=os.environ["BUILDER_SECRET"],
            builder_pass_phrase=os.environ["BUILDER_PASS_PHRASE"],
        )

    @property
    def client(self):
        if self._client is None:
            self._init_client()
        return self._client

    def place_market_order(
        self,
        token_id: str,
        amount: float,
        side: str,  # "BUY" or "SELL"
    ) -> tuple[Optional[str], Optional[str]]:
        """Place a market order via builder relayer.

        Returns (order_id, error)
        """
        try:
            result = self.client.place_order(
                token_id=token_id,
                amount=amount,
                side=side,
            )
            order_id = result.get("orderID", str(result)[:40])
            return order_id, None
        except Exception as e:
            return None, str(e)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order via builder relayer."""
        try:
            self.client.cancel(order_id)
            return True
        except Exception:
            return False

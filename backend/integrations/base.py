"""Base integration contract. Every provider must return normalized metrics."""
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import os


@dataclass
class NormalizedMetric:
    """Provider-independent metric shape."""
    provider: str
    account_id: str
    campaign_id: Optional[str]
    date: str
    impressions: int
    clicks: int
    conversions: int
    spend: float
    revenue: float
    ctr: float
    cpc: float
    cpa: float
    roas: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IntegrationBase:
    """Base class for all provider integrations.

    Subclasses MUST implement:
      - name: str
      - required_env: list of env var names
      - fetch_metrics(account_id, since, until) -> List[NormalizedMetric]

    Demo/sandbox mode is used when credentials are missing.
    Never return synthetic data as if it were real — always flag `mode`.
    """
    name: str = "base"
    required_env: List[str] = []

    def is_configured(self) -> bool:
        return all(os.environ.get(v) for v in self.required_env)

    @property
    def mode(self) -> str:
        return "live" if self.is_configured() else "demo"

    def status(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "mode": self.mode,
            "configured": self.is_configured(),
            "required_env": self.required_env,
            "missing_env": [v for v in self.required_env if not os.environ.get(v)],
        }

    async def fetch_metrics(self, account_id: str, since: str, until: str) -> List[NormalizedMetric]:
        raise NotImplementedError

    @staticmethod
    def _normalize(provider: str, account_id: str, raw: Dict[str, Any]) -> NormalizedMetric:
        imp = int(raw.get("impressions", 0))
        clk = int(raw.get("clicks", 0))
        conv = int(raw.get("conversions", 0))
        spend = float(raw.get("spend", 0))
        rev = float(raw.get("revenue", 0))
        return NormalizedMetric(
            provider=provider,
            account_id=account_id,
            campaign_id=raw.get("campaign_id"),
            date=raw.get("date", datetime.now(timezone.utc).date().isoformat()),
            impressions=imp, clicks=clk, conversions=conv,
            spend=round(spend, 2), revenue=round(rev, 2),
            ctr=round(clk / imp * 100, 4) if imp else 0.0,
            cpc=round(spend / clk, 4) if clk else 0.0,
            cpa=round(spend / conv, 4) if conv else 0.0,
            roas=round(rev / spend, 4) if spend else 0.0,
        )

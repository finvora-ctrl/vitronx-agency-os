"""Meta (Facebook + Instagram) Marketing API integration stub.
Falls back to labeled demo/sandbox mode when META_ACCESS_TOKEN is not configured.
"""
import random
from datetime import datetime, timedelta, timezone
from typing import List
from .base import IntegrationBase, NormalizedMetric


class MetaAdsIntegration(IntegrationBase):
    name = "meta_ads"
    required_env = ["META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"]

    async def fetch_metrics(self, account_id: str, since: str, until: str) -> List[NormalizedMetric]:
        if self.is_configured():
            # Real integration would call Graph API here.
            # Kept as a hook — do not fabricate live data.
            raise NotImplementedError("Live Meta Ads API not yet wired. Contact platform team.")
        # Demo mode: labeled synthetic data
        return self._demo_metrics(account_id, since, until)

    def _demo_metrics(self, account_id: str, since: str, until: str) -> List[NormalizedMetric]:
        start = datetime.fromisoformat(since); end = datetime.fromisoformat(until)
        out: List[NormalizedMetric] = []
        d = start
        while d <= end:
            imp = random.randint(8000, 45000)
            clk = int(imp * random.uniform(0.012, 0.035))
            conv = int(clk * random.uniform(0.02, 0.09))
            spend = round(clk * random.uniform(0.8, 3.5), 2)
            rev = round(conv * random.uniform(120, 480), 2)
            out.append(self._normalize(self.name, account_id, {
                "campaign_id": "demo-meta-01", "date": d.date().isoformat(),
                "impressions": imp, "clicks": clk, "conversions": conv,
                "spend": spend, "revenue": rev,
            }))
            d += timedelta(days=1)
        return out

"""Google Ads API integration stub with demo/sandbox mode."""
import random
from datetime import datetime, timedelta
from typing import List
from .base import IntegrationBase, NormalizedMetric


class GoogleAdsIntegration(IntegrationBase):
    name = "google_ads"
    required_env = ["GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CUSTOMER_ID",
                    "GOOGLE_ADS_REFRESH_TOKEN"]

    async def fetch_metrics(self, account_id: str, since: str, until: str) -> List[NormalizedMetric]:
        if self.is_configured():
            raise NotImplementedError("Live Google Ads API not yet wired.")
        return self._demo_metrics(account_id, since, until)

    def _demo_metrics(self, account_id: str, since: str, until: str) -> List[NormalizedMetric]:
        start = datetime.fromisoformat(since); end = datetime.fromisoformat(until)
        out = []; d = start
        while d <= end:
            imp = random.randint(4000, 30000)
            clk = int(imp * random.uniform(0.02, 0.06))
            conv = int(clk * random.uniform(0.03, 0.12))
            spend = round(clk * random.uniform(1.2, 5.0), 2)
            rev = round(conv * random.uniform(150, 620), 2)
            out.append(self._normalize(self.name, account_id, {
                "campaign_id": "demo-gads-01", "date": d.date().isoformat(),
                "impressions": imp, "clicks": clk, "conversions": conv,
                "spend": spend, "revenue": rev,
            }))
            d += timedelta(days=1)
        return out

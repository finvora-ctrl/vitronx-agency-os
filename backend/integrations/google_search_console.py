"""Google Search Console integration stub."""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from .base import IntegrationBase


class GoogleSearchConsoleIntegration(IntegrationBase):
    name = "google_search_console"
    required_env = ["GSC_SITE_URL", "GOOGLE_SERVICE_ACCOUNT_JSON"]

    async def fetch_metrics(self, account_id: str, since: str, until: str) -> List[Dict[str, Any]]:
        if self.is_configured():
            raise NotImplementedError("Live GSC API not yet wired.")
        return self._demo(account_id, since, until)

    def _demo(self, account_id, since, until):
        start = datetime.fromisoformat(since); end = datetime.fromisoformat(until)
        out = []; d = start
        while d <= end:
            imp = random.randint(2000, 18000)
            clk = int(imp * random.uniform(0.015, 0.055))
            out.append({
                "provider": self.name, "account_id": account_id,
                "date": d.date().isoformat(),
                "impressions": imp, "clicks": clk,
                "ctr": round(clk / imp * 100, 3) if imp else 0,
                "avg_position": round(random.uniform(4.5, 22.0), 2),
            })
            d += timedelta(days=1)
        return out

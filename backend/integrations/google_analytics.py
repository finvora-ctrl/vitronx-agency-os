"""Google Analytics 4 integration stub with demo mode."""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from .base import IntegrationBase


class GoogleAnalyticsIntegration(IntegrationBase):
    name = "google_analytics"
    required_env = ["GA4_PROPERTY_ID", "GOOGLE_SERVICE_ACCOUNT_JSON"]

    async def fetch_metrics(self, account_id: str, since: str, until: str) -> List[Dict[str, Any]]:
        if self.is_configured():
            raise NotImplementedError("Live GA4 API not yet wired.")
        return self._demo(account_id, since, until)

    def _demo(self, account_id, since, until):
        start = datetime.fromisoformat(since); end = datetime.fromisoformat(until)
        out = []; d = start
        while d <= end:
            sessions = random.randint(400, 3200)
            users = int(sessions * random.uniform(0.6, 0.85))
            pv = int(sessions * random.uniform(1.5, 4.2))
            bounce = round(random.uniform(38, 68), 2)
            conv = int(sessions * random.uniform(0.008, 0.045))
            out.append({
                "provider": self.name, "account_id": account_id,
                "date": d.date().isoformat(), "sessions": sessions, "users": users,
                "page_views": pv, "bounce_rate": bounce, "conversions": conv,
                "avg_session_duration": round(random.uniform(45, 320), 1),
            })
            d += timedelta(days=1)
        return out

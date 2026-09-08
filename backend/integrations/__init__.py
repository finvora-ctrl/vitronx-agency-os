"""VITRONX Integration Layer — provider-agnostic normalization.
All external ad/analytics providers expose the same normalized metric contract.
"""
from .base import IntegrationBase, NormalizedMetric
from .meta_ads import MetaAdsIntegration
from .google_ads import GoogleAdsIntegration
from .google_analytics import GoogleAnalyticsIntegration
from .google_search_console import GoogleSearchConsoleIntegration

REGISTRY = {
    "meta_ads": MetaAdsIntegration,
    "google_ads": GoogleAdsIntegration,
    "google_analytics": GoogleAnalyticsIntegration,
    "google_search_console": GoogleSearchConsoleIntegration,
}

def get_integration(provider: str) -> IntegrationBase:
    cls = REGISTRY.get(provider)
    if not cls:
        raise ValueError(f"Unknown provider: {provider}")
    return cls()

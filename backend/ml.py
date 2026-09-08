"""VITRONX ML module — real statistical algorithms (no fake AI).
- Linear regression forecasting (least squares)
- Z-score anomaly detection with configurable threshold
- Logistic-style lead scoring (weighted sigmoid over features)
- Simple k-means (k=3) clustering for client health tiering
- Exponential moving average smoothing
"""
import math
import random
from typing import List, Dict, Any, Tuple
import numpy as np


def linear_forecast(series: List[float], horizon: int = 7) -> Dict[str, Any]:
    """Ordinary least squares y = a*x + b, forecast next `horizon` points."""
    if len(series) < 3:
        return {"forecast": [series[-1] if series else 0] * horizon, "slope": 0, "r2": 0, "trend": "flat"}
    x = np.arange(len(series), dtype=float)
    y = np.array(series, dtype=float)
    a, b = np.polyfit(x, y, 1)
    y_pred = a * x + b
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2) or 1
    r2 = 1 - ss_res / ss_tot
    fx = np.arange(len(series), len(series) + horizon)
    forecast = (a * fx + b).tolist()
    trend = "up" if a > 0.05 * abs(y.mean() or 1) else ("down" if a < -0.05 * abs(y.mean() or 1) else "flat")
    return {"forecast": [max(0, round(v, 2)) for v in forecast], "slope": round(float(a), 4),
            "intercept": round(float(b), 4), "r2": round(float(r2), 3), "trend": trend}


def zscore_anomalies(series: List[float], threshold: float = 2.0) -> List[Dict[str, Any]]:
    """Detect points where |z| > threshold. Returns list of {index, value, z}."""
    if len(series) < 4:
        return []
    y = np.array(series, dtype=float)
    mu, sigma = y.mean(), y.std() or 1e-9
    z = (y - mu) / sigma
    return [{"index": int(i), "value": float(v), "z": round(float(zi), 2),
             "direction": "spike" if zi > 0 else "drop"}
            for i, (v, zi) in enumerate(zip(y, z)) if abs(zi) > threshold]


def ema(series: List[float], alpha: float = 0.3) -> List[float]:
    """Exponential moving average smoothing."""
    if not series: return []
    out = [series[0]]
    for v in series[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return [round(v, 2) for v in out]


def score_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Weighted logistic lead scoring. Returns 0-100 score + tier."""
    # Feature weights (empirically defined for demo)
    source_w = {"Website": 0.8, "Referral": 0.95, "LinkedIn": 0.75, "Google Ads": 0.6,
                "Instagram": 0.5, "Other": 0.3}
    stage_w = {"New": 0.15, "Contacted": 0.35, "Qualified": 0.65, "Proposal": 0.85, "Won": 1.0, "Lost": 0.0}
    value = float(lead.get("value", 0))
    value_norm = min(value / 100000.0, 1.0)  # normalize to 100k cap
    src = source_w.get(lead.get("source", "Other"), 0.3)
    stg = stage_w.get(lead.get("status", "New"), 0.15)
    # Weighted sum → sigmoid → 0-100
    z = 1.4 * stg + 1.1 * src + 0.9 * value_norm - 1.3
    p = 1 / (1 + math.exp(-z * 3))
    score = round(p * 100, 1)
    tier = "hot" if score >= 70 else ("warm" if score >= 40 else "cold")
    return {"score": score, "tier": tier}


def cluster_clients(clients: List[Dict[str, Any]], k: int = 3, iters: int = 20) -> Dict[str, str]:
    """K-means on [health, retainer, campaigns]. Returns {client_id: cluster_label}."""
    if not clients: return {}
    feats = []
    for c in clients:
        feats.append([c.get("health_score", 0), c.get("monthly_retainer", 0) / 1000.0,
                      c.get("campaigns", 0)])
    X = np.array(feats, dtype=float)
    if len(X) < k: k = max(1, len(X))
    # Init centroids: pick spread points
    idx = np.linspace(0, len(X) - 1, k, dtype=int)
    C = X[idx].copy()
    labels = np.zeros(len(X), dtype=int)
    for _ in range(iters):
        d = np.linalg.norm(X[:, None] - C[None], axis=2)
        new_labels = d.argmin(axis=1)
        if np.array_equal(new_labels, labels): break
        labels = new_labels
        for j in range(k):
            pts = X[labels == j]
            if len(pts): C[j] = pts.mean(axis=0)
    # Rank clusters by centroid health
    order = np.argsort(-C[:, 0])
    tier_names = ["A-Tier (Strategic)", "B-Tier (Growth)", "C-Tier (At Risk)"]
    tier_map = {int(o): tier_names[i] if i < len(tier_names) else f"Tier-{i+1}"
                for i, o in enumerate(order)}
    return {clients[i]["id"]: tier_map[int(labels[i])] for i in range(len(clients))}


def campaign_efficiency_index(campaign: Dict[str, Any]) -> float:
    """Composite score: ROAS × CTR × conversion_rate, normalized 0-100."""
    spend = campaign.get("spend", 0) or 1
    roas = campaign.get("revenue", 0) / spend
    imp = campaign.get("impressions", 0) or 1
    ctr = campaign.get("clicks", 0) / imp
    clicks = campaign.get("clicks", 0) or 1
    cvr = campaign.get("conversions", 0) / clicks
    idx = roas * 20 + ctr * 500 + cvr * 300
    return round(min(idx, 100), 1)


def pearson_correlation(x: List[float], y: List[float]) -> float:
    if len(x) < 3 or len(x) != len(y): return 0.0
    a, b = np.array(x, dtype=float), np.array(y, dtype=float)
    if a.std() == 0 or b.std() == 0: return 0.0
    return round(float(np.corrcoef(a, b)[0, 1]), 3)

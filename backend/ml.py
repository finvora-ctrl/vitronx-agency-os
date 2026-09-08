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
from datetime import datetime, timezone
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


# ---------- Creative Intelligence ----------
# Feature extraction from creative metadata + historical similarity
CTA_KEYWORDS = ["shop now","buy now","learn more","sign up","get started","book now",
                "download","try free","order now","claim","subscribe","join","tap","swipe"]
OFFER_KEYWORDS = ["off","free","discount","save","% off","limited","today","sale","bogo",
                  "flat","upto","hurry","last chance","exclusive","bonus"]

def extract_creative_features(creative: Dict[str, Any]) -> Dict[str, float]:
    """Extract structured features from a creative record."""
    caption = (creative.get("caption") or "").lower()
    text_blob = f"{caption} {(creative.get('cta') or '').lower()} {(creative.get('offer') or '').lower()}"
    has_cta = 1.0 if any(k in text_blob for k in CTA_KEYWORDS) or creative.get("cta") else 0.0
    has_offer = 1.0 if any(k in text_blob for k in OFFER_KEYWORDS) or creative.get("offer") else 0.0
    caption_len = len(caption)
    # Ideal caption length curve (peak ~120 chars)
    caption_score = max(0.0, 1.0 - abs(caption_len - 120) / 300.0)
    hashtag_count = (creative.get("hashtags") or "").count("#")
    hashtag_score = min(hashtag_count / 8.0, 1.0)  # 8 hashtags = optimal
    # Content type weights (Reels/Video outperform on IG)
    type_w = {"Reel": 1.0, "Video": 0.95, "Carousel": 0.85, "Story": 0.7,
              "Social Post": 0.6, "Ad Creative": 0.75, "Blog": 0.55}
    ct_score = type_w.get(creative.get("content_type", "Social Post"), 0.6)
    # Platform × objective fit
    plat_obj_map = {
        ("Instagram","Awareness"): 0.95, ("Instagram","Engagement"): 0.98,
        ("Instagram","Conversions"): 0.7, ("Instagram","Lead Generation"): 0.75,
        ("Facebook","Conversions"): 0.9, ("Facebook","Lead Generation"): 0.88,
        ("LinkedIn","Lead Generation"): 0.95, ("LinkedIn","Awareness"): 0.75,
        ("YouTube","Awareness"): 0.92, ("YouTube","Traffic"): 0.85,
    }
    po_fit = plat_obj_map.get((creative.get("platform","Instagram"), creative.get("objective","Awareness")), 0.7)
    return {
        "has_cta": has_cta, "has_offer": has_offer,
        "caption_len_score": round(caption_score, 3),
        "hashtag_score": round(hashtag_score, 3),
        "content_type_score": round(ct_score, 3),
        "platform_objective_fit": round(po_fit, 3),
    }


def score_creative(creative: Dict[str, Any], historical: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Predict CTR / engagement / conversion potential from features + historical similarity.
    Returns full explainable scoring dict. NOT a guarantee — clearly labeled as prediction.
    """
    f = extract_creative_features(creative)
    historical = historical or []

    # Historical similarity: find creatives with same content_type + platform and average their actual CTR
    similar = [h for h in historical
               if h.get("content_type") == creative.get("content_type")
               and h.get("platform") == creative.get("platform")
               and h.get("actual_ctr") is not None]
    if similar:
        avg_hist_ctr = float(np.mean([h["actual_ctr"] for h in similar]))
        avg_hist_eng = float(np.mean([h.get("actual_engagement", 3.0) for h in similar]))
        similarity_count = len(similar)
        similarity_score = min(similarity_count / 8.0, 1.0)
    else:
        avg_hist_ctr, avg_hist_eng = 2.0, 3.5
        similarity_score = 0.15  # low confidence without history

    # Predicted CTR: weighted combo of features + historical anchor
    predicted_ctr = round(
        avg_hist_ctr *
        (0.55 + 0.20 * f["has_cta"] + 0.10 * f["has_offer"] + 0.10 * f["content_type_score"] + 0.10 * f["platform_objective_fit"]),
        2
    )
    predicted_engagement = round(
        avg_hist_eng *
        (0.60 + 0.15 * f["content_type_score"] + 0.10 * f["caption_len_score"] +
         0.10 * f["hashtag_score"] + 0.10 * f["platform_objective_fit"]),
        2
    )
    # Conversion potential: driven by CTA, offer, platform×objective
    conv_score = round(100 * (0.20 + 0.35 * f["has_cta"] + 0.20 * f["has_offer"] + 0.25 * f["platform_objective_fit"]), 1)

    # Audience fit: platform_objective_fit + caption suitability
    audience_fit = round(100 * (0.4 * f["platform_objective_fit"] + 0.3 * f["caption_len_score"] +
                                0.15 * f["hashtag_score"] + 0.15 * f["content_type_score"]), 1)

    # Composite creative score (0-100)
    composite = round(
        (min(predicted_ctr / 5.0, 1.0) * 25 +
         min(predicted_engagement / 8.0, 1.0) * 20 +
         (conv_score / 100.0) * 25 +
         (audience_fit / 100.0) * 15 +
         similarity_score * 15),
        1
    )
    # Confidence: mainly driven by historical volume
    confidence = round(35 + similarity_score * 55 + f["platform_objective_fit"] * 10, 1)

    # Explainable reasons
    reasons = []
    if f["has_cta"]: reasons.append("Clear call-to-action detected — CTAs historically lift CTR ~18%")
    else: reasons.append("No explicit CTA — adding one could lift click-through")
    if f["has_offer"]: reasons.append("Offer/incentive present — drives conversion")
    if f["content_type_score"] >= 0.85: reasons.append(f"{creative.get('content_type')} format ranks top-tier on {creative.get('platform')}")
    if f["platform_objective_fit"] >= 0.9: reasons.append(f"Excellent platform-objective fit ({creative.get('platform')} × {creative.get('objective','Awareness')})")
    if similarity_count := len(similar):
        reasons.append(f"{similarity_count} similar historical creative(s) averaged {avg_hist_ctr:.2f}% CTR")
    if f["caption_len_score"] < 0.5:
        reasons.append("Caption length is far from optimal (~120 chars sweet spot)")
    if f["hashtag_score"] < 0.4:
        reasons.append("Low hashtag count — 5-8 relevant tags recommended")

    tier = "high" if composite >= 80 else ("medium" if composite >= 60 else "low")
    return {
        "features": f,
        "predicted_ctr": predicted_ctr,
        "predicted_engagement": predicted_engagement,
        "conversion_potential": conv_score,
        "audience_fit_score": audience_fit,
        "historical_similarity": round(similarity_score * 100, 1),
        "similar_creatives_count": len(similar),
        "composite_score": composite,
        "confidence": confidence,
        "performance_tier": tier,
        "reasons": reasons,
        "model_name": "vitronx-creative-v1",
        "model_version": "1.0.0",
    }


def rank_creatives(creatives: List[Dict[str, Any]], historical: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Score all creatives; return sorted by composite_score desc with winner flag."""
    scored = []
    for c in creatives:
        s = score_creative(c, historical)
        scored.append({**c, **s})
    scored.sort(key=lambda x: -x["composite_score"])
    if scored:
        scored[0]["winner"] = True
    return scored


def compute_ab_winner(variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Given A/B variants with actual metrics, decide winner using confidence heuristic.
    Uses relative uplift + sample size to gate the recommendation."""
    if len(variants) < 2:
        return {"winner_id": None, "confidence": 0, "reason": "Need at least 2 variants"}
    # Rank by ROAS (fallback: CTR, conversions)
    def key(v):
        if v.get("actual_spend", 0) > 0:
            return v.get("actual_revenue", 0) / v["actual_spend"]
        return v.get("actual_ctr", 0)
    sorted_v = sorted(variants, key=key, reverse=True)
    winner, runner = sorted_v[0], sorted_v[1]
    w_metric = key(winner); r_metric = key(runner)
    if r_metric == 0:
        uplift = 100.0 if w_metric else 0.0
    else:
        uplift = ((w_metric - r_metric) / r_metric) * 100
    total_impressions = sum(v.get("actual_impressions", 0) for v in variants)
    # Confidence: needs uplift > 10% AND meaningful sample size
    if total_impressions < 5000:
        confidence = 30
        verdict = "insufficient_data"
    elif abs(uplift) < 5:
        confidence = 50
        verdict = "inconclusive"
    elif abs(uplift) < 15:
        confidence = 70
        verdict = "likely_winner"
    else:
        confidence = 90
        verdict = "clear_winner"
    return {
        "winner_id": winner.get("id"),
        "winner_name": winner.get("name"),
        "uplift_pct": round(uplift, 2),
        "verdict": verdict,
        "confidence": confidence,
        "total_impressions": total_impressions,
        "primary_metric": "ROAS" if any(v.get("actual_spend", 0) > 0 for v in variants) else "CTR",
    }


def prediction_error_stats(pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Given [{predicted, actual}] pairs, compute MAE, MAPE, avg error."""
    if not pairs: return {"mae": 0, "mape": 0, "samples": 0, "avg_error": 0}
    pred = np.array([p["predicted"] for p in pairs], dtype=float)
    act = np.array([p["actual"] for p in pairs], dtype=float)
    mae = float(np.mean(np.abs(pred - act)))
    mask = act != 0
    mape = float(np.mean(np.abs((pred[mask] - act[mask]) / act[mask])) * 100) if mask.any() else 0.0
    return {"mae": round(mae, 3), "mape": round(mape, 2),
            "samples": len(pairs), "avg_predicted": round(float(pred.mean()), 3),
            "avg_actual": round(float(act.mean()), 3),
            "avg_error": round(float((pred - act).mean()), 3)}


def compute_client_risk(client: Dict[str, Any], campaigns: List[Dict[str, Any]],
                         tasks: List[Dict[str, Any]], content: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Rule-based risk scoring with transparent drivers."""
    drivers = []
    risk_points = 0

    # Health score bucket
    health = client.get("health_score", 75)
    if health < 60:
        risk_points += 30; drivers.append({"factor": "Client Health critical", "detail": f"Health = {health}/100", "weight": 30})
    elif health < 75:
        risk_points += 15; drivers.append({"factor": "Client Health below healthy", "detail": f"Health = {health}/100", "weight": 15})

    # ROAS
    active = [c for c in campaigns if c.get("status") == "Active"]
    total_spend = sum(c.get("spend", 0) for c in active)
    total_rev = sum(c.get("revenue", 0) for c in active)
    roas = total_rev / total_spend if total_spend else 0
    if total_spend > 5000 and roas < 1.5:
        risk_points += 25
        drivers.append({"factor": "Poor ROAS", "detail": f"Blended ROAS {roas:.2f}x on ${total_spend:,.0f} spend", "weight": 25})
    elif total_spend > 5000 and roas < 2.5:
        risk_points += 10
        drivers.append({"factor": "ROAS below target", "detail": f"Blended ROAS {roas:.2f}x", "weight": 10})

    # Overdue tasks
    now = datetime.now(timezone.utc)
    overdue = [t for t in tasks if t.get("status") != "Completed" and t.get("due_date") and
               datetime.fromisoformat(t["due_date"].replace("Z","+00:00")) < now]
    if len(overdue) >= 5:
        risk_points += 20; drivers.append({"factor": "Overdue tasks", "detail": f"{len(overdue)} tasks past due", "weight": 20})
    elif len(overdue) >= 2:
        risk_points += 10; drivers.append({"factor": "Overdue tasks", "detail": f"{len(overdue)} tasks past due", "weight": 10})

    # Pending approvals
    pending = [c for c in content if c.get("status") == "Client Review"]
    if len(pending) >= 4:
        risk_points += 15; drivers.append({"factor": "Approval backlog", "detail": f"{len(pending)} items awaiting approval", "weight": 15})
    elif len(pending) >= 2:
        risk_points += 5; drivers.append({"factor": "Approvals pending", "detail": f"{len(pending)} items", "weight": 5})

    # Content pipeline coverage
    scheduled = sum(1 for c in content if c.get("status") in ("Scheduled","Approved","Published"))
    if scheduled < 3:
        risk_points += 10; drivers.append({"factor": "Thin content pipeline", "detail": f"Only {scheduled} scheduled/approved items", "weight": 10})

    # Level
    if risk_points >= 45: level = "critical"
    elif risk_points >= 25: level = "high"
    elif risk_points >= 12: level = "medium"
    else: level = "low"

    # Intervention
    intervention = None
    if level in ("critical","high"):
        intervention = "Schedule an account review call this week; prioritize approval-dependent content and pause underperforming campaigns."
    elif level == "medium":
        intervention = "Clear approval backlog, address top overdue tasks, and review ROAS on active campaigns."
    else:
        intervention = "Client is stable — continue monitoring key metrics."

    return {
        "risk_score": risk_points, "risk_level": level,
        "drivers": drivers, "intervention": intervention,
        "metrics": {"roas": round(roas, 2), "spend": total_spend, "revenue": total_rev,
                    "overdue_tasks": len(overdue), "pending_approvals": len(pending),
                    "scheduled_content": scheduled, "health_score": health}
    }

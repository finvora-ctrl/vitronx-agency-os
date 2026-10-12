"""ML Learning Lab: chronological training, honest evaluation, explanations. Pure functions (no DB)."""
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from ml import _creative_to_features

CTR_FEATURES = ["platform", "content_type", "objective", "has_cta", "has_offer",
                "caption_len_score", "hashtag_score", "content_type_score",
                "platform_objective_fit", "caption_chars", "hashtag_count"]
LEAD_SOURCES = ["Website", "Referral", "LinkedIn", "Google Ads", "Instagram", "Other"]
LEAD_FEATURES = [f"source_{s.replace(' ', '_').lower()}" for s in LEAD_SOURCES] + ["value_log", "has_email", "has_phone"]
MIN_TRAIN = {"ctr_rf": 12, "lead_lr": 12}
READY_TEST_N = 30

ACTIVE: Dict[str, Dict[str, Any]] = {"ctr_rf": {}, "lead_lr": {}}


def _ts(r):
    return r.get("created_at") or ""


def ctr_vector(c):
    return [float(v) for v in _creative_to_features(c)]


def lead_vector(l):
    src = l.get("source") if l.get("source") in LEAD_SOURCES else "Other"
    onehot = [1.0 if s == src else 0.0 for s in LEAD_SOURCES]
    return onehot + [math.log1p(float(l.get("value") or 0)), 1.0 if l.get("email") else 0.0, 1.0 if l.get("phone") else 0.0]


def chrono_split(rows, test_frac=0.25):
    rows = sorted(rows, key=_ts)
    n_test = max(3, int(round(len(rows) * test_frac)))
    return rows[:-n_test], rows[-n_test:]


def _range(rows):
    ts = sorted(_ts(r) for r in rows if _ts(r))
    return {"from": ts[0] if ts else None, "to": ts[-1] if ts else None}


def _warnings(n_total, n_test):
    w = []
    if n_test < READY_TEST_N:
        w.append(f"Only {n_test} test records — metrics are unstable and NOT evidence of real-world accuracy.")
    if n_total < 100:
        w.append(f"Small dataset ({n_total} usable records). Collect more labelled outcomes before relying on predictions.")
    return w


def regression_metrics(y, yhat):
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    y, yhat = np.array(y, float), np.array(yhat, float)
    return {"n": int(len(y)), "mae": round(float(mean_absolute_error(y, yhat)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y, yhat))), 4),
            "r2": round(float(r2_score(y, yhat)), 4) if len(y) > 2 else None}


def classification_metrics(y, proba, threshold=0.5):
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score
    y = np.array(y, int); proba = np.array(proba, float); yp = (proba >= threshold).astype(int)
    auc = round(float(roc_auc_score(y, proba)), 3) if len(set(y.tolist())) == 2 else None
    return {"n": int(len(y)), "accuracy": round(float(accuracy_score(y, yp)), 3),
            "precision": round(float(precision_score(y, yp, zero_division=0)), 3),
            "recall": round(float(recall_score(y, yp, zero_division=0)), 3),
            "f1": round(float(f1_score(y, yp, zero_division=0)), 3), "roc_auc": auc,
            "confusion_matrix": confusion_matrix(y, yp, labels=[0, 1]).tolist()}


def readiness(kind, m):
    if m.get("status") == "insufficient_data":
        return "insufficient_data"
    ok = (m.get("r2") or 0) > 0.3 and m["mae"] < m["baseline_lr"]["mae"] if kind == "ctr_rf" else (m.get("roc_auc") or 0) >= 0.7
    return "ready_for_cautious_use" if ok and m["test_records"] >= READY_TEST_N else "evaluated"


def train_ctr(records):
    from sklearn.ensemble import RandomForestRegressor
    valid = [r for r in records if r.get("actual_ctr") is not None and (r.get("actual_impressions") or 0) > 0]
    if len(valid) < MIN_TRAIN["ctr_rf"]:
        return {"status": "insufficient_data", "total_samples": len(valid), "min_required": MIN_TRAIN["ctr_rf"]}
    tr, te = chrono_split(valid)
    Xtr = np.array([ctr_vector(r) for r in tr]); ytr = np.array([r["actual_ctr"] for r in tr])
    Xte = np.array([ctr_vector(r) for r in te]); yte = np.array([r["actual_ctr"] for r in te])
    model = RandomForestRegressor(n_estimators=80, max_depth=6, random_state=42, n_jobs=1).fit(Xtr, ytr)
    m = regression_metrics(yte, model.predict(Xte))
    base = regression_metrics(yte, np.full(len(yte), ytr.mean()))
    imp = sorted([{"feature": CTR_FEATURES[i], "importance": round(float(v), 4)}
                  for i, v in enumerate(model.feature_importances_)], key=lambda x: -x["importance"])
    metrics = {"algorithm": "RandomForestRegressor(n_estimators=80, max_depth=6, random_state=42)",
               "validation": "chronological split by created_at (oldest 75% train, newest 25% test)",
               "train_records": len(tr), "test_records": len(te), "mae": m["mae"], "rmse": m["rmse"], "r2": m["r2"],
               "baseline_lr": {"name": "train-mean predictor", "mae": base["mae"], "r2": base["r2"]}}
    return {"status": "trained", "model": model, "metrics": metrics, "importance": imp,
            "train_ids": [r["id"] for r in tr], "test_ids": [r["id"] for r in te],
            "x_median": np.median(Xtr, axis=0).tolist(), "train_range": _range(tr), "test_range": _range(te),
            "total_samples": len(valid), "warnings": _warnings(len(valid), len(te))}


def train_lead(records):
    from sklearn.linear_model import LogisticRegression
    valid = [r for r in records if r.get("status") in ("Won", "Lost")]
    if len(valid) < MIN_TRAIN["lead_lr"]:
        return {"status": "insufficient_data", "total_samples": len(valid), "min_required": MIN_TRAIN["lead_lr"],
                "note": f"Need at least {MIN_TRAIN['lead_lr']} Won/Lost labelled leads."}
    tr, te = chrono_split(valid)
    ytr = [1 if r["status"] == "Won" else 0 for r in tr]; yte = [1 if r["status"] == "Won" else 0 for r in te]
    if len(set(ytr)) < 2:
        return {"status": "insufficient_data", "total_samples": len(valid), "note": "Training window needs both Won and Lost leads."}
    Xtr = np.array([lead_vector(r) for r in tr]); Xte = np.array([lead_vector(r) for r in te])
    model = LogisticRegression(max_iter=500, class_weight="balanced").fit(Xtr, ytr)
    m = classification_metrics(yte, model.predict_proba(Xte)[:, 1])
    maj = 1 if sum(ytr) * 2 >= len(ytr) else 0
    metrics = {"algorithm": "LogisticRegression(class_weight=balanced, max_iter=500)",
               "validation": "chronological split by created_at (oldest 75% train, newest 25% test)",
               "train_records": len(tr), "test_records": len(te),
               **{k: m[k] for k in ("accuracy", "precision", "recall", "f1", "roc_auc", "confusion_matrix")},
               "baseline_majority_accuracy": round(sum(1 for v in yte if v == maj) / len(yte), 3),
               "coefficients": dict(zip(LEAD_FEATURES, [round(float(c), 3) for c in model.coef_[0]]))}
    return {"status": "trained", "model": model, "metrics": metrics,
            "train_ids": [r["id"] for r in tr], "test_ids": [r["id"] for r in te],
            "x_mean": Xtr.mean(axis=0).tolist(), "train_range": _range(tr), "test_range": _range(te),
            "total_samples": len(valid), "warnings": _warnings(len(valid), len(te))}


def refit(kind, train_rows):
    """Rebuild an archived model version exactly from its stored training record ids."""
    rows = sorted(train_rows, key=_ts)
    if kind == "ctr_rf":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(n_estimators=80, max_depth=6, random_state=42, n_jobs=1).fit(
            np.array([ctr_vector(r) for r in rows]), np.array([r["actual_ctr"] for r in rows]))
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(max_iter=500, class_weight="balanced").fit(
        np.array([lead_vector(r) for r in rows]), [1 if r["status"] == "Won" else 0 for r in rows])


def should_promote(kind, cand, active_meta):
    m = cand["metrics"]
    if kind == "ctr_rf":
        if m["mae"] >= m["baseline_lr"]["mae"]:
            return False, "Candidate does not beat the train-mean baseline MAE."
        if active_meta and m["mae"] > active_meta["metrics"]["mae"] * 1.05:
            return False, f"Candidate MAE {m['mae']} worse than active {active_meta['metrics']['mae']} (+5% tolerance)."
    else:
        if active_meta and m["f1"] < active_meta["metrics"]["f1"] - 0.02:
            return False, f"Candidate F1 {m['f1']} worse than active {active_meta['metrics']['f1']}."
    return True, "Passed evaluation gate."


def activate(kind, model, meta):
    ACTIVE[kind] = {"model": model, "meta": meta}


def predict_ctr(c) -> Optional[Dict[str, Any]]:
    a = ACTIVE["ctr_rf"]
    if not a:
        return None
    return {"predicted_ctr_rf": round(max(float(a["model"].predict(np.array([ctr_vector(c)]))[0]), 0), 3),
            "model_version": a["meta"]["version"], "trained_at": a["meta"]["trained_at"]}


def predict_lead(l) -> Optional[Dict[str, Any]]:
    a = ACTIVE["lead_lr"]
    if not a:
        return None
    p = float(a["model"].predict_proba(np.array([lead_vector(l)]))[0][1])
    return {"conversion_probability": round(p * 100, 1), "tier": "HOT" if p >= 0.7 else ("WARM" if p >= 0.4 else "COLD"),
            "model_version": a["meta"]["version"]}


def explain_ctr(c):
    a = ACTIVE["ctr_rf"]
    if not a:
        return None
    x = ctr_vector(c); base = float(a["model"].predict(np.array([x]))[0]); med = a["meta"]["x_median"]
    contrib = []
    for i, name in enumerate(CTR_FEATURES):
        x2 = list(x); x2[i] = med[i]
        contrib.append({"feature": name, "value": x[i], "training_median": med[i],
                        "effect_pp": round(base - float(a["model"].predict(np.array([x2]))[0]), 3)})
    contrib.sort(key=lambda r: -abs(r["effect_pp"]))
    return {"prediction": round(base, 3), "unit": "CTR %", "method":
            "Local sensitivity: each feature is replaced by its training median and the change in predicted CTR is reported. "
            "This shows association learned by the model, not causation.", "contributions": contrib}


def explain_lead(l):
    a = ACTIVE["lead_lr"]
    if not a:
        return None
    x = lead_vector(l); coefs = a["meta"]["metrics"]["coefficients"]; mean = a["meta"]["x_mean"]
    contrib = [{"feature": f, "value": round(x[i], 3), "training_mean": round(mean[i], 3),
                "log_odds_effect": round(coefs[f] * (x[i] - mean[i]), 3)} for i, f in enumerate(LEAD_FEATURES)]
    contrib.sort(key=lambda r: -abs(r["log_odds_effect"]))
    p = predict_lead(l)
    return {**p, "method": "Logistic regression: effect = coefficient × (lead value − training mean) in log-odds. "
            "Tier thresholds: HOT ≥70%, WARM ≥40%, else COLD. Pipeline stage is deliberately excluded to avoid label leakage.",
            "contributions": contrib}


def now_iso():
    return datetime.now(timezone.utc).isoformat()

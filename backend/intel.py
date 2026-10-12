"""Campaign Doctor, ML Learning Lab, Model Transparency, Recommendations and AI Buddy chat."""
import hashlib
import json
import math
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import ml_lab
from ml import zscore_anomalies, compute_client_risk

AGENCY_FIN_ROLES = ("agency_admin", "account_manager", "super_admin")
AGENCY_ROLES = ("agency_admin", "account_manager", "designer", "marketer", "super_admin")
OWNER_ROLE = {"ctr_drop": "designer", "creative_fatigue": "designer", "cpc_increase": "marketer",
              "conversion_decline": "account_manager", "unusual_spend": "marketer", "underperforming": "account_manager"}


def _fv(v, u):
    return f"₹{v}" if u == "₹" else f"{v}{u}"


def _today():
    return datetime.now(timezone.utc).date()


def _welch_t(a, b):
    a, b = np.array(a, float), np.array(b, float)
    if len(a) < 2 or len(b) < 2:
        return 0.0
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float((a.mean() - b.mean()) / se) if se > 0 else 0.0


def _agg(rows):
    imp = sum(r["impressions"] for r in rows); clk = sum(r["clicks"] for r in rows)
    sp = sum(r["spend"] for r in rows); cv = sum(r["conversions"] for r in rows); rev = sum(r.get("revenue", 0) for r in rows)
    return {"impressions": imp, "clicks": clk, "spend": round(sp, 2), "conversions": cv, "revenue": round(rev, 2),
            "ctr": round(clk / imp * 100, 3) if imp else None, "cpc": round(sp / clk, 2) if clk else None,
            "cvr": round(cv / clk * 100, 3) if clk else None, "cpa": round(sp / cv, 2) if cv else None,
            "roas": round(rev / sp, 2) if sp else None, "avg_daily_spend": round(sp / len(rows), 2) if rows else 0, "days": len(rows)}


def _daily(rows, m):
    out = []
    for r in rows:
        if m == "ctr" and r["impressions"]: out.append(r["clicks"] / r["impressions"] * 100)
        elif m == "cpc" and r["clicks"]: out.append(r["spend"] / r["clicks"])
        elif m == "cvr" and r["clicks"]: out.append(r["conversions"] / r["clicks"] * 100)
        elif m == "spend": out.append(r["spend"])
    return out


def _conf(t, n_recent, n_base):
    a = abs(t)
    if a >= 3.5 and n_recent >= 7 and n_base >= 21: return "high"
    if a >= 2.5 and n_base >= 14: return "medium"
    return "low"


def analyze_campaign(c, rows):
    """Deterministic baseline-vs-recent diagnosis for one campaign."""
    rows = sorted(rows, key=lambda r: r["date"])
    base_out = {"campaign_id": c["id"], "campaign_name": c["name"], "platform": c.get("platform"), "status": c.get("status"),
                "series": [{"date": r["date"], "ctr": round(r["clicks"] / r["impressions"] * 100, 3) if r["impressions"] else None,
                            "spend": r["spend"]} for r in rows[-35:]],
                "data_sources": sorted({r.get("data_source", "unknown") for r in rows})}
    if len(rows) < 14:
        return {**base_out, "state": "insufficient_data", "findings": [],
                "message": f"Only {len(rows)} days of daily metrics recorded. At least 14 days (7 baseline + 7 recent) are needed."}
    last = datetime.fromisoformat(rows[-1]["date"]).date()
    rstart = last - timedelta(days=6); bstart = rstart - timedelta(days=28)
    recent = [r for r in rows if r["date"] >= rstart.isoformat()]
    base = [r for r in rows if bstart.isoformat() <= r["date"] < rstart.isoformat()]
    if len(base) < 7:
        return {**base_out, "state": "insufficient_data", "findings": [], "message": "Fewer than 7 baseline days before the recent window."}
    A, B = _agg(recent), _agg(base)
    rp = f"{rstart.isoformat()} → {last.isoformat()}"; bp = f"{bstart.isoformat()} → {(rstart - timedelta(days=1)).isoformat()}"
    findings = []

    def add(ftype, title, metric, bval, rval, t, causes, actions, severity, unit=""):
        chg = round((rval - bval) / bval * 100, 1) if bval else None
        fid = hashlib.md5(f"{c['id']}|{ftype}|{last}".encode()).hexdigest()[:12]
        findings.append({"id": fid, "type": ftype, "title": title, "metric": metric, "severity": severity,
                         "observed": {"baseline_value": bval, "recent_value": rval, "change_pct": chg, "unit": unit,
                                      "baseline_period": bp, "recent_period": rp, "baseline_days": len(base),
                                      "recent_days": len(recent), "welch_t": round(t, 2)},
                         "confidence": _conf(t, len(recent), len(base)), "possible_causes": causes,
                         "recommended_actions": actions, "suggested_owner_role": OWNER_ROLE[ftype],
                         "priority": "High" if severity == "high" else "Medium", "due_days": 2 if severity == "high" else 5,
                         "causality_note": "Observed change vs baseline. Causes are hypotheses to investigate, not proven."})

    def sev(chg): return "high" if abs(chg) >= 30 else "medium"
    if A["ctr"] is not None and B["ctr"]:
        t = _welch_t(_daily(recent, "ctr"), _daily(base, "ctr")); chg = (A["ctr"] - B["ctr"]) / B["ctr"] * 100
        if chg <= -15 and t <= -2:
            add("ctr_drop", f"CTR fell {abs(round(chg,1))}% vs 28-day baseline", "ctr", B["ctr"], A["ctr"], t,
                ["Creative fatigue (same audience repeatedly exposed)", "Audience targeting or placement change", "Increased auction competition"],
                ["Rotate in a fresh creative variant and A/B test it", "Review audience and placement settings for recent edits", "Check frequency in the ad platform (not available in VITRONX data)"],
                sev(chg), "%")
            tail = rows[-14:]; ys = _daily(tail, "ctr")
            if len(ys) >= 10:
                slope = float(np.polyfit(np.arange(len(ys)), ys, 1)[0]); rel = slope / (np.mean(ys) or 1) * 100
                imp_chg = (A["impressions"] / max(len(recent), 1)) / max(B["impressions"] / max(len(base), 1), 1) - 1
                if rel < -1.5 and imp_chg > -0.2:
                    add("creative_fatigue", "Possible creative fatigue: CTR trending down while delivery is stable", "ctr_slope",
                        round(float(np.mean(_daily(base, "ctr"))), 3), round(rel, 2), t,
                        ["Gradual CTR decline with stable impressions is consistent with fatigue; frequency data is needed to confirm"],
                        ["Refresh hook/visual of the top-spend creative", "Launch a new variant group and compare CTR after 7 days"],
                        "medium", "%/day")
    if A["cpc"] and B["cpc"]:
        t = _welch_t(_daily(recent, "cpc"), _daily(base, "cpc")); chg = (A["cpc"] - B["cpc"]) / B["cpc"] * 100
        if chg >= 20 and t >= 2:
            add("cpc_increase", f"CPC rose {round(chg,1)}% vs baseline", "cpc", B["cpc"], A["cpc"], t,
                ["Higher auction competition (e.g. seasonal demand)", "Lower ad relevance / CTR", "Bid strategy change"],
                ["Review bid strategy and caps", "Tighten audience or add negative keywords", "Improve relevance with new creative"], sev(chg), "₹")
    if A["cvr"] is not None and B["cvr"]:
        t = _welch_t(_daily(recent, "cvr"), _daily(base, "cvr")); chg = (A["cvr"] - B["cvr"]) / B["cvr"] * 100
        if chg <= -20 and t <= -2:
            add("conversion_decline", f"Conversion rate fell {abs(round(chg,1))}% vs baseline", "cvr", B["cvr"], A["cvr"], t,
                ["Landing page issue (speed, broken form, stock-out)", "Lower-intent traffic from targeting change", "Tracking/pixel problem"],
                ["Test the landing page and checkout/form end-to-end", "Verify conversion tracking fires correctly", "Compare traffic quality by placement"], sev(chg), "%")
    spends = _daily(rows[-35:], "spend"); anoms = zscore_anomalies(spends, threshold=2.5)
    recent_anoms = [a for a in anoms if a["index"] >= len(spends) - 7 and a["direction"] == "spike"]
    if recent_anoms:
        a = max(recent_anoms, key=lambda x: x["z"]); d = rows[-35:][a["index"]]["date"]
        add("unusual_spend", f"Unusual spend spike on {d} (z={a['z']})", "daily_spend", round(float(np.mean(spends)), 2), a["value"], a["z"],
            ["Budget edit or bid change", "Platform delivery burst"], ["Confirm the budget change was intentional", "Set a daily spend cap if unintended"],
            "high" if a["z"] >= 3.5 else "medium", "₹")
    return {**base_out, "state": "findings" if findings else "ok", "findings": findings, "recent": A, "baseline": B,
            "recent_period": rp, "baseline_period": bp}


def _peer_underperformance(results):
    roas = [r["recent"]["roas"] for r in results if r.get("recent") and r["recent"]["roas"] is not None and r["recent"]["spend"] > 0]
    if len(roas) < 3: return
    med = float(np.median(roas))
    for r in results:
        rc = r.get("recent")
        if rc and rc["roas"] is not None and med > 0 and rc["roas"] < 0.5 * med and rc["spend"] > 0:
            fid = hashlib.md5(f"{r['campaign_id']}|under|{r['recent_period']}".encode()).hexdigest()[:12]
            r["findings"].append({"id": fid, "type": "underperforming", "metric": "roas", "severity": "medium",
                "title": f"ROAS {rc['roas']}x is under half the client median ({round(med,2)}x)",
                "observed": {"baseline_value": round(med, 2), "recent_value": rc["roas"], "change_pct": round((rc['roas'] - med) / med * 100, 1),
                             "unit": "x", "baseline_period": "peer campaigns, same 7 days", "recent_period": r["recent_period"],
                             "recent_days": rc["days"], "welch_t": None},
                "confidence": "medium" if len(roas) >= 5 else "low",
                "possible_causes": ["Objective mismatch (awareness campaigns naturally show lower ROAS)", "Weak offer or audience fit"],
                "recommended_actions": ["Confirm this campaign's objective justifies lower ROAS", "Consider reallocating budget after human review"],
                "suggested_owner_role": "account_manager", "priority": "Medium", "due_days": 5,
                "causality_note": "Peer comparison only; campaigns differ in objective and audience."})
            r["state"] = "findings"


def build_router(db, get_current_user, require_role, gen_ai_text, new_id, now_iso, profitability_fn):
    r = APIRouter()

    def scope(user, cid):
        if user["role"] == "client":
            if cid and cid != user.get("client_id"): raise HTTPException(403, "Forbidden")
            return user.get("client_id")
        return cid

    # ---------- Campaign Doctor ----------
    async def doctor_for_client(cid, campaign_id=None):
        q = {"client_id": cid}
        if campaign_id: q["id"] = campaign_id
        camps = await db.campaigns.find(q, {"_id": 0}).to_list(300)
        out = []
        for c in camps:
            rows = await db.campaign_daily.find({"campaign_id": c["id"]}, {"_id": 0}).sort("date", 1).to_list(400)
            out.append(analyze_campaign(c, rows))
        _peer_underperformance(out)
        order = {"high": 0, "medium": 1}
        for o in out: o["findings"].sort(key=lambda f: order.get(f["severity"], 2))
        out.sort(key=lambda o: (0 if o["state"] == "findings" else 1, -len(o["findings"])))
        srcs = sorted({s for o in out for s in o["data_sources"]})
        return {"client_id": cid, "generated_at": now_iso(), "campaigns": out, "data_sources": srcs,
                "summary": {"campaigns": len(out), "with_findings": sum(1 for o in out if o["state"] == "findings"),
                            "insufficient_data": sum(1 for o in out if o["state"] == "insufficient_data"),
                            "findings": sum(len(o["findings"]) for o in out)},
                "method": "Recent 7 days vs prior 28-day baseline from stored daily metrics. Flags need both a material % change and |Welch t| ≥ 2. Spend spikes use z-score > 2.5 over 35 days."}

    @r.get("/doctor/{cid}")
    async def doctor(cid: str, campaign_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        scope(user, cid)
        return await doctor_for_client(cid, campaign_id)

    @r.post("/doctor/{cid}/explain")
    async def doctor_explain(cid: str, user: dict = Depends(get_current_user)):
        scope(user, cid)
        d = await doctor_for_client(cid)
        facts = [{"campaign": o["campaign_name"], "findings": [{k: f[k] for k in ("title", "observed", "confidence", "possible_causes", "recommended_actions")} for f in o["findings"]]}
                 for o in d["campaigns"] if o["findings"]]
        if not facts:
            return {"narrative": "No statistically meaningful deterioration detected in the latest 7 days versus baseline.", "llm_used": False}
        txt = await gen_ai_text(
            f"Data sources: {d['data_sources']}. Verified findings (JSON):\n{json.dumps(facts)[:7000]}\n\nWrite a 4-6 bullet plain-English briefing for an account manager. Quote the actual numbers and dates. Say 'possible cause' not 'cause'. If data source is synthetic_demo, mention that it is demo data.",
            "You explain pre-computed marketing diagnostics. Never invent metrics. Never claim causation.")
        if not txt:
            return {"narrative": "AI explanation unavailable right now. The findings below are computed directly from stored metrics.", "llm_used": False}
        return {"narrative": txt, "llm_used": True}

    class FindingTask(BaseModel):
        client_id: str
        campaign_id: str
        finding_id: str
        assignee_id: Optional[str] = None
        priority: Optional[str] = None
        due_days: Optional[int] = None

    @r.post("/doctor/task")
    async def finding_to_task(body: FindingTask, user: dict = Depends(require_role(*AGENCY_ROLES))):
        d = await doctor_for_client(body.client_id, body.campaign_id)
        camp = d["campaigns"][0] if d["campaigns"] else None
        f = next((x for x in (camp or {}).get("findings", []) if x["id"] == body.finding_id), None)
        if not f: raise HTTPException(404, "Finding no longer present (data may have changed). Re-run the Campaign Doctor.")
        owner = None
        if body.assignee_id: owner = await db.users.find_one({"id": body.assignee_id}, {"_id": 0, "password_hash": 0})
        if not owner: owner = await db.users.find_one({"role": f["suggested_owner_role"]}, {"_id": 0, "password_hash": 0})
        due = datetime.now(timezone.utc) + timedelta(days=body.due_days or f["due_days"])
        ob = f["observed"]
        task = {"id": new_id(), "client_id": body.client_id, "name": f"Campaign Doctor: {camp['campaign_name']} — {f['title']}",
                "description": f"Evidence: {f['metric']} {ob['baseline_value']}{ob['unit']} ({ob['baseline_period']}) → {ob['recent_value']}{ob['unit']} ({ob['recent_period']}), change {ob['change_pct']}%, confidence {f['confidence']}.\nActions: " + "; ".join(f["recommended_actions"]),
                "assignee_id": owner["id"] if owner else user["id"], "priority": body.priority or f["priority"], "status": "To Do",
                "due_date": due.isoformat(), "source": "campaign_doctor", "source_id": f["id"],
                "campaign_id": body.campaign_id, "created_at": now_iso(), "created_by": user["id"]}
        await db.tasks.insert_one(dict(task))
        iv = {"id": new_id(), "task_id": task["id"], "client_id": body.client_id, "campaign_id": body.campaign_id,
              "campaign_name": camp["campaign_name"], "finding_id": f["id"], "finding_type": f["type"], "finding_title": f["title"],
              "metric": f["metric"], "snapshot": camp.get("recent"), "start_date": _today().isoformat(),
              "created_at": now_iso(), "created_by": user["id"]}
        await db.interventions.insert_one(dict(iv))
        await db.activity.insert_one({"id": new_id(), "client_id": body.client_id, "user_id": user["id"], "user_name": user.get("name"),
                                      "action": f"created task from Campaign Doctor: {f['title']}", "created_at": now_iso()})
        return {"task": task, "intervention": iv, "suggested_owner": {"id": owner["id"], "name": owner["name"], "role": owner["role"]} if owner else None}

    @r.get("/doctor/interventions/{cid}")
    async def interventions(cid: str, user: dict = Depends(get_current_user)):
        scope(user, cid)
        items = await db.interventions.find({"client_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(100)
        for iv in items:
            post = await db.campaign_daily.find({"campaign_id": iv["campaign_id"], "date": {"$gt": iv["start_date"]}}, {"_id": 0}).to_list(400)
            task = await db.tasks.find_one({"id": iv["task_id"]}, {"_id": 0, "status": 1})
            iv["task_status"] = (task or {}).get("status", "deleted")
            iv["post_days"] = len(post)
            if len(post) < 3:
                iv["outcome"] = "awaiting_data"; iv["outcome_note"] = f"{len(post)} day(s) of post-intervention data. Need ≥3 to compare."
                continue
            A = _agg(post); m = {"ctr_slope": "ctr", "daily_spend": "avg_daily_spend", "roas": "roas"}.get(iv["metric"], iv["metric"])
            before = (iv.get("snapshot") or {}).get(m); after = A.get(m)
            iv["post"] = A; iv["before_value"] = before; iv["after_value"] = after
            if before is None or after is None:
                iv["outcome"] = "not_comparable"; continue
            chg = (after - before) / before * 100 if before else 0
            good = chg < -5 if m in ("cpc", "avg_daily_spend", "cpa") else chg > 5
            bad = chg > 5 if m in ("cpc", "avg_daily_spend", "cpa") else chg < -5
            iv["change_pct"] = round(chg, 1)
            iv["outcome"] = "improved" if good else ("worsened" if bad else "no_clear_change")
            iv["outcome_note"] = "Before/after comparison only. Seasonality or other changes may explain the difference."
        return items

    class DailyIn(BaseModel):
        campaign_id: str
        date: str
        impressions: int
        clicks: int
        spend: float
        conversions: int = 0
        revenue: float = 0

    @r.post("/campaign-daily")
    async def add_daily(body: DailyIn, user: dict = Depends(require_role(*AGENCY_ROLES))):
        c = await db.campaigns.find_one({"id": body.campaign_id}, {"_id": 0})
        if not c: raise HTTPException(404, "Campaign not found")
        if body.clicks > body.impressions: raise HTTPException(400, "Clicks cannot exceed impressions")
        datetime.fromisoformat(body.date)
        doc = {**body.model_dump(), "client_id": c["client_id"], "data_source": "agency_entered", "updated_at": now_iso()}
        await db.campaign_daily.update_one({"campaign_id": body.campaign_id, "date": body.date},
                                           {"$set": doc, "$setOnInsert": {"id": new_id()}}, upsert=True)
        return {"ok": True}

    # ---------- ML Learning Lab ----------
    async def records_for(kind):
        if kind == "ctr_rf":
            return await db.creatives.find({"actual_impressions": {"$gt": 0}, "actual_ctr": {"$exists": True}}, {"_id": 0}).to_list(5000)
        return await db.leads.find({}, {"_id": 0}).to_list(5000)

    async def source_counts(kind, ids):
        col = db.creatives if kind == "ctr_rf" else db.leads
        out = {}
        async for d in col.find({"id": {"$in": ids}}, {"_id": 0, "data_source": 1}):
            s = d.get("data_source", "not_recorded"); out[s] = out.get(s, 0) + 1
        return out

    async def train_and_register(kind, trigger, user_id, force=False):
        recs = await records_for(kind)
        active = await db.ml_model_versions.find_one({"kind": kind, "status": "active"}, {"_id": 0})
        cand = ml_lab.train_ctr(recs) if kind == "ctr_rf" else ml_lab.train_lead(recs)
        if cand["status"] != "trained":
            return {**cand, "promoted": False, "readiness": "insufficient_data"}
        new_obs = cand["total_samples"] - (active or {}).get("total_samples", 0)
        if active and new_obs < 5 and not force:
            return {"status": "skipped", "promoted": False, "new_observations": new_obs,
                    "reason": f"Only {new_obs} new labelled records since {active['version_label']}. Retraining needs ≥5 (admin can force)."}
        n = await db.ml_model_versions.count_documents({"kind": kind}) + 1
        label = f"{'rf-ctr' if kind == 'ctr_rf' else 'lr-lead'}-v{n}"
        ok, reason = ml_lab.should_promote(kind, cand, active)
        meta = {k: v for k, v in cand.items() if k != "model"}
        meta.update({"id": new_id(), "kind": kind, "version": n, "version_label": label, "trained_at": now_iso(),
                     "trained_by": user_id, "trigger": trigger, "status": "active" if ok else "rejected",
                     "promotion_reason": reason, "readiness": ml_lab.readiness(kind, cand["metrics"]),
                     "data_sources": await source_counts(kind, cand["train_ids"] + cand["test_ids"])})
        if ok:
            await db.ml_model_versions.update_many({"kind": kind, "status": "active"}, {"$set": {"status": "retired"}})
            ml_lab.activate(kind, cand["model"], {**meta, "version": label})
        await db.ml_model_versions.insert_one(dict(meta))
        meta.pop("_id", None)
        return {**{k: v for k, v in meta.items() if k not in ("train_ids", "test_ids", "x_median", "x_mean")}, "promoted": ok}

    async def restore_active(kind):
        a = await db.ml_model_versions.find_one({"kind": kind, "status": "active"}, {"_id": 0})
        if not a:
            if await db.ml_model_versions.count_documents({"kind": kind}):
                return {"restored": None, "reason": "No version has passed the evaluation gate"}
            return await train_and_register(kind, "bootstrap", "system", force=True)
        col = db.creatives if kind == "ctr_rf" else db.leads
        rows = await col.find({"id": {"$in": a["train_ids"]}}, {"_id": 0}).to_list(5000)
        if len(rows) != len(a["train_ids"]):
            await db.ml_model_versions.update_one({"id": a["id"]}, {"$set": {"status": "retired", "promotion_reason": "Training records changed; cannot reproduce."}})
            return await train_and_register(kind, "rebuild_after_data_change", "system", force=True)
        ml_lab.activate(kind, ml_lab.refit(kind, rows), {**a, "version": a["version_label"]})
        return {"restored": a["version_label"]}

    async def log_prediction(kind, entity, pred, value):
        a = ml_lab.ACTIVE[kind]["meta"]
        label_known = (kind == "lead_lr" and entity.get("status") in ("Won", "Lost")) or (kind == "ctr_rf" and entity.get("actual_ctr") is not None)
        feats = dict(zip(ml_lab.CTR_FEATURES if kind == "ctr_rf" else ml_lab.LEAD_FEATURES,
                         ml_lab.ctr_vector(entity) if kind == "ctr_rf" else ml_lab.lead_vector(entity)))
        await db.ml_predictions.update_one(
            {"kind": kind, "entity_id": entity["id"], "model_version": a["version"]},
            {"$setOnInsert": {"id": new_id(), "client_id": entity.get("client_id"), "features": feats, "prediction": value,
                              "data_source": entity.get("data_source", "not_recorded"), "created_at": now_iso(),
                              "label_known_at_prediction": label_known,
                              "in_training_set": entity["id"] in a.get("train_ids", []) or entity["id"] in a.get("test_ids", []),
                              "actual": None}}, upsert=True)

    async def resolve_actuals():
        n = 0
        async for p in db.ml_predictions.find({"actual": None}, {"_id": 0}):
            if p["kind"] == "ctr_rf":
                e = await db.creatives.find_one({"id": p["entity_id"]}, {"_id": 0})
                act = e.get("actual_ctr") if e and (e.get("actual_impressions") or 0) > 0 else None
            else:
                e = await db.leads.find_one({"id": p["entity_id"]}, {"_id": 0})
                act = (1 if e["status"] == "Won" else 0) if e and e.get("status") in ("Won", "Lost") else None
            if act is not None:
                await db.ml_predictions.update_one({"id": p["id"]}, {"$set": {"actual": act, "actual_recorded_at": now_iso()}}); n += 1
        return n

    async def live_eval(kind):
        q = {"kind": kind, "actual": {"$ne": None}, "label_known_at_prediction": False, "in_training_set": False}
        rows = await db.ml_predictions.find(q, {"_id": 0}).to_list(5000)
        total = await db.ml_predictions.count_documents({"kind": kind})
        out = {"logged_predictions": total, "resolved_honest": len(rows),
               "excluded_note": "Predictions made when the outcome was already known, or on training/test records, are excluded from live evaluation."}
        if len(rows) < 10:
            out["status"] = "insufficient_data"; out["message"] = f"{len(rows)} honest prediction/actual pairs. Need ≥10 to evaluate live accuracy."
            return out
        if kind == "ctr_rf":
            out["metrics"] = ml_lab.regression_metrics([r["actual"] for r in rows], [r["prediction"] for r in rows])
        else:
            out["metrics"] = ml_lab.classification_metrics([r["actual"] for r in rows], [r["prediction"] / 100 for r in rows])
        out["status"] = "evaluated"
        return out

    def public_meta(v):
        return {k: v[k] for k in v if k not in ("train_ids", "test_ids", "x_median", "x_mean", "_id")}

    @r.get("/ml/lab")
    async def lab(user: dict = Depends(require_role(*AGENCY_ROLES))):
        await resolve_actuals()
        out = {}
        for kind in ("ctr_rf", "lead_lr"):
            versions = await db.ml_model_versions.find({"kind": kind}, {"_id": 0}).sort("version", -1).to_list(50)
            active = next((v for v in versions if v["status"] == "active"), None)
            le = await live_eval(kind)
            drift = None
            if active and le.get("metrics"):
                if kind == "ctr_rf":
                    drift = le["metrics"]["mae"] > 1.5 * active["metrics"]["mae"]
                else:
                    drift = le["metrics"]["accuracy"] < active["metrics"]["accuracy"] - 0.15
            out[kind] = {"active": public_meta(active) if active else None, "readiness": active["readiness"] if active else "insufficient_data",
                         "versions": [public_meta(v) for v in versions], "live_evaluation": le, "drift_flag": drift}
        return out

    @r.post("/ml/lab/{kind}/retrain")
    async def retrain(kind: str, force: bool = False, user: dict = Depends(require_role("agency_admin", "account_manager"))):
        if kind not in ("ctr_rf", "lead_lr"): raise HTTPException(404, "Unknown model")
        if force and user["role"] != "agency_admin": raise HTTPException(403, "Only admins can force retraining")
        return await train_and_register(kind, "manual", user["id"], force)

    @r.post("/ml/lab/resolve")
    async def resolve(user: dict = Depends(require_role(*AGENCY_ROLES))):
        return {"resolved": await resolve_actuals()}

    # Backward-compatible endpoints used by existing panels
    def compat_status(kind):
        a = ml_lab.ACTIVE[kind]
        if not a: return {"status": "untrained"}
        m = a["meta"]
        return {"status": "trained", "metrics": m["metrics"], "importance": m.get("importance"), "model_version": m["version"],
                "trained_at": m["trained_at"], "readiness": m["readiness"], "warnings": m.get("warnings", []),
                "total_samples": m.get("total_samples"), "train_range": m.get("train_range"), "test_range": m.get("test_range"),
                "data_sources": m.get("data_sources")}

    @r.get("/ml/ctr-model")
    async def ctr_status(user: dict = Depends(get_current_user)):
        return compat_status("ctr_rf")

    @r.post("/ml/ctr-model/train")
    async def ctr_train(user: dict = Depends(require_role("agency_admin", "account_manager"))):
        return await train_and_register("ctr_rf", "manual", user["id"])

    @r.get("/ml/ctr-model/predict/{creative_id}")
    async def ctr_predict(creative_id: str, user: dict = Depends(get_current_user)):
        c = await db.creatives.find_one({"id": creative_id}, {"_id": 0})
        if not c: raise HTTPException(404, "Creative not found")
        scope(user, c.get("client_id"))
        p = ml_lab.predict_ctr(c)
        if not p: return {"status": "model_not_trained"}
        await log_prediction("ctr_rf", c, p, p["predicted_ctr_rf"])
        return {**p, "creative_name": c.get("name")}

    @r.get("/ml/lead-conversion")
    async def lead_status(user: dict = Depends(get_current_user)):
        return compat_status("lead_lr")

    @r.post("/ml/lead-conversion/train")
    async def lead_train(user: dict = Depends(require_role("agency_admin", "account_manager"))):
        return await train_and_register("lead_lr", "manual", user["id"])

    @r.get("/ml/lead-conversion/predict/{lead_id}")
    async def lead_predict(lead_id: str, user: dict = Depends(get_current_user)):
        l = await db.leads.find_one({"id": lead_id}, {"_id": 0})
        if not l: raise HTTPException(404, "Lead not found")
        scope(user, l.get("client_id"))
        p = ml_lab.predict_lead(l)
        if not p: return {"status": "model_not_trained"}
        await log_prediction("lead_lr", l, p, p["conversion_probability"])
        return {**p, "lead_name": l.get("name")}

    @r.get("/ml/lead-conversion/predict-batch/{client_id}")
    async def lead_batch(client_id: str, user: dict = Depends(get_current_user)):
        scope(user, client_id)
        leads = await db.leads.find({"client_id": client_id}, {"_id": 0}).to_list(500)
        out = []
        for l in leads:
            p = ml_lab.predict_lead(l)
            if p and l.get("status") not in ("Won", "Lost"):
                await log_prediction("lead_lr", l, p, p["conversion_probability"])
            out.append({**l, **(p or {"conversion_probability": None, "tier": None})})
        out.sort(key=lambda x: -(x.get("conversion_probability") or 0))
        return out

    @r.get("/ml/explain/{kind}/{entity_id}")
    async def explain(kind: str, entity_id: str, user: dict = Depends(get_current_user)):
        col = {"ctr": db.creatives, "lead": db.leads}.get(kind)
        if col is None: raise HTTPException(404, "Unknown model")
        e = await col.find_one({"id": entity_id}, {"_id": 0})
        if not e: raise HTTPException(404, "Record not found")
        scope(user, e.get("client_id"))
        mk = "ctr_rf" if kind == "ctr" else "lead_lr"
        ex = ml_lab.explain_ctr(e) if kind == "ctr" else ml_lab.explain_lead(e)
        if not ex: return {"status": "model_not_trained"}
        m = ml_lab.ACTIVE[mk]["meta"]
        return {**ex, "entity_name": e.get("name"), "model_version": m["version"], "readiness": m["readiness"],
                "trained_on": m.get("total_samples"), "data_sources": m.get("data_sources"), "warnings": m.get("warnings", []),
                "actual": e.get("actual_ctr") if kind == "ctr" else e.get("status"),
                "in_training_data": entity_id in m.get("train_ids", []) or entity_id in m.get("test_ids", [])}

    @r.get("/ml/transparency")
    async def transparency(user: dict = Depends(get_current_user)):
        out = []
        for kind, name, problem, target in (("ctr_rf", "CTR Predictor", "Estimate click-through rate of a creative before/while it runs", "actual_ctr (%) of a creative with impressions > 0"),
                                            ("lead_lr", "Lead Conversion Classifier", "Estimate probability that an open lead will be Won", "lead status Won (1) vs Lost (0)")):
            a = ml_lab.ACTIVE[kind].get("meta")
            versions = await db.ml_model_versions.count_documents({"kind": kind})
            out.append({"key": kind, "name": name, "type": "trained_ml", "algorithm": a["metrics"]["algorithm"] if a else "Not trained",
                        "problem": problem, "target": target,
                        "features": ml_lab.CTR_FEATURES if kind == "ctr_rf" else ml_lab.LEAD_FEATURES,
                        "training_data": {"collection": "creatives" if kind == "ctr_rf" else "leads (Won/Lost only)",
                                          "usable_records": a.get("total_samples") if a else 0,
                                          "train_range": a.get("train_range") if a else None, "test_range": a.get("test_range") if a else None,
                                          "sources": a.get("data_sources") if a else "Not recorded"},
                        "preprocessing": (["Keep creatives with impressions > 0 and recorded actual_ctr", "Categorical platform/type/objective mapped to integer codes", "Caption → CTA/offer/length/hashtag features"]
                                          if kind == "ctr_rf" else ["Keep leads with status Won or Lost", "Source one-hot encoded", "Deal value log1p transformed", "Pipeline stage EXCLUDED (it encodes the outcome → leakage)"]),
                        "validation": a["metrics"]["validation"] if a else "Not recorded",
                        "metrics": a["metrics"] if a else None, "version": a["version"] if a else None,
                        "trained_at": a["trained_at"] if a else None, "readiness": a["readiness"] if a else "insufficient_data",
                        "versions_recorded": versions, "warnings": a.get("warnings", []) if a else [],
                        "limitations": ["Trained on seeded SYNTHETIC demo records — not on Meta/Google/GA4 data (no live integration connected)",
                                        "Small sample → wide error bars; do not use for budget decisions",
                                        "Learns associations, not causes"],
                        "outcomes_and_retraining": ("Actual CTR is recorded via A/B metrics entry on a creative; predictions are logged and matched automatically. Retraining is manual (≥5 new labelled records) and a candidate replaces the active model only if it passes the evaluation gate."
                                                    if kind == "ctr_rf" else "Outcome recorded when a lead's status is set to Won/Lost; logged predictions are matched automatically. Retraining is manual (≥5 new labelled records) with an evaluation gate."),
                        "self_learning": False})
        out += [
            {"key": "campaign_doctor", "name": "Campaign Doctor", "type": "statistical_rules", "algorithm": "7-day vs 28-day baseline; Welch t-statistic; z-score spend anomaly; peer ROAS median",
             "problem": "Detect measurable campaign deterioration", "target": "n/a (diagnostic)", "features": ["daily impressions", "clicks", "spend", "conversions", "revenue"],
             "training_data": {"collection": "campaign_daily", "sources": await _daily_sources()}, "validation": "Not a trained model — deterministic thresholds",
             "limitations": ["No frequency/audience data, so fatigue is a hypothesis", "Seasonality not modelled"], "self_learning": False},
            {"key": "lead_heuristic", "name": "Lead Score (heuristic)", "type": "rule_based", "algorithm": "Hand-set weights on source, stage, value → sigmoid",
             "problem": "Quick lead prioritisation", "target": "n/a", "features": ["source", "stage", "value"], "training_data": {"sources": "None — weights are manually defined"},
             "validation": "Not validated", "limitations": ["Weights are not learned from data"], "self_learning": False},
            {"key": "client_risk", "name": "Client Risk Score", "type": "rule_based", "algorithm": "Additive points from health score, ROAS, overdue tasks, pending approvals",
             "problem": "Flag retention/delivery risk", "target": "n/a", "features": ["health_score", "ROAS", "overdue tasks", "pending approvals"],
             "training_data": {"sources": "None — rule-based"}, "validation": "Not validated against churn outcomes (no churn labels recorded)", "limitations": ["Thresholds are judgement-based"], "self_learning": False},
            {"key": "forecast", "name": "Trend Forecast", "type": "statistical", "algorithm": "OLS linear trend + EMA + z-score anomalies",
             "problem": "Short-term direction of spend/clicks/conversions", "target": "next 7 days", "features": ["30-day daily client series from campaign_daily"],
             "training_data": {"sources": await _daily_sources()}, "validation": "In-sample R² only", "limitations": ["Linear; no seasonality"], "self_learning": False},
        ]
        return {"models": out, "integrations_note": "Meta Ads, Google Ads, GA4 and Search Console are in DEMO mode. No external platform data has been ingested.",
                "self_learning_note": "No model in VITRONX retrains or improves automatically. Retraining is a manual, gated action."}

    async def _daily_sources():
        out = {}
        for s in await db.campaign_daily.distinct("data_source"):
            out[s] = await db.campaign_daily.count_documents({"data_source": s})
        return out or "No daily metrics recorded"

    # ---------- Recommendations ----------
    async def recommendations_for(user, client_id=None, limit=30):
        cid = scope(user, client_id)
        clients = await db.clients.find({"id": cid} if cid else {}, {"_id": 0}).to_list(200)
        now = datetime.now(timezone.utc); recs = []
        def rec(kind, c, issue, evidence, period, action, conf, link, prio, benefit=None):
            recs.append({"id": hashlib.md5(f"{kind}|{c['id']}|{issue}".encode()).hexdigest()[:12], "kind": kind, "client_id": c["id"],
                         "client_name": c["name"], "issue": issue, "evidence": evidence, "period": period, "action": action,
                         "expected_benefit": benefit, "confidence": conf, "link": link, "priority_score": prio, "requires_human_approval": True})
        for c in clients:
            d = await doctor_for_client(c["id"])
            for o in d["campaigns"]:
                for f in o["findings"]:
                    ob = f["observed"]
                    rec("campaign", c, f"{o['campaign_name']}: {f['title']}",
                        f"{f['metric']} {_fv(ob['baseline_value'], ob['unit'])} → {_fv(ob['recent_value'], ob['unit'])} ({ob['change_pct']}%)",
                        ob["recent_period"], f["recommended_actions"][0], f["confidence"], f"/workspace/{c['id']}?tab=Campaigns",
                        90 if f["severity"] == "high" else 60)
            leads = await db.leads.find({"client_id": c["id"], "status": {"$in": ["New", "Contacted"]}}, {"_id": 0}).to_list(500)
            for l in leads:
                try: age = (now - datetime.fromisoformat(l["created_at"].replace("Z", "+00:00"))).days
                except Exception: continue
                p = ml_lab.predict_lead(l)
                if age >= 3 and p and p["conversion_probability"] >= 40:
                    rec("lead", c, f"Follow up {l['name']} ({l.get('company','')})", f"Status '{l['status']}' for {age} days; model P(Won)={p['conversion_probability']}% ({p['model_version']}, demo-trained)",
                        f"since {l['created_at'][:10]}", "Call or email the lead within 24h and update the stage", "low", f"/workspace/{c['id']}?tab=Leads", 50 + min(p["conversion_probability"] / 5, 20))
            tasks = await db.tasks.find({"client_id": c["id"], "status": {"$ne": "Completed"}}, {"_id": 0}).to_list(500)
            overdue = [t for t in tasks if t.get("due_date") and t["due_date"] < now.isoformat()]
            if overdue:
                oldest = min(t["due_date"] for t in overdue)
                rec("tasks", c, f"{len(overdue)} overdue task(s)", ", ".join(t["name"] for t in overdue[:3]), f"oldest due {oldest[:10]}",
                    "Reassign or reschedule overdue tasks blocking delivery", "high", f"/workspace/{c['id']}?tab=Tasks", 55 + min(len(overdue) * 3, 25))
            content = await db.content.find({"client_id": c["id"], "status": "Client Review"}, {"_id": 0}).to_list(300)
            stale = [x for x in content if (x.get("created_at") or "") < (now - timedelta(days=3)).isoformat()]
            if stale:
                rec("approvals", c, f"{len(stale)} approval(s) waiting > 3 days", ", ".join(x["title"] for x in stale[:3]), "in Client Review",
                    "Nudge the client contact for approval (send manually after review)", "high", f"/workspace/{c['id']}?tab=Approvals", 58)
            if user["role"] != "client":
                camps = await db.campaigns.find({"client_id": c["id"]}, {"_id": 0}).to_list(300)
                rk = compute_client_risk(c, camps, tasks, content)
                if rk.get("risk_level") in ("high", "critical"):
                    rec("client_risk", c, f"Client risk {rk['risk_level']} (score {rk['risk_score']})", " · ".join(f"{x['factor']}: {x['detail']}" for x in rk["drivers"][:3]),
                        "current", rk.get("intervention", "Schedule a client health review"), "medium", f"/workspace/{c['id']}?tab=Risk", 80 if rk["risk_level"] == "critical" else 65)
                cpas = [(cp, cp["spend"] / cp["conversions"]) for cp in camps if cp.get("conversions") and cp.get("spend")]
                tot = sum(cp.get("spend", 0) for cp in camps)
                if len(cpas) >= 3 and tot:
                    med = float(np.median([x[1] for x in cpas]))
                    for cp, cpa in cpas:
                        if cpa > 1.5 * med and cp["spend"] >= 0.1 * tot:
                            excess = round(cp["spend"] - cp["conversions"] * med)
                            rec("budget", c, f"{cp['name']}: CPA ₹{round(cpa):,} vs client median ₹{round(med):,}", f"Spend ₹{round(cp['spend']):,}, {cp['conversions']} conversions (lifetime totals)",
                                "campaign lifetime", "Review targeting/bids before any budget shift (human approval required)", "medium",
                                f"/workspace/{c['id']}?tab=Campaigns", 62, f"Up to ₹{excess:,} if CPA matched the median (upper bound, not guaranteed)")
        recs.sort(key=lambda x: -x["priority_score"])
        return recs[:limit]

    @r.get("/recommendations")
    async def recommendations(client_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        return await recommendations_for(user, client_id)

    # ---------- AI Buddy ----------
    class ChatIn(BaseModel):
        message: str
        session_id: str
        path: Optional[str] = None
        client_id: Optional[str] = None
        campaign_id: Optional[str] = None

    @r.post("/buddy/chat")
    async def buddy_chat(body: ChatIn, user: dict = Depends(get_current_user)):
        msg = body.message.strip()[:1000]
        if not msg: raise HTTPException(400, "Empty message")
        cid = scope(user, body.client_id)
        client = await db.clients.find_one({"id": cid}, {"_id": 0, "name": 1, "id": 1}) if cid else None
        if cid and not client: cid = None
        low = msg.lower(); facts: Dict[str, Any] = {}; sources = []; intents = []
        def has(*w): return any(x in low for x in w)
        if has("ctr", "campaign", "cpc", "conversion", "spend", "fatigue", "attention", "perform"):
            intents.append("campaign_doctor")
            if cid:
                d = await doctor_for_client(cid, body.campaign_id)
                facts["campaign_doctor"] = {"data_sources": d["data_sources"], "method": d["method"], "summary": d["summary"],
                    "campaigns": [{"name": o["campaign_name"], "state": o["state"], "recent": o.get("recent"), "baseline": o.get("baseline"),
                                   "findings": [{k: f[k] for k in ("title", "observed", "confidence", "possible_causes", "recommended_actions")} for f in o["findings"]]}
                                  for o in d["campaigns"][:6]]}
                sources.append({"label": "Campaign Doctor", "link": f"/workspace/{cid}?tab=Campaigns"})
        if has("risk", "churn"):
            intents.append("risk")
            if cid and user["role"] != "client":
                c = await db.clients.find_one({"id": cid}, {"_id": 0})
                rk = compute_client_risk(c, await db.campaigns.find({"client_id": cid}, {"_id": 0}).to_list(300),
                                         await db.tasks.find({"client_id": cid}, {"_id": 0}).to_list(300), await db.content.find({"client_id": cid}, {"_id": 0}).to_list(300))
                facts["client_risk"] = {**rk, "method": "Rule-based additive points (not ML)"}
                sources.append({"label": "Risk", "link": f"/workspace/{cid}?tab=Risk"})
            elif user["role"] == "client":
                facts["client_risk"] = "Risk scores are internal to the agency and not available in the client portal."
        if has("predict", "model", "train", "accuracy", "machine learning", "ml", "data used"):
            intents.append("models")
            facts["models"] = [{"name": k, **{x: ml_lab.ACTIVE[k]["meta"].get(x) for x in ("version", "metrics", "readiness", "total_samples", "data_sources", "warnings", "train_range")}}
                               if ml_lab.ACTIVE[k] else {"name": k, "status": "not trained"} for k in ("ctr_rf", "lead_lr")]
            facts["models_note"] = "Trained on seeded synthetic demo data; no external ad platform data ingested; no automatic self-learning."
            sources.append({"label": "ML Lab", "link": f"/workspace/{cid}?tab=ML+Lab" if cid else "/"})
        if has("lead", "hot", "warm", "cold"):
            intents.append("leads")
            q = {"client_id": cid} if cid else ({} if user["role"] != "client" else {"client_id": "none"})
            q["status"] = {"$nin": ["Won", "Lost"]}
            leads = await db.leads.find(q, {"_id": 0}).to_list(300)
            scored = sorted([{**l, **(ml_lab.predict_lead(l) or {})} for l in leads], key=lambda x: -(x.get("conversion_probability") or 0))[:5]
            facts["top_open_leads"] = [{"name": l["name"], "source": l.get("source"), "value_inr": l.get("value"), "status": l["status"],
                                        "p_won_pct": l.get("conversion_probability"), "tier": l.get("tier")} for l in scored]
            if scored and ml_lab.ACTIVE["lead_lr"]:
                facts["lead_tier_explanation"] = ml_lab.explain_lead(scored[0])
        if has("overdue", "task", "deadline", "late"):
            intents.append("tasks")
            q = {"status": {"$ne": "Completed"}, "due_date": {"$lt": now_iso()}}
            if cid: q["client_id"] = cid
            od = await db.tasks.find(q, {"_id": 0}).sort("due_date", 1).to_list(50)
            facts["overdue_tasks"] = {"count": len(od), "items": [{"name": t["name"], "due": t["due_date"][:10], "priority": t.get("priority"), "status": t["status"]} for t in od[:8]]}
        if has("profit", "margin", "revenue", "profitability"):
            intents.append("profitability")
            if user["role"] in AGENCY_FIN_ROLES and cid:
                facts["profitability"] = await profitability_fn(cid, user=user)
            elif user["role"] not in AGENCY_FIN_ROLES:
                facts["profitability"] = "Restricted: your role cannot view agency financial data."
            else:
                facts["profitability"] = "Select a client to view its profitability."
        if has("report", "summary", "overall", "how is", "how are"):
            intents.append("report")
            q = {"client_id": cid} if cid else ({} if user["role"] != "client" else {"client_id": "none"})
            camps = await db.campaigns.find(q, {"_id": 0}).to_list(500)
            sp = sum(c.get("spend", 0) for c in camps); rv = sum(c.get("revenue", 0) for c in camps)
            im = sum(c.get("impressions", 0) for c in camps); ck = sum(c.get("clicks", 0) for c in camps); cv = sum(c.get("conversions", 0) for c in camps)
            facts["report_kpis"] = {"campaigns": len(camps), "spend_inr": sp, "revenue_inr": rv, "roas": round(rv / sp, 2) if sp else None,
                                    "ctr_pct": round(ck / im * 100, 2) if im else None, "conversions": cv, "note": "Lifetime campaign totals (seeded demo data)"}
        if has("next", "should", "priorit", "first", "recommend", "todo", "to do") or not intents:
            intents.append("recommendations")
            recs = await recommendations_for(user, cid, limit=6)
            facts["recommendations"] = [{k: x[k] for k in ("client_name", "issue", "evidence", "period", "action", "confidence", "expected_benefit")} for x in recs]
            sources.append({"label": "Recommendations", "link": f"/workspace/{cid}?tab=AI+Insights" if cid else "/"})
        if has("profitability calculated", "how is profit", "calculate"):
            facts["profitability_method"] = "Revenue = monthly retainer + 15% of ad spend (mgmt fee). Cost = team 30% + creative 10% of revenue + 2% of ad spend. Heuristic estimate, not accounting data."

        history = await db.buddy_messages.find({"session_id": body.session_id, "user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(6)
        hist_txt = "\n".join(f"{h['role']}: {h['text'][:300]}" for h in reversed(history))
        ctx = {"user_role": user["role"], "current_page": body.path, "selected_client": client["name"] if client else None}
        facts_txt = json.dumps(facts, default=str)[:9000]
        answer = await gen_ai_text(
            f"Context: {json.dumps(ctx)}\nRecent conversation:\n{hist_txt}\n\nVERIFIED FACTS (JSON from VITRONX services):\n{facts_txt}\n\nUser question: {msg}",
            "You are VITRONX AI Buddy, a friendly concise assistant for a digital marketing agency in India. Answer ONLY from the verified facts. "
            "Quote real numbers, dates and ₹ values. If facts are missing or insufficient, say so and suggest where to look. Never invent data. "
            "Describe causes as possibilities, not proof. Mention when data is synthetic demo data if relevant. Never recommend automatic actions; say a human should approve. "
            "Plain text, max ~140 words, short bullets allowed, no markdown headers.")
        llm_used = bool(answer)
        if not answer:
            lines = ["AI language service is unavailable, so here are the computed facts:"]
            for k, v in facts.items():
                lines.append(f"• {k}: {json.dumps(v, default=str)[:400]}")
            if not facts: lines.append("• No matching data found for this question in your scope.")
            answer = "\n".join(lines)
        for role, text in (("user", msg), ("assistant", answer)):
            await db.buddy_messages.insert_one({"id": new_id(), "session_id": body.session_id, "user_id": user["id"], "role": role,
                                                "text": text, "client_id": cid, "created_at": now_iso()})
        return {"answer": answer, "llm_used": llm_used, "intents": intents, "sources": sources, "scope_client": client["name"] if client else None}

    # ---------- Startup ----------
    async def startup():
        for col in ("campaigns", "creatives", "leads", "tasks"):
            await db[col].update_many({"data_source": {"$exists": False}, "created_by": {"$exists": True}}, {"$set": {"data_source": "agency_entered"}})
            await db[col].update_many({"data_source": {"$exists": False}}, {"$set": {"data_source": "synthetic_demo"}})
        if await db.campaign_daily.count_documents({}) == 0:
            await seed_daily()
        for kind in ("ctr_rf", "lead_lr"):
            try:
                await restore_active(kind)
            except Exception as e:
                import logging; logging.getLogger("vitronx").warning(f"model restore {kind} failed: {e}")

    async def seed_daily():
        today = _today(); docs = []
        camps = await db.campaigns.find({}, {"_id": 0}).to_list(500)
        for c in camps:
            rng = random.Random(c["id"])
            imp = max(c.get("impressions", 0), 20000) / 56; ctr = (c.get("clicks", 0) / c["impressions"]) if c.get("impressions") else 0.02
            cpc = (c.get("spend", 0) / c["clicks"]) if c.get("clicks") else 8; cvr = (c.get("conversions", 0) / c["clicks"]) if c.get("clicks") else 0.02
            aov = (c.get("revenue", 0) / c["conversions"]) if c.get("conversions") else 1500
            scenario = rng.choice(["ctr_drop", "cpc_spike", "conv_drop", "spend_spike"]) if rng.random() < 0.35 else None
            for i in range(60, 0, -1):
                d = today - timedelta(days=i); k = 60 - i
                f_ctr = f_cpc = f_cvr = f_sp = 1.0
                if scenario == "ctr_drop" and k >= 46: f_ctr = 1 - 0.04 * (k - 45)
                if scenario == "cpc_spike" and k >= 53: f_cpc = 1.55
                if scenario == "conv_drop" and k >= 53: f_cvr = 0.45
                if scenario == "spend_spike" and k == 57: f_sp = 3.2
                im = int(imp * rng.uniform(0.85, 1.15)); ck = int(im * ctr * f_ctr * rng.uniform(0.9, 1.1))
                sp = round(ck * cpc * f_cpc * rng.uniform(0.92, 1.08) * f_sp, 2); cv = int(round(ck * cvr * f_cvr * rng.uniform(0.85, 1.15)))
                docs.append({"id": new_id(), "campaign_id": c["id"], "client_id": c["client_id"], "date": d.isoformat(), "impressions": im,
                             "clicks": ck, "spend": sp, "conversions": cv, "revenue": round(cv * aov * rng.uniform(0.9, 1.1), 2),
                             "data_source": "synthetic_demo", "created_at": now_iso()})
        if docs:
            await db.campaign_daily.insert_many(docs)
            await db.campaign_daily.create_index([("campaign_id", 1), ("date", 1)])

    r.startup = startup
    return r

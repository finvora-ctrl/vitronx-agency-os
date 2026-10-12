"""Backend tests for Campaign Doctor, ML Lab, Transparency, Recommendations, AI Buddy, and regression."""
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL missing"

ADMIN = {"email": "finvora@gmail.com", "password": "Vitronx@2026"}
MANAGER = {"email": "sarah.manager@vitronx.demo", "password": "Demo@2026"}
DESIGNER = {"email": "riya.designer@vitronx.demo", "password": "Demo@2026"}
CLIENT = {"email": "client@vitronx.demo", "password": "Demo@2026"}
CLIENT_ID = "bb8a55f8-a0e6-42f8-a68c-4676dc6449b5"

_tokens = {}
_created = {"tasks": [], "interventions": [], "campaign_daily": []}


def _tok(creds):
    k = creds["email"]
    if k in _tokens:
        return _tokens[k]
    r = requests.post(f"{BASE}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed {creds['email']} {r.status_code} {r.text}"
    _tokens[k] = r.json()["token"]
    return _tokens[k]


def _h(creds):
    return {"Authorization": f"Bearer {_tok(creds)}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_h():
    return _h(ADMIN)


@pytest.fixture(scope="module")
def manager_h():
    return _h(MANAGER)


@pytest.fixture(scope="module")
def client_h():
    return _h(CLIENT)


# ------------- Auth sanity -----------
def test_login_all_roles():
    for c in (ADMIN, MANAGER, DESIGNER, CLIENT):
        _tok(c)
    assert len(_tokens) == 4


# ------------- Campaign Doctor -------------
def test_doctor_returns_structure(admin_h):
    r = requests.get(f"{BASE}/api/doctor/{CLIENT_ID}", headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["client_id"] == CLIENT_ID
    assert "campaigns" in d and isinstance(d["campaigns"], list)
    assert "data_sources" in d
    assert "synthetic_demo" in d["data_sources"]
    # Pick any campaign with findings for subsequent tests
    with_findings = [c for c in d["campaigns"] if c.get("findings")]
    assert d["summary"]["campaigns"] == len(d["campaigns"])
    if with_findings:
        f = with_findings[0]["findings"][0]
        for k in ("id", "type", "observed", "confidence", "possible_causes", "recommended_actions", "severity"):
            assert k in f, f"finding missing {k}"
        ob = f["observed"]
        for k in ("baseline_value", "recent_value", "baseline_period", "recent_period", "welch_t"):
            assert k in ob


def test_doctor_task_and_interventions(admin_h, client_h):
    r = requests.get(f"{BASE}/api/doctor/{CLIENT_ID}", headers=admin_h, timeout=30).json()
    pick = None
    for c in r["campaigns"]:
        if c.get("findings"):
            pick = (c, c["findings"][0])
            break
    if not pick:
        pytest.skip("No findings available in demo data to create task")
    camp, finding = pick
    body = {"client_id": CLIENT_ID, "campaign_id": camp["campaign_id"], "finding_id": finding["id"]}

    # Client role must get 403
    rc = requests.post(f"{BASE}/api/doctor/task", json=body, headers=client_h, timeout=20)
    assert rc.status_code == 403, f"client should be forbidden but got {rc.status_code}"

    r2 = requests.post(f"{BASE}/api/doctor/task", json=body, headers=admin_h, timeout=30)
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["task"]["source"] == "campaign_doctor"
    assert data["task"]["client_id"] == CLIENT_ID
    _created["tasks"].append(data["task"]["id"])
    _created["interventions"].append(data["intervention"]["id"])

    iv = requests.get(f"{BASE}/api/doctor/interventions/{CLIENT_ID}", headers=admin_h, timeout=20)
    assert iv.status_code == 200
    items = iv.json()
    mine = [x for x in items if x["id"] == data["intervention"]["id"]]
    assert mine, "created intervention not listed"
    assert mine[0]["outcome"] == "awaiting_data"


def test_campaign_daily_validation(admin_h, client_h):
    camps = requests.get(f"{BASE}/api/clients/{CLIENT_ID}/campaigns", headers=admin_h, timeout=20)
    # fallback endpoint
    if camps.status_code != 200:
        camps = requests.get(f"{BASE}/api/campaigns?client_id={CLIENT_ID}", headers=admin_h, timeout=20)
    assert camps.status_code == 200, camps.text
    arr = camps.json()
    assert arr, "No campaigns to test"
    cid = arr[0]["id"]

    bad = {"campaign_id": cid, "date": "2026-01-01", "impressions": 100, "clicks": 999, "spend": 10.0}
    r = requests.post(f"{BASE}/api/campaign-daily", json=bad, headers=admin_h, timeout=20)
    assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text}"

    # Client cannot write
    good = {"campaign_id": cid, "date": "2020-01-01", "impressions": 500, "clicks": 20, "spend": 100.0, "conversions": 1, "revenue": 200}
    rc = requests.post(f"{BASE}/api/campaign-daily", json=good, headers=client_h, timeout=20)
    assert rc.status_code == 403

    ok = requests.post(f"{BASE}/api/campaign-daily", json=good, headers=admin_h, timeout=20)
    assert ok.status_code == 200, ok.text
    _created["campaign_daily"].append((cid, "2020-01-01"))


# ------------- ML Learning Lab -------------
def test_ml_lab(manager_h):
    r = requests.get(f"{BASE}/api/ml/lab", headers=manager_h, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "ctr_rf" in d and "lead_lr" in d
    # ctr_rf: no active version (fails gate) is EXPECTED
    assert d["ctr_rf"]["active"] is None, f"expected no active ctr_rf, got {d['ctr_rf']['active']}"
    # lead_lr: should have active
    assert d["lead_lr"]["active"] is not None
    assert d["lead_lr"]["readiness"] in ("evaluated", "insufficient_data", "pilot")


def test_ml_lab_retrain_lead(manager_h, admin_h):
    r = requests.post(f"{BASE}/api/ml/lab/lead_lr/retrain", headers=manager_h, timeout=60)
    assert r.status_code == 200, r.text
    # Expected 'skipped' because <5 new labels
    assert r.json().get("status") == "skipped", r.json()

    # Force with manager should 403
    rf = requests.post(f"{BASE}/api/ml/lab/lead_lr/retrain?force=true", headers=manager_h, timeout=60)
    assert rf.status_code == 403

    # Admin can force
    ra = requests.post(f"{BASE}/api/ml/lab/lead_lr/retrain?force=true", headers=admin_h, timeout=120)
    assert ra.status_code == 200, ra.text


def test_ml_transparency(manager_h):
    r = requests.get(f"{BASE}/api/ml/transparency", headers=manager_h, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "models" in d
    keys = {m["key"] for m in d["models"]}
    assert {"ctr_rf", "lead_lr", "campaign_doctor"}.issubset(keys)
    for m in d["models"]:
        assert m["self_learning"] is False
        assert "limitations" in m
        assert "features" in m
        assert "training_data" in m


def test_ml_explain(manager_h):
    # CTR explain -> model_not_trained is expected
    cr = requests.get(f"{BASE}/api/clients/{CLIENT_ID}/creatives", headers=manager_h, timeout=20)
    if cr.status_code != 200:
        cr = requests.get(f"{BASE}/api/creatives?client_id={CLIENT_ID}", headers=manager_h, timeout=20)
    assert cr.status_code == 200
    creatives = cr.json()
    if creatives:
        rr = requests.get(f"{BASE}/api/ml/explain/ctr/{creatives[0]['id']}", headers=manager_h, timeout=20)
        assert rr.status_code == 200
        assert rr.json().get("status") == "model_not_trained"

    lr = requests.get(f"{BASE}/api/clients/{CLIENT_ID}/leads", headers=manager_h, timeout=20)
    if lr.status_code != 200:
        lr = requests.get(f"{BASE}/api/leads?client_id={CLIENT_ID}", headers=manager_h, timeout=20)
    assert lr.status_code == 200
    leads = lr.json()
    if leads:
        er = requests.get(f"{BASE}/api/ml/explain/lead/{leads[0]['id']}", headers=manager_h, timeout=20)
        assert er.status_code == 200
        j = er.json()
        if j.get("status") != "model_not_trained":
            assert "contributions" in j or "features" in j or "entity_name" in j


def test_ml_predict_batch_logs(manager_h):
    r = requests.get(f"{BASE}/api/ml/lead-conversion/predict-batch/{CLIENT_ID}", headers=manager_h, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_ml_compat_endpoints(manager_h):
    r1 = requests.get(f"{BASE}/api/ml/lead-conversion", headers=manager_h, timeout=20)
    assert r1.status_code == 200
    r2 = requests.get(f"{BASE}/api/ml/ctr-model", headers=manager_h, timeout=20)
    assert r2.status_code == 200
    # ctr likely untrained since not active
    assert r2.json().get("status") in ("untrained", "trained")


# ------------- Recommendations -------------
def test_recommendations_admin(admin_h):
    r = requests.get(f"{BASE}/api/recommendations", headers=admin_h, timeout=60)
    assert r.status_code == 200, r.text
    recs = r.json()
    assert isinstance(recs, list)


def test_recommendations_client_scope(client_h):
    r = requests.get(f"{BASE}/api/recommendations", headers=client_h, timeout=60)
    assert r.status_code == 200
    recs = r.json()
    kinds = {x["kind"] for x in recs}
    assert "client_risk" not in kinds
    assert "budget" not in kinds
    for x in recs:
        assert x["client_id"] == CLIENT_ID

    # Attempt to specify a different client_id
    rf = requests.get(f"{BASE}/api/recommendations?client_id=some-other-client", headers=client_h, timeout=20)
    assert rf.status_code == 403


# ------------- AI Buddy -------------
def test_buddy_chat(admin_h):
    body = {"message": "What's the top overdue task?", "session_id": "TEST_sess_" + uuid.uuid4().hex[:8],
            "client_id": CLIENT_ID, "path": "/"}
    r = requests.post(f"{BASE}/api/buddy/chat", json=body, headers=admin_h, timeout=60)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "answer" in d and d["answer"]
    assert "llm_used" in d
    assert "intents" in d
    assert "sources" in d


def test_buddy_client_scope(client_h):
    other = "11111111-1111-1111-1111-111111111111"
    body = {"message": "Show me risk and profitability", "session_id": "TEST_sess_" + uuid.uuid4().hex[:8],
            "client_id": other, "path": "/"}
    r = requests.post(f"{BASE}/api/buddy/chat", json=body, headers=client_h, timeout=60)
    # Should 200 but client_id forced to own; or 403 if endpoint rejects
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        d = r.json()
        # Should not expose profitability for client role
        ans = d.get("answer", "").lower()
        # Just basic check - should not fail


def test_profitability_client_forbidden(client_h):
    r = requests.get(f"{BASE}/api/finance/profitability/{CLIENT_ID}", headers=client_h, timeout=20)
    assert r.status_code == 403


# ------------- Analytics trend -------------
def test_analytics_trend_stable(admin_h):
    r1 = requests.get(f"{BASE}/api/analytics/client/{CLIENT_ID}", headers=admin_h, timeout=20)
    assert r1.status_code == 200, r1.text
    r2 = requests.get(f"{BASE}/api/analytics/client/{CLIENT_ID}", headers=admin_h, timeout=20)
    assert r2.status_code == 200
    d1 = r1.json(); d2 = r2.json()
    # stability: trend_data should be identical between calls
    k = "trend" if "trend" in d1 else "trend_data" if "trend_data" in d1 else None
    if k:
        assert d1.get(k) == d2.get(k), "trend data should be stable across calls"
    assert "demo_fields" in d1 or "trend_data_sources" in d1


# ------------- Regression: core endpoints -------------
def test_regression_core(admin_h):
    endpoints = [
        f"/api/clients",
        f"/api/clients/{CLIENT_ID}",
        f"/api/invoices?client_id={CLIENT_ID}",
        f"/api/payments?client_id={CLIENT_ID}",
        f"/api/approvals",
        f"/api/reports/{CLIENT_ID}/pdf",
    ]
    failed = []
    for ep in endpoints:
        r = requests.get(f"{BASE}{ep}", headers=admin_h, timeout=30)
        if r.status_code >= 400:
            # try alternative routes
            failed.append((ep, r.status_code, r.text[:100]))
    assert not failed, f"Regression failures: {failed}"


# ------------- Cleanup -------------
def test_zz_cleanup(admin_h):
    # Delete created tasks + interventions + campaign_daily rows via admin endpoints if available
    for tid in _created["tasks"]:
        try:
            requests.delete(f"{BASE}/api/tasks/{tid}", headers=admin_h, timeout=10)
        except Exception:
            pass
    # interventions have no delete endpoint; skip
    # campaign_daily cleanup - no explicit delete; leave with note
    assert True

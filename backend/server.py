from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import random
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Dict

import bcrypt
import jwt
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

from ml import (linear_forecast, zscore_anomalies, ema, score_lead,
                cluster_clients, campaign_efficiency_index, pearson_correlation,
                score_creative, rank_creatives, compute_ab_winner,
                prediction_error_stats, compute_client_risk,
                train_ctr_model, predict_ctr_rf, get_trained_ctr_model,
                train_lead_conversion, predict_lead_conversion, get_trained_lead_model)
from integrations import REGISTRY as INTEGRATION_REGISTRY, get_integration

# ---------- Setup ----------
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
JWT_SECRET = os.environ['JWT_SECRET']
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'finvora@gmail.com')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Vitronx@2026')
JWT_ALG = "HS256"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="VITRONX API")
api = APIRouter(prefix="/api")

logger = logging.getLogger("vitronx")
logging.basicConfig(level=logging.INFO)

# ---------- Auth Helpers ----------
def hash_pwd(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_pwd(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

def make_token(user_id: str, email: str, role: str) -> str:
    payload = {"sub": user_id, "email": email, "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user

def require_role(*roles):
    async def checker(user: dict = Depends(get_current_user)):
        if user["role"] not in roles and user["role"] != "super_admin":
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker

# ---------- Models ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id() -> str:
    return str(uuid.uuid4())

class LoginReq(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    avatar: Optional[str] = None
    department: Optional[str] = None

class ClientIn(BaseModel):
    name: str
    industry: str
    website: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    address: Optional[str] = ""
    account_manager_id: Optional[str] = None
    monthly_retainer: float = 0
    status: str = "Active"
    logo_color: Optional[str] = None
    notes: Optional[str] = ""
    primary_contact: Optional[str] = ""

class CampaignIn(BaseModel):
    client_id: str
    name: str
    objective: str = "Lead Generation"
    platform: str = "Meta Ads"
    status: str = "Active"
    budget: float = 0
    spend: float = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0

class TaskIn(BaseModel):
    client_id: Optional[str] = None
    project_id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    assignee_id: Optional[str] = None
    priority: str = "Medium"
    status: str = "To Do"
    due_date: Optional[str] = None

class ContentIn(BaseModel):
    client_id: str
    title: str
    content_type: str = "Social Post"
    platform: str = "Instagram"
    caption: Optional[str] = ""
    hashtags: Optional[str] = ""
    status: str = "Idea"
    publish_date: Optional[str] = None
    assignee_id: Optional[str] = None

class ProjectIn(BaseModel):
    client_id: str
    name: str
    description: Optional[str] = ""
    status: str = "Active"
    priority: str = "Medium"
    budget: float = 0
    progress: int = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class LeadIn(BaseModel):
    client_id: str
    name: str
    company: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    source: str = "Website"
    status: str = "New"
    value: float = 0
    notes: Optional[str] = ""

class ApprovalAction(BaseModel):
    action: str  # approve/reject/request_changes
    comment: Optional[str] = ""

class AIQuery(BaseModel):
    prompt: str
    client_id: Optional[str] = None
    kind: str = "insight"  # insight | recommendation | caption

# ---------- Utility ----------
def strip_id(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc.pop("_id", None)
    return doc

async def list_col(col, q: dict = None, limit: int = 500) -> List[dict]:
    q = q or {}
    docs = await col.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return docs

# ---------- AUTH ROUTES ----------
@api.post("/auth/login")
async def login(body: LoginReq, response: Response):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_pwd(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = make_token(user["id"], user["email"], user["role"])
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none",
                        max_age=7*24*3600, path="/")
    user.pop("_id", None); user.pop("password_hash", None)
    return {"user": user, "token": token}

@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

# ---------- CLIENTS ----------
@api.get("/clients")
async def list_clients(user: dict = Depends(get_current_user)):
    q = {}
    if user["role"] == "client":
        q = {"id": user.get("client_id")}
    elif user["role"] == "account_manager":
        q = {"account_manager_id": user["id"]}
    clients = await list_col(db.clients, q)
    # enrich with counts
    for c in clients:
        c["active_projects"] = await db.projects.count_documents({"client_id": c["id"], "status": "Active"})
        c["active_campaigns"] = await db.campaigns.count_documents({"client_id": c["id"], "status": "Active"})
        c["pending_approvals"] = await db.content.count_documents({"client_id": c["id"], "status": "Client Review"})
    return clients

@api.post("/clients")
async def create_client(body: ClientIn, user: dict = Depends(require_role("agency_admin", "account_manager"))):
    doc = body.model_dump()
    doc["id"] = new_id()
    doc["created_at"] = now_iso()
    doc["health_score"] = random.randint(72, 94)
    doc["logo_color"] = doc.get("logo_color") or random.choice(["#FF9F1C","#00E5FF","#10B981","#F43F5E","#8B5CF6"])
    await db.clients.insert_one(doc)
    strip_id(doc)
    return doc

@api.get("/clients/{cid}")
async def get_client(cid: str, user: dict = Depends(get_current_user)):
    c = await db.clients.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Client not found")
    if user["role"] == "client" and user.get("client_id") != cid:
        raise HTTPException(403, "Forbidden")
    return c

@api.patch("/clients/{cid}")
async def update_client(cid: str, body: dict, user: dict = Depends(require_role("agency_admin","account_manager"))):
    body.pop("id", None); body.pop("_id", None)
    await db.clients.update_one({"id": cid}, {"$set": body})
    return await db.clients.find_one({"id": cid}, {"_id": 0})

@api.delete("/clients/{cid}")
async def delete_client(cid: str, user: dict = Depends(require_role("agency_admin"))):
    await db.clients.delete_one({"id": cid})
    return {"ok": True}

# ---------- GENERIC CRUD FACTORY ----------
def crud_for(col_name: str, InModel):
    async def list_items(client_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        q = {}
        if client_id: q["client_id"] = client_id
        if user["role"] == "client":
            q["client_id"] = user.get("client_id")
        return await list_col(db[col_name], q)

    async def create_item(body: InModel, user: dict = Depends(get_current_user)):
        doc = body.model_dump()
        doc["id"] = new_id(); doc["created_at"] = now_iso(); doc["created_by"] = user["id"]
        await db[col_name].insert_one(doc)
        strip_id(doc); return doc

    async def update_item(item_id: str, body: dict, user: dict = Depends(get_current_user)):
        body.pop("id", None); body.pop("_id", None)
        body["updated_at"] = now_iso()
        await db[col_name].update_one({"id": item_id}, {"$set": body})
        return await db[col_name].find_one({"id": item_id}, {"_id": 0})

    async def delete_item(item_id: str, user: dict = Depends(get_current_user)):
        await db[col_name].delete_one({"id": item_id})
        return {"ok": True}

    return list_items, create_item, update_item, delete_item

# Campaigns
_lc, _cc, _uc, _dc = crud_for("campaigns", CampaignIn)
api.add_api_route("/campaigns", _lc, methods=["GET"])
api.add_api_route("/campaigns", _cc, methods=["POST"])
api.add_api_route("/campaigns/{item_id}", _uc, methods=["PATCH"])
api.add_api_route("/campaigns/{item_id}", _dc, methods=["DELETE"])

# Tasks
_lt, _ct, _ut, _dt = crud_for("tasks", TaskIn)
api.add_api_route("/tasks", _lt, methods=["GET"])
api.add_api_route("/tasks", _ct, methods=["POST"])
api.add_api_route("/tasks/{item_id}", _ut, methods=["PATCH"])
api.add_api_route("/tasks/{item_id}", _dt, methods=["DELETE"])

# Content
_lct, _cct, _uct, _dct = crud_for("content", ContentIn)
api.add_api_route("/content", _lct, methods=["GET"])
api.add_api_route("/content", _cct, methods=["POST"])
api.add_api_route("/content/{item_id}", _uct, methods=["PATCH"])
api.add_api_route("/content/{item_id}", _dct, methods=["DELETE"])

# Projects
_lp, _cp, _up, _dp = crud_for("projects", ProjectIn)
api.add_api_route("/projects", _lp, methods=["GET"])
api.add_api_route("/projects", _cp, methods=["POST"])
api.add_api_route("/projects/{item_id}", _up, methods=["PATCH"])
api.add_api_route("/projects/{item_id}", _dp, methods=["DELETE"])

# Leads
_ll, _cl, _ul, _dl = crud_for("leads", LeadIn)
api.add_api_route("/leads", _ll, methods=["GET"])
api.add_api_route("/leads", _cl, methods=["POST"])
api.add_api_route("/leads/{item_id}", _ul, methods=["PATCH"])
api.add_api_route("/leads/{item_id}", _dl, methods=["DELETE"])

# ---------- APPROVALS ----------
@api.post("/content/{cid}/approval")
async def submit_approval(cid: str, action: ApprovalAction, user: dict = Depends(get_current_user)):
    content = await db.content.find_one({"id": cid})
    if not content:
        raise HTTPException(404, "Content not found")
    new_status = {"approve": "Approved", "reject": "Rejected", "request_changes": "Design", "submit": "Client Review"}.get(action.action, content.get("status"))
    await db.content.update_one({"id": cid}, {"$set": {"status": new_status, "updated_at": now_iso()}})
    await db.approvals.insert_one({
        "id": new_id(), "content_id": cid, "action": action.action, "comment": action.comment,
        "user_id": user["id"], "user_name": user["name"], "created_at": now_iso(),
        "client_id": content.get("client_id")
    })
    await db.activity.insert_one({
        "id": new_id(), "client_id": content.get("client_id"), "user_id": user["id"],
        "user_name": user["name"], "action": f"{action.action}d content: {content.get('title')}",
        "created_at": now_iso()
    })
    return {"ok": True, "status": new_status}

@api.get("/approvals")
async def list_approvals(client_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"status": "Client Review"}
    if client_id: q["client_id"] = client_id
    if user["role"] == "client":
        q["client_id"] = user.get("client_id")
    return await list_col(db.content, q)

# ---------- TEAM ----------
@api.get("/team")
async def list_team(user: dict = Depends(get_current_user)):
    users = await db.users.find({"role": {"$ne": "client"}}, {"_id": 0, "password_hash": 0}).to_list(200)
    for u in users:
        u["active_tasks"] = await db.tasks.count_documents({"assignee_id": u["id"], "status": {"$ne": "Completed"}})
    return users

# ---------- ACTIVITY ----------
@api.get("/activity")
async def get_activity(client_id: Optional[str] = None, limit: int = 30, user: dict = Depends(get_current_user)):
    q = {}
    if client_id: q["client_id"] = client_id
    if user["role"] == "client": q["client_id"] = user.get("client_id")
    return await db.activity.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)

# ---------- NOTIFICATIONS (basic — extended in Phase 2 below) ----------

# ---------- ANALYTICS / DASHBOARDS ----------
@api.get("/analytics/agency")
async def agency_dashboard(user: dict = Depends(get_current_user)):
    clients = await db.clients.find({}, {"_id": 0}).to_list(500)
    campaigns = await db.campaigns.find({}, {"_id": 0}).to_list(500)
    tasks = await db.tasks.find({}, {"_id": 0}).to_list(500)
    content = await db.content.find({}, {"_id": 0}).to_list(500)
    leads = await db.leads.find({}, {"_id": 0}).to_list(500)

    total_spend = sum(c.get("spend", 0) for c in campaigns)
    total_revenue = sum(c.get("revenue", 0) for c in campaigns)
    total_conv = sum(c.get("conversions", 0) for c in campaigns)
    roas = round(total_revenue / total_spend, 2) if total_spend else 0
    retainer = sum(c.get("monthly_retainer", 0) for c in clients)
    avg_health = round(sum(c.get("health_score", 0) for c in clients) / max(len(clients), 1), 1)

    # 12-week trend
    trend = []
    for i in range(12):
        wk = datetime.now(timezone.utc) - timedelta(weeks=11-i)
        trend.append({
            "week": wk.strftime("%b %d"),
            "spend": int(total_spend / 12 * (0.7 + random.random() * 0.6)),
            "revenue": int(total_revenue / 12 * (0.7 + random.random() * 0.6)),
            "leads": int(len(leads) / 12 * (0.5 + random.random())),
        })

    return {
        "kpis": {
            "total_clients": len(clients),
            "active_campaigns": sum(1 for c in campaigns if c.get("status") == "Active"),
            "active_projects": await db.projects.count_documents({"status": "Active"}),
            "tasks_due_today": sum(1 for t in tasks if t.get("status") != "Completed"),
            "pending_approvals": sum(1 for c in content if c.get("status") == "Client Review"),
            "monthly_revenue": total_revenue,
            "monthly_retainer": retainer,
            "monthly_spend": total_spend,
            "total_leads": len(leads),
            "avg_roas": roas,
            "avg_health": avg_health,
        },
        "trend": trend,
        "clients": [
            {"id": c["id"], "name": c["name"], "industry": c["industry"], "health": c.get("health_score", 0),
             "logo_color": c.get("logo_color", "#FF9F1C"),
             "monthly_retainer": c.get("monthly_retainer", 0),
             "campaigns": sum(1 for k in campaigns if k.get("client_id") == c["id"]),
             "leads": sum(1 for l in leads if l.get("client_id") == c["id"])}
            for c in clients
        ]
    }

@api.get("/analytics/client/{cid}")
async def client_dashboard(cid: str, user: dict = Depends(get_current_user)):
    if user["role"] == "client" and user.get("client_id") != cid:
        raise HTTPException(403, "Forbidden")
    campaigns = await db.campaigns.find({"client_id": cid}, {"_id": 0}).to_list(500)
    leads = await db.leads.find({"client_id": cid}, {"_id": 0}).to_list(500)
    content = await db.content.find({"client_id": cid}, {"_id": 0}).to_list(500)
    tasks = await db.tasks.find({"client_id": cid}, {"_id": 0}).to_list(500)

    spend = sum(c.get("spend", 0) for c in campaigns)
    revenue = sum(c.get("revenue", 0) for c in campaigns)
    imp = sum(c.get("impressions", 0) for c in campaigns)
    clk = sum(c.get("clicks", 0) for c in campaigns)
    conv = sum(c.get("conversions", 0) for c in campaigns)
    ctr = round(clk / imp * 100, 2) if imp else 0
    cpc = round(spend / clk, 2) if clk else 0
    cpa = round(spend / conv, 2) if conv else 0
    roas = round(revenue / spend, 2) if spend else 0

    # 30-day trend from stored daily metrics
    since = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    agg = await db.campaign_daily.aggregate([
        {"$match": {"client_id": cid, "date": {"$gte": since}}},
        {"$group": {"_id": "$date", "impressions": {"$sum": "$impressions"}, "clicks": {"$sum": "$clicks"},
                    "conversions": {"$sum": "$conversions"}, "spend": {"$sum": "$spend"}}},
        {"$sort": {"_id": 1}}]).to_list(60)
    trend = [{"date": datetime.fromisoformat(a["_id"]).strftime("%b %d"), "impressions": a["impressions"],
              "clicks": a["clicks"], "conversions": a["conversions"], "spend": round(a["spend"])} for a in agg]
    trend_sources = await db.campaign_daily.distinct("data_source", {"client_id": cid})

    platform_split = {}
    for c in campaigns:
        p = c.get("platform", "Other")
        platform_split[p] = platform_split.get(p, 0) + c.get("spend", 0)

    return {
        "kpis": {
            "followers": random.randint(45000, 180000),
            "engagement_rate": round(random.uniform(3.2, 7.8), 2),
            "reach": random.randint(200000, 900000),
            "website_visitors": random.randint(12000, 68000),
            "leads": len(leads),
            "conversions": conv,
            "spend": spend, "revenue": revenue,
            "roas": roas, "cpa": cpa, "cpc": cpc, "ctr": ctr,
            "seo_score": random.randint(62, 91),
            "pending_content": sum(1 for c in content if c.get("status") == "Client Review"),
            "open_tasks": sum(1 for t in tasks if t.get("status") != "Completed"),
        },
        "trend": trend,
        "trend_data_sources": trend_sources,
        "demo_fields": ["followers", "engagement_rate", "reach", "website_visitors", "seo_score"],
        "platform_split": [{"name": k, "value": v} for k, v in platform_split.items()],
        "lead_funnel": [
            {"stage": "New", "count": sum(1 for l in leads if l.get("status") == "New")},
            {"stage": "Contacted", "count": sum(1 for l in leads if l.get("status") == "Contacted")},
            {"stage": "Qualified", "count": sum(1 for l in leads if l.get("status") == "Qualified")},
            {"stage": "Proposal", "count": sum(1 for l in leads if l.get("status") == "Proposal")},
            {"stage": "Won", "count": sum(1 for l in leads if l.get("status") == "Won")},
        ]
    }

@api.get("/seo/{cid}")
async def seo_metrics(cid: str, user: dict = Depends(get_current_user)):
    kws = [
        {"keyword": "luxury skincare online", "position": 3, "prev": 5, "volume": 12000, "difficulty": 62},
        {"keyword": "organic serum india", "position": 7, "prev": 9, "volume": 8400, "difficulty": 48},
        {"keyword": "premium moisturizer", "position": 12, "prev": 8, "volume": 22000, "difficulty": 71},
        {"keyword": "anti aging cream", "position": 5, "prev": 6, "volume": 34000, "difficulty": 78},
        {"keyword": "vitamin c serum", "position": 2, "prev": 4, "volume": 45000, "difficulty": 74},
    ]
    return {
        "score": random.randint(72, 88),
        "organic_traffic": random.randint(18000, 42000),
        "keywords_tracked": len(kws),
        "backlinks": random.randint(1200, 4800),
        "domain_authority": random.randint(38, 62),
        "keywords": kws,
    }

# ---------- AI INSIGHTS ----------
async def gen_ai_text(prompt: str, sys: str) -> str:
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"vitronx-{new_id()}",
            system_message=sys,
        ).with_model("gemini", "gemini-3.1-pro-preview")
        resp = await chat.send_message(UserMessage(text=prompt))
        return resp
    except Exception as e:
        logger.warning(f"AI generation failed: {e}")
        return None

@api.get("/ai/insights/{cid}")
async def ai_insights(cid: str, user: dict = Depends(get_current_user)):
    existing = await db.ai_insights.find({"client_id": cid}, {"_id": 0}).sort("created_at", -1).to_list(20)
    return existing

@api.post("/ai/generate/{cid}")
async def generate_insights(cid: str, user: dict = Depends(get_current_user)):
    client = await db.clients.find_one({"id": cid}, {"_id": 0})
    if not client:
        raise HTTPException(404, "Client not found")
    campaigns = await db.campaigns.find({"client_id": cid}, {"_id": 0}).to_list(50)
    leads = await db.leads.find({"client_id": cid}, {"_id": 0}).to_list(200)

    # Rule-based insights
    spend = sum(c.get("spend", 0) for c in campaigns)
    revenue = sum(c.get("revenue", 0) for c in campaigns)
    roas = revenue / spend if spend else 0

    insights = []
    if roas > 3:
        insights.append({
            "title": "Scale winning campaigns",
            "category": "Advertising",
            "priority": "High",
            "confidence": 92,
            "evidence": f"Blended ROAS is {roas:.2f}x across {len(campaigns)} campaigns with total revenue ${revenue:,.0f}.",
            "recommendation": "Increase top-3 campaign budgets by 15-25% while ROAS remains above 3.0x.",
            "expected_impact": "+18-24% incremental revenue in 30 days",
        })
    if len(leads) < 40:
        insights.append({
            "title": "Boost lead volume via mid-funnel content",
            "category": "Content",
            "priority": "Medium",
            "confidence": 84,
            "evidence": f"Only {len(leads)} leads recorded this period.",
            "recommendation": "Launch a 5-part educational Reel series with lead-magnet CTAs and retarget engagers.",
            "expected_impact": "+30-50% qualified leads in 21 days",
        })
    underperf = [c for c in campaigns if c.get("spend", 0) > 5000 and c.get("revenue", 0) / max(c.get("spend", 1), 1) < 1.5]
    if underperf:
        insights.append({
            "title": f"Pause or refresh {len(underperf)} underperforming campaign(s)",
            "category": "Advertising",
            "priority": "Critical",
            "confidence": 88,
            "evidence": f"{len(underperf)} campaigns burning >$5K with ROAS <1.5x: {', '.join([c['name'] for c in underperf[:3]])}.",
            "recommendation": "Rotate creative, tighten audience, or pause. Reallocate budget to top performers.",
            "expected_impact": "Save ~$" + f"{sum(c.get('spend',0) for c in underperf) * 0.35:,.0f} monthly",
        })

    # Optional AI summary
    ai_text = None
    try:
        sys_msg = f"You are the VITRONX AI strategist for {client['name']}, a {client['industry']} brand. Be concrete, use metrics, keep it to 3 short bullets."
        prompt = f"Given ROAS {roas:.2f}x, spend ${spend:,.0f}, revenue ${revenue:,.0f}, {len(leads)} leads, {len(campaigns)} campaigns — what should the agency do next week? 3 bullets."
        ai_text = await asyncio.wait_for(gen_ai_text(prompt, sys_msg), timeout=20)
    except Exception:
        ai_text = None

    saved = []
    for ins in insights:
        doc = {**ins, "id": new_id(), "client_id": cid, "created_at": now_iso(), "status": "New"}
        await db.ai_insights.insert_one(doc)
        strip_id(doc); saved.append(doc)

    return {"insights": saved, "ai_summary": ai_text or "Focus on scaling top-ROAS campaigns and refreshing creative on underperformers this week."}

@api.post("/ai/caption")
async def ai_caption(body: AIQuery, user: dict = Depends(get_current_user)):
    client_ctx = ""
    if body.client_id:
        c = await db.clients.find_one({"id": body.client_id}, {"_id": 0})
        if c: client_ctx = f"Brand: {c['name']} ({c['industry']}). "
    sys_msg = "You are a senior social media copywriter. Write punchy, brand-safe captions with 3-5 relevant hashtags."
    text = await gen_ai_text(f"{client_ctx}Write an Instagram caption for: {body.prompt}", sys_msg)
    return {"caption": text or "AI service temporarily unavailable. Please try again."}

# ---------- ML ENDPOINTS ----------
@api.get("/ml/forecast/{cid}")
async def ml_forecast(cid: str, metric: str = "revenue", horizon: int = 7, user: dict = Depends(get_current_user)):
    """Linear regression forecast for revenue/spend/conversions/clicks/impressions."""
    dash = await client_dashboard(cid, user)
    key_map = {"revenue": "spend", "spend": "spend", "conversions": "conversions",
               "clicks": "clicks", "impressions": "impressions"}
    key = key_map.get(metric, "spend")
    series = [t[key] for t in dash["trend"]]
    fc = linear_forecast(series, horizon)
    smoothed = ema(series, alpha=0.3)
    anomalies = zscore_anomalies(series, threshold=1.8)
    labels = [t["date"] for t in dash["trend"]]
    return {"metric": metric, "history": series, "smoothed": smoothed,
            "forecast": fc["forecast"], "slope": fc["slope"], "r2": fc["r2"],
            "trend": fc["trend"], "labels": labels, "anomalies": anomalies}

@api.get("/ml/lead-scoring/{cid}")
async def ml_lead_scoring(cid: str, user: dict = Depends(get_current_user)):
    """Score every lead with logistic model. Returns leads sorted by score desc."""
    if user["role"] == "client" and user.get("client_id") != cid:
        raise HTTPException(403, "Forbidden")
    leads = await db.leads.find({"client_id": cid}, {"_id": 0}).to_list(500)
    scored = []
    for l in leads:
        s = score_lead(l)
        scored.append({**l, "ml_score": s["score"], "ml_tier": s["tier"]})
    scored.sort(key=lambda x: -x["ml_score"])
    hot = sum(1 for s in scored if s["ml_tier"] == "hot")
    warm = sum(1 for s in scored if s["ml_tier"] == "warm")
    cold = sum(1 for s in scored if s["ml_tier"] == "cold")
    return {"leads": scored[:50], "summary": {"hot": hot, "warm": warm, "cold": cold, "total": len(scored)}}

@api.get("/ml/client-clusters")
async def ml_client_clusters(user: dict = Depends(get_current_user)):
    """K-means clustering across all clients on [health, retainer, campaigns]."""
    clients = await db.clients.find({}, {"_id": 0}).to_list(500)
    for c in clients:
        c["campaigns"] = await db.campaigns.count_documents({"client_id": c["id"]})
    tiers = cluster_clients(clients, k=3)
    return [{"id": c["id"], "name": c["name"], "health_score": c["health_score"],
             "monthly_retainer": c["monthly_retainer"], "campaigns": c["campaigns"],
             "tier": tiers.get(c["id"], "Unclassified"),
             "logo_color": c.get("logo_color")} for c in clients]

@api.get("/ml/campaign-efficiency/{cid}")
async def ml_campaign_efficiency(cid: str, user: dict = Depends(get_current_user)):
    """Rank campaigns by composite efficiency index."""
    if user["role"] == "client" and user.get("client_id") != cid:
        raise HTTPException(403, "Forbidden")
    campaigns = await db.campaigns.find({"client_id": cid}, {"_id": 0}).to_list(500)
    for c in campaigns:
        c["efficiency_index"] = campaign_efficiency_index(c)
        c["roas"] = round(c.get("revenue", 0) / max(c.get("spend", 1), 1), 2)
    campaigns.sort(key=lambda x: -x["efficiency_index"])
    return campaigns

@api.get("/ml/anomalies/{cid}")
async def ml_anomalies(cid: str, user: dict = Depends(get_current_user)):
    """Detect spikes/drops in daily spend, conversions across trend."""
    dash = await client_dashboard(cid, user)
    trend = dash["trend"]
    result = {}
    for metric in ["spend", "conversions", "clicks", "impressions"]:
        series = [t[metric] for t in trend]
        result[metric] = zscore_anomalies(series, threshold=1.8)
    # Correlations
    result["correlation_spend_conversions"] = pearson_correlation(
        [t["spend"] for t in trend], [t["conversions"] for t in trend])
    result["correlation_clicks_conversions"] = pearson_correlation(
        [t["clicks"] for t in trend], [t["conversions"] for t in trend])
    return result

# ---------- REPORTS ----------
@api.get("/reports/{cid}")
async def build_report(cid: str, user: dict = Depends(get_current_user)):
    dash = await client_dashboard(cid, user)
    c = await db.clients.find_one({"id": cid}, {"_id": 0})
    return {"client": c, "kpis": dash["kpis"], "period": "Last 30 days", "generated_at": now_iso()}

# ---------- SEED ----------
async def seed_all():
    if await db.users.find_one({"email": ADMIN_EMAIL}):
        # Ensure admin password matches env
        u = await db.users.find_one({"email": ADMIN_EMAIL})
        if not verify_pwd(ADMIN_PASSWORD, u.get("password_hash","")):
            await db.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"password_hash": hash_pwd(ADMIN_PASSWORD)}})
        return

    # ---- Users ----
    users_seed = [
        {"email": ADMIN_EMAIL, "name": "Aditya Kumar", "role": "agency_admin", "password": ADMIN_PASSWORD, "department": "Leadership"},
        {"email": "sarah.manager@vitronx.demo", "name": "Sarah Chen", "role": "account_manager", "password": "Demo@2026", "department": "Accounts"},
        {"email": "riya.designer@vitronx.demo", "name": "Riya Sharma", "role": "designer", "password": "Demo@2026", "department": "Creative"},
        {"email": "arjun.marketer@vitronx.demo", "name": "Arjun Patel", "role": "marketer", "password": "Demo@2026", "department": "Performance"},
        {"email": "priya.writer@vitronx.demo", "name": "Priya Menon", "role": "marketer", "password": "Demo@2026", "department": "Content"},
        {"email": "client@vitronx.demo", "name": "Rahul Malhotra", "role": "client", "password": "Demo@2026", "department": "Client"},
    ]
    user_ids = {}
    for u in users_seed:
        doc = {"id": new_id(), "email": u["email"].lower(), "name": u["name"], "role": u["role"],
               "password_hash": hash_pwd(u["password"]), "department": u["department"],
               "avatar": None, "created_at": now_iso()}
        user_ids[u["email"]] = doc["id"]
        await db.users.insert_one(doc)

    # ---- Clients ----
    clients_data = [
        {"name": "Lumière Cosmetics", "industry": "Luxury Beauty", "logo_color": "#FF9F1C", "monthly_retainer": 45000, "primary_contact": "Rahul Malhotra"},
        {"name": "VerdeLife Wellness", "industry": "Healthcare & Wellness", "logo_color": "#10B981", "monthly_retainer": 38000, "primary_contact": "Kavya Iyer"},
        {"name": "Meridian Estates", "industry": "Luxury Real Estate", "logo_color": "#00E5FF", "monthly_retainer": 62000, "primary_contact": "Vikram Shah"},
        {"name": "Saffron & Smoke", "industry": "Restaurant Chain", "logo_color": "#F43F5E", "monthly_retainer": 28000, "primary_contact": "Ananya Roy"},
        {"name": "NexaLoop Technologies", "industry": "SaaS / B2B Tech", "logo_color": "#8B5CF6", "monthly_retainer": 55000, "primary_contact": "Karan Mehta"},
    ]
    client_ids = []
    for i, cd in enumerate(clients_data):
        cid = new_id(); client_ids.append(cid)
        await db.clients.insert_one({
            "id": cid, "name": cd["name"], "industry": cd["industry"],
            "logo_color": cd["logo_color"], "monthly_retainer": cd["monthly_retainer"],
            "primary_contact": cd["primary_contact"],
            "website": f"https://{cd['name'].lower().replace(' ','').replace('&','and')}.com",
            "email": f"contact@{cd['name'].lower().replace(' ','')}.com",
            "phone": f"+91 98{random.randint(10000000,99999999)}",
            "address": "Mumbai, India" if i%2==0 else "Bengaluru, India",
            "account_manager_id": user_ids["sarah.manager@vitronx.demo"],
            "status": "Active", "health_score": random.randint(74, 93),
            "created_at": now_iso(), "notes": ""
        })
    # Assign client user to first client
    await db.users.update_one({"email": "client@vitronx.demo"}, {"$set": {"client_id": client_ids[0]}})

    # ---- Projects ----
    project_templates = ["Instagram Growth Q1", "Performance Marketing Blitz", "Website Redesign", "SEO Authority Build", "Brand Awareness Push"]
    for cid in client_ids:
        for pt in random.sample(project_templates, 3):
            await db.projects.insert_one({
                "id": new_id(), "client_id": cid, "name": pt,
                "status": random.choice(["Active","Planning","Active","Active","On Hold"]),
                "priority": random.choice(["High","Medium","Critical"]),
                "budget": random.randint(80000, 250000),
                "progress": random.randint(15, 88),
                "start_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(10,60))).isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=random.randint(20,90))).isoformat(),
                "description": f"Q1 initiative to accelerate {pt.lower()}", "created_at": now_iso()
            })

    # ---- Campaigns ----
    platforms = ["Meta Ads", "Google Ads", "LinkedIn", "YouTube"]
    objectives = ["Lead Generation", "Conversions", "Awareness", "Traffic"]
    for cid in client_ids:
        for i in range(random.randint(3, 6)):
            spend = random.randint(15000, 120000)
            conv = random.randint(20, 300)
            revenue = int(spend * random.uniform(0.8, 5.2))
            imp = random.randint(80000, 900000)
            clicks = int(imp * random.uniform(0.008, 0.048))
            await db.campaigns.insert_one({
                "id": new_id(), "client_id": cid,
                "name": f"{random.choice(['Summer','Festive','Retargeting','New Arrivals','Awareness','Conversion'])} - {random.choice(platforms).split()[0]} {i+1}",
                "platform": random.choice(platforms),
                "objective": random.choice(objectives),
                "status": random.choice(["Active","Active","Active","Paused","Completed"]),
                "budget": spend + random.randint(5000, 40000),
                "spend": spend, "impressions": imp, "clicks": clicks,
                "conversions": conv, "revenue": revenue,
                "start_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(5,45))).isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=random.randint(5,45))).isoformat(),
                "created_at": now_iso()
            })

    # ---- Content ----
    content_types = ["Reel", "Carousel", "Social Post", "Story", "Blog", "Ad Creative"]
    platforms_c = ["Instagram", "Facebook", "LinkedIn", "YouTube"]
    statuses = ["Idea","Brief","Design","Internal Review","Client Review","Approved","Scheduled","Published"]
    all_designers = [user_ids["riya.designer@vitronx.demo"], user_ids["priya.writer@vitronx.demo"]]
    for cid in client_ids:
        for i in range(random.randint(8, 14)):
            await db.content.insert_one({
                "id": new_id(), "client_id": cid,
                "title": f"{random.choice(['Behind the Scenes','Product Launch','Customer Story','How-To','Founder Note','Weekend Vibes'])} #{i+1}",
                "content_type": random.choice(content_types),
                "platform": random.choice(platforms_c),
                "status": random.choice(statuses),
                "caption": "Sample caption for demo content...",
                "hashtags": "#brand #marketing #growth",
                "publish_date": (datetime.now(timezone.utc) + timedelta(days=random.randint(-10,25))).isoformat(),
                "assignee_id": random.choice(all_designers),
                "created_at": now_iso()
            })

    # ---- Tasks ----
    task_names = ["Design new hero banner", "Write blog outline", "Shoot product photography", "Optimize landing page", "Analyze campaign performance", "Client review call", "Content calendar review", "SEO audit report", "Ad copy revisions", "Influencer outreach"]
    assignees = list(user_ids.values())
    for cid in client_ids:
        for i in range(random.randint(6, 12)):
            await db.tasks.insert_one({
                "id": new_id(), "client_id": cid,
                "name": random.choice(task_names),
                "assignee_id": random.choice(assignees),
                "status": random.choice(["To Do","In Progress","Review","Completed","To Do"]),
                "priority": random.choice(["Low","Medium","High","Critical"]),
                "due_date": (datetime.now(timezone.utc) + timedelta(days=random.randint(-3,20))).isoformat(),
                "description": "Auto-seeded demo task.",
                "created_at": now_iso()
            })

    # ---- Leads ----
    for cid in client_ids:
        for i in range(random.randint(10, 25)):
            await db.leads.insert_one({
                "id": new_id(), "client_id": cid,
                "name": random.choice(["Neha Kapoor","Rohan Bhatt","Ishaan Verma","Anaya Singh","Kabir Rao","Meera Nair","Zoya Khan","Aditya Roy"]),
                "company": random.choice(["Acme Corp","Nova Retail","Zenith Group","Peak Ventures","Astra Foods"]),
                "email": f"lead{i}@example.com",
                "phone": f"+91 98{random.randint(10000000,99999999)}",
                "source": random.choice(["Website","Instagram","Google Ads","Referral","LinkedIn"]),
                "status": random.choice(["New","Contacted","Qualified","Proposal","Won","Lost"]),
                "value": random.randint(5000, 250000),
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(0,45))).isoformat()
            })

    # ---- Activity ----
    for cid in client_ids:
        for i in range(5):
            await db.activity.insert_one({
                "id": new_id(), "client_id": cid,
                "user_id": random.choice(assignees), "user_name": random.choice(["Sarah Chen","Riya Sharma","Arjun Patel"]),
                "action": random.choice(["approved content: Summer Reel #4","launched campaign: Retargeting Meta","assigned task: Design hero banner","completed shoot: Product Photography","generated report: Monthly Performance"]),
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=random.randint(1,72))).isoformat()
            })

    logger.info("Seed complete.")

# ---------- Startup ----------
@app.on_event("startup")
async def on_start():
    await db.users.create_index("email", unique=True)
    await db.clients.create_index("id", unique=True)
    try:
        init_storage()
        logger.info("Emergent Object Storage initialized")
    except Exception as e:
        logger.warning(f"Object storage init failed: {e} (uploads will error until fixed)")
    await seed_all()
    await seed_phase2()
    await seed_phase3()
    await intel_router.startup()
    # Write test creds
    try:
        mem = Path("/app/memory")
        mem.mkdir(parents=True, exist_ok=True)
        (mem / "test_credentials.md").write_text(
            f"""# VITRONX Test Credentials

## Agency Admin (owner)
- Email: `{ADMIN_EMAIL}`
- Password: `{ADMIN_PASSWORD}`
- Role: agency_admin

## Account Manager
- Email: `sarah.manager@vitronx.demo`
- Password: `Demo@2026`

## Designer
- Email: `riya.designer@vitronx.demo`
- Password: `Demo@2026`

## Marketer
- Email: `arjun.marketer@vitronx.demo`
- Password: `Demo@2026`

## Client
- Email: `client@vitronx.demo`
- Password: `Demo@2026`

## Endpoints
- POST /api/auth/login
- GET /api/auth/me
- POST /api/auth/logout
"""
        )
    except Exception as e:
        logger.warning(f"Could not write test_credentials: {e}")

# ============================================================
# PHASE 2 — CREATIVE INTELLIGENCE, RISK, NOTIFICATIONS, BUDGET, INTEGRATIONS
# ============================================================

# ---------- Models ----------
class CreativeIn(BaseModel):
    client_id: str
    campaign_id: Optional[str] = None
    name: str
    content_type: str = "Social Post"
    platform: str = "Instagram"
    objective: str = "Awareness"
    caption: Optional[str] = ""
    cta: Optional[str] = ""
    offer: Optional[str] = ""
    hashtags: Optional[str] = ""
    thumbnail_url: Optional[str] = None
    variant_group: Optional[str] = None  # e.g. "diwali-2026" groups A/B/C together
    variant_label: Optional[str] = None  # "A", "B", "C"
    status: str = "Draft"
    actual_impressions: Optional[int] = None
    actual_clicks: Optional[int] = None
    actual_conversions: Optional[int] = None
    actual_spend: Optional[float] = None
    actual_revenue: Optional[float] = None
    actual_engagement: Optional[float] = None

class ABMetricsIn(BaseModel):
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0
    revenue: float = 0
    engagement: float = 0

class BudgetIn(BaseModel):
    client_id: str
    period: str = "monthly"  # monthly | campaign | project
    category: str = "advertising"  # advertising | production | seo | retainer | other
    allocated: float = 0
    campaign_id: Optional[str] = None
    project_id: Optional[str] = None
    notes: Optional[str] = ""

class InvoiceIn(BaseModel):
    client_id: str
    number: Optional[str] = None
    amount: float
    tax: float = 0
    due_date: Optional[str] = None
    status: str = "Draft"
    line_items: Optional[List[Dict[str, Any]]] = None

class NotificationIn(BaseModel):
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    kind: str
    severity: str = "info"  # info | warning | critical | success
    title: str
    message: str
    link: Optional[str] = None

class TaskFromInsight(BaseModel):
    insight_id: str
    assignee_id: Optional[str] = None
    due_days: int = 3

# ---------- Historical helpers ----------
async def historical_creative_stats(client_id: str) -> List[Dict[str, Any]]:
    docs = await db.creatives.find(
        {"client_id": client_id, "actual_impressions": {"$gt": 0}},
        {"_id": 0}
    ).to_list(500)
    for d in docs:
        imp, clk = d.get("actual_impressions", 0), d.get("actual_clicks", 0)
        d["actual_ctr"] = (clk / imp * 100) if imp else 0
    return docs

# ---------- Creative CRUD + Scoring ----------
@api.get("/creatives")
async def list_creatives(client_id: Optional[str] = None, variant_group: Optional[str] = None,
                          user: dict = Depends(get_current_user)):
    q = {}
    if client_id: q["client_id"] = client_id
    if variant_group: q["variant_group"] = variant_group
    if user["role"] == "client":
        q["client_id"] = user.get("client_id")
    return await list_col(db.creatives, q)

@api.post("/creatives")
async def create_creative(body: CreativeIn, user: dict = Depends(get_current_user)):
    doc = body.model_dump()
    doc["id"] = new_id(); doc["created_at"] = now_iso(); doc["created_by"] = user["id"]
    await db.creatives.insert_one(doc)
    strip_id(doc)
    # Compute score immediately for convenience
    historical = await historical_creative_stats(body.client_id)
    doc["score"] = score_creative(doc, historical)
    return doc

@api.patch("/creatives/{cid}")
async def update_creative(cid: str, body: dict, user: dict = Depends(get_current_user)):
    body.pop("id", None); body.pop("_id", None); body["updated_at"] = now_iso()
    await db.creatives.update_one({"id": cid}, {"$set": body})
    return await db.creatives.find_one({"id": cid}, {"_id": 0})

@api.delete("/creatives/{cid}")
async def delete_creative(cid: str, user: dict = Depends(get_current_user)):
    await db.creatives.delete_one({"id": cid})
    return {"ok": True}

@api.post("/creatives/{cid}/score")
async def score_one_creative(cid: str, user: dict = Depends(get_current_user)):
    c = await db.creatives.find_one({"id": cid}, {"_id": 0})
    if not c: raise HTTPException(404, "Creative not found")
    historical = await historical_creative_stats(c["client_id"])
    score = score_creative(c, historical)
    # Persist prediction for feedback loop
    await db.predictions.insert_one({
        "id": new_id(), "creative_id": cid, "client_id": c["client_id"],
        "model_name": score["model_name"], "model_version": score["model_version"],
        "predicted_ctr": score["predicted_ctr"],
        "predicted_engagement": score["predicted_engagement"],
        "composite_score": score["composite_score"],
        "confidence": score["confidence"],
        "created_at": now_iso(),
    })
    return score

@api.get("/creatives/rank/{client_id}")
async def rank_client_creatives(client_id: str, variant_group: Optional[str] = None,
                                  user: dict = Depends(get_current_user)):
    if user["role"] == "client" and user.get("client_id") != client_id:
        raise HTTPException(403, "Forbidden")
    q = {"client_id": client_id}
    if variant_group: q["variant_group"] = variant_group
    creatives = await db.creatives.find(q, {"_id": 0}).to_list(200)
    historical = await historical_creative_stats(client_id)
    ranked = rank_creatives(creatives, historical)
    return ranked

# ---------- A/B Testing ----------
@api.get("/ab/groups/{client_id}")
async def list_ab_groups(client_id: str, user: dict = Depends(get_current_user)):
    """Return distinct variant_groups with variant count + winner."""
    pipeline = [
        {"$match": {"client_id": client_id, "variant_group": {"$ne": None}}},
        {"$group": {"_id": "$variant_group", "count": {"$sum": 1},
                    "campaign_id": {"$first": "$campaign_id"}}}
    ]
    groups = await db.creatives.aggregate(pipeline).to_list(200)
    out = []
    for g in groups:
        variants = await db.creatives.find({"client_id": client_id, "variant_group": g["_id"]}, {"_id": 0}).to_list(20)
        winner = compute_ab_winner(variants)
        out.append({"group": g["_id"], "variants": len(variants),
                    "campaign_id": g.get("campaign_id"), "winner": winner})
    return out

@api.post("/ab/{creative_id}/record")
async def record_ab_metrics(creative_id: str, body: ABMetricsIn, user: dict = Depends(get_current_user)):
    """Record actual performance for a variant — closes the prediction feedback loop."""
    creative = await db.creatives.find_one({"id": creative_id})
    if not creative: raise HTTPException(404, "Creative not found")
    imp = body.impressions
    actual_ctr = (body.clicks / imp * 100) if imp else 0
    update = {
        "actual_impressions": body.impressions, "actual_clicks": body.clicks,
        "actual_conversions": body.conversions, "actual_spend": body.spend,
        "actual_revenue": body.revenue, "actual_engagement": body.engagement,
        "actual_ctr": round(actual_ctr, 3),
        "actual_recorded_at": now_iso(),
    }
    await db.creatives.update_one({"id": creative_id}, {"$set": update})
    # Update latest prediction with actual
    latest = await db.predictions.find_one({"creative_id": creative_id}, sort=[("created_at", -1)])
    if latest:
        await db.predictions.update_one({"id": latest["id"]}, {"$set": {
            "actual_ctr": round(actual_ctr, 3),
            "actual_recorded_at": now_iso(),
            "error_ctr": round(actual_ctr - latest.get("predicted_ctr", 0), 3),
        }})
    await db.activity.insert_one({
        "id": new_id(), "client_id": creative["client_id"], "user_id": user["id"],
        "user_name": user["name"],
        "action": f"recorded actual performance for creative: {creative.get('name')}",
        "created_at": now_iso()
    })
    return {"ok": True, "actual_ctr": round(actual_ctr, 3)}

# ---------- Prediction Accuracy ----------
@api.get("/ml/prediction-accuracy/{client_id}")
async def prediction_accuracy(client_id: str, user: dict = Depends(get_current_user)):
    """Compare predicted vs actual CTR for closed feedback loop."""
    if user["role"] == "client" and user.get("client_id") != client_id:
        raise HTTPException(403, "Forbidden")
    preds = await db.predictions.find(
        {"client_id": client_id, "actual_ctr": {"$exists": True}}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    pairs = [{"predicted": p["predicted_ctr"], "actual": p["actual_ctr"]} for p in preds]
    stats = prediction_error_stats(pairs)
    return {"stats": stats, "samples": preds[:50],
            "model": "vitronx-creative-v1", "metric": "CTR (%)"}

# ---------- Client Risk ----------
@api.get("/risk/{client_id}")
async def client_risk(client_id: str, user: dict = Depends(get_current_user)):
    if user["role"] == "client" and user.get("client_id") != client_id:
        raise HTTPException(403, "Forbidden")
    c = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not c: raise HTTPException(404, "Client not found")
    campaigns = await db.campaigns.find({"client_id": client_id}, {"_id": 0}).to_list(300)
    tasks = await db.tasks.find({"client_id": client_id}, {"_id": 0}).to_list(300)
    content = await db.content.find({"client_id": client_id}, {"_id": 0}).to_list(300)
    risk = compute_client_risk(c, campaigns, tasks, content)
    risk["client"] = {"id": c["id"], "name": c["name"], "industry": c["industry"], "logo_color": c.get("logo_color")}
    return risk

@api.get("/risk/agency/all")
async def agency_risk(user: dict = Depends(require_role("agency_admin","account_manager"))):
    clients = await db.clients.find({}, {"_id": 0}).to_list(500)
    out = []
    for c in clients:
        campaigns = await db.campaigns.find({"client_id": c["id"]}, {"_id": 0}).to_list(300)
        tasks = await db.tasks.find({"client_id": c["id"]}, {"_id": 0}).to_list(300)
        content = await db.content.find({"client_id": c["id"]}, {"_id": 0}).to_list(300)
        r = compute_client_risk(c, campaigns, tasks, content)
        out.append({"id": c["id"], "name": c["name"], "logo_color": c.get("logo_color"),
                    "industry": c["industry"], "health_score": c.get("health_score"),
                    **r})
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    out.sort(key=lambda x: (order.get(x["risk_level"], 4), -x["risk_score"]))
    return out

# ---------- Notifications (real, computed) ----------
@api.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    q = {}
    if user["role"] == "client":
        q = {"$or": [{"user_id": user["id"]}, {"client_id": user.get("client_id")}]}
    else:
        q = {"$or": [{"user_id": user["id"]}, {"user_id": None}]}
    docs = await db.notifications.find(q, {"_id": 0}).sort("created_at", -1).to_list(100)
    unread = sum(1 for d in docs if not d.get("read"))
    return {"notifications": docs, "unread": unread}

@api.post("/notifications/{nid}/read")
async def read_notification(nid: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"id": nid}, {"$set": {"read": True, "read_at": now_iso()}})
    return {"ok": True}

@api.post("/notifications/read-all")
async def read_all_notifications(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({}, {"$set": {"read": True, "read_at": now_iso()}})
    return {"ok": True}

@api.post("/notifications/compute")
async def compute_notifications(user: dict = Depends(require_role("agency_admin","account_manager"))):
    """Scan all clients and generate notifications for real conditions."""
    created = 0
    clients = await db.clients.find({}, {"_id": 0}).to_list(500)
    for c in clients:
        campaigns = await db.campaigns.find({"client_id": c["id"]}, {"_id": 0}).to_list(300)
        tasks = await db.tasks.find({"client_id": c["id"]}, {"_id": 0}).to_list(300)
        content = await db.content.find({"client_id": c["id"]}, {"_id": 0}).to_list(300)
        # ROAS drop
        for camp in campaigns:
            if camp.get("spend", 0) > 5000:
                roas = camp.get("revenue", 0) / camp["spend"]
                if roas < 1.2 and camp.get("status") == "Active":
                    key = f"roas-drop-{camp['id']}"
                    if not await db.notifications.find_one({"kind": key}):
                        await db.notifications.insert_one({
                            "id": new_id(), "kind": key, "user_id": None,
                            "client_id": c["id"], "campaign_id": camp["id"],
                            "severity": "critical",
                            "title": f"ROAS critical on {camp['name']}",
                            "message": f"{c['name']}: ROAS {roas:.2f}x on ${camp['spend']:,.0f} spend — review or pause",
                            "link": f"/workspace/{c['id']}",
                            "read": False, "created_at": now_iso()
                        }); created += 1
        # Approval backlog
        pending = [x for x in content if x.get("status") == "Client Review"]
        if len(pending) >= 3:
            key = f"approval-backlog-{c['id']}"
            if not await db.notifications.find_one({"kind": key, "read": False}):
                await db.notifications.insert_one({
                    "id": new_id(), "kind": key, "user_id": None,
                    "client_id": c["id"], "severity": "warning",
                    "title": f"Approval backlog for {c['name']}",
                    "message": f"{len(pending)} content items awaiting client approval",
                    "link": f"/workspace/{c['id']}",
                    "read": False, "created_at": now_iso()
                }); created += 1
        # Overdue tasks
        from datetime import datetime as _dt
        now = datetime.now(timezone.utc)
        overdue = [t for t in tasks if t.get("status") != "Completed" and t.get("due_date") and
                   _dt.fromisoformat(t["due_date"].replace("Z","+00:00")) < now]
        if len(overdue) >= 3:
            key = f"overdue-tasks-{c['id']}"
            if not await db.notifications.find_one({"kind": key, "read": False}):
                await db.notifications.insert_one({
                    "id": new_id(), "kind": key, "user_id": None,
                    "client_id": c["id"], "severity": "warning",
                    "title": f"Overdue tasks — {c['name']}",
                    "message": f"{len(overdue)} tasks past due date",
                    "link": f"/tasks",
                    "read": False, "created_at": now_iso()
                }); created += 1
    return {"created": created}

# ---------- Budgets ----------
@api.get("/budgets")
async def list_budgets(client_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {}
    if client_id: q["client_id"] = client_id
    if user["role"] == "client": q["client_id"] = user.get("client_id")
    budgets = await list_col(db.budgets, q)
    # Enrich with actual spend
    for b in budgets:
        spent = 0
        if b.get("campaign_id"):
            camp = await db.campaigns.find_one({"id": b["campaign_id"]})
            if camp: spent = camp.get("spend", 0)
        elif b.get("category") == "advertising":
            camps = await db.campaigns.find({"client_id": b["client_id"]}).to_list(100)
            spent = sum(c.get("spend", 0) for c in camps)
        b["spent"] = spent
        b["remaining"] = max(b["allocated"] - spent, 0)
        b["utilization_pct"] = round(spent / b["allocated"] * 100, 1) if b["allocated"] else 0
        if b["utilization_pct"] >= 100: b["status"] = "overspend"
        elif b["utilization_pct"] >= 85: b["status"] = "critical"
        elif b["utilization_pct"] >= 70: b["status"] = "warning"
        else: b["status"] = "healthy"
    return budgets

@api.post("/budgets")
async def create_budget(body: BudgetIn, user: dict = Depends(require_role("agency_admin","account_manager"))):
    doc = body.model_dump()
    doc["id"] = new_id(); doc["created_at"] = now_iso()
    await db.budgets.insert_one(doc); strip_id(doc); return doc

@api.delete("/budgets/{bid}")
async def delete_budget(bid: str, user: dict = Depends(require_role("agency_admin","account_manager"))):
    await db.budgets.delete_one({"id": bid}); return {"ok": True}

# ---------- Invoices ----------
@api.get("/invoices")
async def list_invoices(client_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {}
    if client_id: q["client_id"] = client_id
    if user["role"] == "client": q["client_id"] = user.get("client_id")
    return await list_col(db.invoices, q)

@api.post("/invoices")
async def create_invoice(body: InvoiceIn, user: dict = Depends(require_role("agency_admin","account_manager"))):
    doc = body.model_dump()
    doc["id"] = new_id(); doc["created_at"] = now_iso()
    if not doc.get("number"):
        n = await db.invoices.count_documents({})
        doc["number"] = f"VX-{2026}{n+1001}"
    doc["total"] = doc["amount"] + doc.get("tax", 0)
    await db.invoices.insert_one(doc); strip_id(doc); return doc

@api.patch("/invoices/{iid}")
async def update_invoice(iid: str, body: dict, user: dict = Depends(require_role("agency_admin","account_manager"))):
    body.pop("id", None); body.pop("_id", None)
    await db.invoices.update_one({"id": iid}, {"$set": body})
    return await db.invoices.find_one({"id": iid}, {"_id": 0})

# ---------- AI Insight → Task ----------
@api.post("/ai/insight-to-task")
async def insight_to_task(body: TaskFromInsight, user: dict = Depends(get_current_user)):
    insight = await db.ai_insights.find_one({"id": body.insight_id}, {"_id": 0})
    if not insight: raise HTTPException(404, "Insight not found")
    priority_map = {"Critical":"Critical","High":"High","Medium":"Medium","Low":"Low"}
    task = {
        "id": new_id(), "client_id": insight["client_id"],
        "name": f"AI Action: {insight['title']}",
        "description": f"{insight.get('recommendation','')}\n\nEvidence: {insight.get('evidence','')}",
        "assignee_id": body.assignee_id or user["id"],
        "priority": priority_map.get(insight.get("priority","Medium"),"Medium"),
        "status": "To Do",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=body.due_days)).isoformat(),
        "source": "ai_insight", "source_id": body.insight_id,
        "created_at": now_iso(), "created_by": user["id"],
    }
    await db.tasks.insert_one(task)
    await db.ai_insights.update_one({"id": body.insight_id}, {"$set": {"status": "Accepted", "task_id": task["id"]}})
    await db.activity.insert_one({
        "id": new_id(), "client_id": insight["client_id"], "user_id": user["id"],
        "user_name": user["name"],
        "action": f"created task from AI recommendation: {insight['title']}",
        "created_at": now_iso()
    })
    strip_id(task); return task

# ---------- Integrations ----------
@api.get("/integrations")
async def list_integrations(user: dict = Depends(get_current_user)):
    return [get_integration(k).status() for k in INTEGRATION_REGISTRY.keys()]

@api.get("/integrations/{provider}/preview")
async def integration_preview(provider: str, user: dict = Depends(require_role("agency_admin","account_manager"))):
    """Fetch a 7-day preview from the provider (demo mode by default)."""
    try:
        integ = get_integration(provider)
    except ValueError as e:
        raise HTTPException(404, str(e))
    since = (datetime.now(timezone.utc) - timedelta(days=6)).date().isoformat()
    until = datetime.now(timezone.utc).date().isoformat()
    try:
        data = await integ.fetch_metrics("demo-account", since, until)
        data = [d.to_dict() if hasattr(d, "to_dict") else d for d in data]
    except NotImplementedError as e:
        return {"mode": integ.mode, "status": "not_wired", "message": str(e), "data": []}
    return {"mode": integ.mode, "status": "ok",
            "note": "DEMO/SANDBOX data — clearly labeled. Not from live provider." if integ.mode == "demo" else "Live data.",
            "data": data}

# ---------- Enhanced Agency Command Center ----------
@api.get("/analytics/needs-attention")
async def needs_attention(user: dict = Depends(get_current_user)):
    """Aggregated priorities across the agency for the command center."""
    items = []
    clients = await db.clients.find({}, {"_id": 0}).to_list(500)
    from datetime import datetime as _dt
    now = datetime.now(timezone.utc)

    for c in clients:
        # ROAS drops
        camps = await db.campaigns.find({"client_id": c["id"], "status": "Active"}, {"_id": 0}).to_list(50)
        for camp in camps:
            if camp.get("spend", 0) > 5000:
                roas = camp.get("revenue", 0) / camp["spend"]
                if roas < 1.5:
                    items.append({
                        "severity": "critical" if roas < 1.0 else "high",
                        "kind": "roas_drop", "client_id": c["id"], "client_name": c["name"],
                        "logo_color": c.get("logo_color"),
                        "title": f"{c['name']} — {camp['name']} ROAS {roas:.2f}x",
                        "detail": f"Spend ${camp['spend']:,.0f} · Revenue ${camp.get('revenue',0):,.0f}",
                        "link": f"/workspace/{c['id']}", "score": (1.5 - roas) * 100
                    })
        # Approvals
        pending = await db.content.count_documents({"client_id": c["id"], "status": "Client Review"})
        if pending >= 2:
            items.append({
                "severity": "warning", "kind": "approvals",
                "client_id": c["id"], "client_name": c["name"], "logo_color": c.get("logo_color"),
                "title": f"{c['name']} — {pending} approvals pending",
                "detail": "Client review backlog", "link": f"/workspace/{c['id']}",
                "score": pending * 5,
            })
        # Overdue tasks
        tasks = await db.tasks.find({"client_id": c["id"], "status": {"$ne": "Completed"}}).to_list(100)
        overdue = [t for t in tasks if t.get("due_date") and _dt.fromisoformat(t["due_date"].replace("Z","+00:00")) < now]
        if len(overdue) >= 2:
            items.append({
                "severity": "warning", "kind": "overdue",
                "client_id": c["id"], "client_name": c["name"], "logo_color": c.get("logo_color"),
                "title": f"{c['name']} — {len(overdue)} overdue tasks",
                "detail": "Team execution risk", "link": f"/tasks", "score": len(overdue) * 4,
            })
    # Budget alerts
    budgets = await db.budgets.find({}, {"_id": 0}).to_list(500)
    for b in budgets:
        spent = 0
        if b.get("campaign_id"):
            camp = await db.campaigns.find_one({"id": b["campaign_id"]})
            if camp: spent = camp.get("spend", 0)
        util = spent / b["allocated"] * 100 if b.get("allocated") else 0
        if util >= 85:
            cli = next((c for c in clients if c["id"] == b["client_id"]), {})
            items.append({
                "severity": "critical" if util >= 100 else "warning",
                "kind": "budget", "client_id": b["client_id"], "client_name": cli.get("name","?"),
                "logo_color": cli.get("logo_color"),
                "title": f"{cli.get('name','?')} — budget at {util:.0f}%",
                "detail": f"${spent:,.0f} of ${b['allocated']:,.0f} used",
                "link": f"/workspace/{b['client_id']}", "score": util,
            })
    sev_order = {"critical": 0, "high": 1, "warning": 2, "info": 3}
    items.sort(key=lambda x: (sev_order.get(x["severity"], 4), -x.get("score", 0)))
    return items[:20]

# ---------- Seed additions (idempotent) ----------
async def seed_phase2():
    """Add creatives (with variant groups) and budgets on top of existing seed."""
    if await db.creatives.count_documents({}) > 0:
        return  # already seeded
    clients = await db.clients.find({}, {"_id": 0}).to_list(500)
    for c in clients:
        camps = await db.campaigns.find({"client_id": c["id"]}, {"_id": 0}).to_list(50)
        if not camps: continue
        # Create an A/B/C variant group for the first active campaign
        target = next((x for x in camps if x.get("status") == "Active"), camps[0])
        group = f"{c['name'].split()[0].lower()}-launch-2026"
        for label, ct, cta_offer in [
            ("A", "Reel", ("Shop Now", "Flat 25% off")),
            ("B", "Carousel", ("Learn More", "")),
            ("C", "Reel", ("Buy Now", "Bundle deal — Save 40%")),
        ]:
            imp = random.randint(15000, 90000)
            clk = int(imp * random.uniform(0.015, 0.045))
            conv = int(clk * random.uniform(0.03, 0.11))
            spend = round(clk * random.uniform(1.5, 4.5), 2)
            rev = round(conv * random.uniform(180, 620), 2)
            await db.creatives.insert_one({
                "id": new_id(), "client_id": c["id"], "campaign_id": target["id"],
                "name": f"{target['name']} — Variant {label}",
                "content_type": ct, "platform": target.get("platform","Meta Ads").replace(" Ads",""),
                "objective": target.get("objective","Awareness"),
                "caption": f"Discover {c['name']}'s latest — crafted for you. Tap the link in bio to explore.",
                "cta": cta_offer[0], "offer": cta_offer[1],
                "hashtags": "#" + " #".join(c['industry'].lower().split()) + " #brand #launch",
                "variant_group": group, "variant_label": label,
                "status": "Published",
                "actual_impressions": imp, "actual_clicks": clk,
                "actual_conversions": conv, "actual_spend": spend, "actual_revenue": rev,
                "actual_engagement": round(random.uniform(3.5, 8.5), 2),
                "actual_ctr": round(clk / imp * 100, 3) if imp else 0,
                "created_at": now_iso()
            })
        # Extra draft creative (no historical data)
        await db.creatives.insert_one({
            "id": new_id(), "client_id": c["id"], "campaign_id": target["id"],
            "name": f"{target['name']} — Draft Concept",
            "content_type": "Reel", "platform": "Instagram", "objective": "Engagement",
            "caption": "Behind the scenes with the team. Something exciting is coming.",
            "cta": "Follow", "offer": "", "hashtags": "#bts #comingsoon",
            "variant_group": None, "variant_label": None,
            "status": "Draft", "created_at": now_iso()
        })
        # Advertising budget
        allocated = round(sum(cp.get("budget", 0) for cp in camps) * 1.1, 2) or 100000
        await db.budgets.insert_one({
            "id": new_id(), "client_id": c["id"], "period": "monthly",
            "category": "advertising", "allocated": allocated,
            "notes": "Monthly ad spend budget", "created_at": now_iso()
        })
        # Sample invoice
        n = await db.invoices.count_documents({})
        await db.invoices.insert_one({
            "id": new_id(), "client_id": c["id"], "number": f"VX-2026{n+1001}",
            "amount": c.get("monthly_retainer", 25000),
            "tax": round(c.get("monthly_retainer", 25000) * 0.18, 2),
            "total": round(c.get("monthly_retainer", 25000) * 1.18, 2),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat(),
            "status": random.choice(["Sent","Paid","Sent"]),
            "line_items": [{"description": f"Monthly retainer — {c['name']}", "amount": c.get("monthly_retainer", 25000)}],
            "created_at": now_iso()
        })
    logger.info("Phase 2 seed complete.")


# ============================================================
# PHASE 3 — INDIA/GST INVOICES, UPLOADS, MESSAGING, SEARCH, DAILY BRIEF, RF MODEL
# ============================================================
import requests
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse, Response

# ---------- Emergent Object Storage ----------
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "vitronx"
_storage_key = None

def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init",
                          json={"emergent_key": os.environ.get("EMERGENT_LLM_KEY")}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                         headers={"X-Storage-Key": key, "Content-Type": content_type},
                         data=data, timeout=120)
    if resp.status_code == 404:
        # Key may be stale — re-init once
        key = init_storage(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                             headers={"X-Storage-Key": key, "Content-Type": content_type},
                             data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}",
                         headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}",
                             headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

ALLOWED_MIME = {"image/png","image/jpeg","image/gif","image/webp","image/svg+xml",
                "video/mp4","video/quicktime","video/webm",
                "application/pdf","application/msword","text/plain"}

# ---------- Payment / Invoice-GST models ----------
class PaymentIn(BaseModel):
    invoice_id: str
    amount: float
    payment_date: Optional[str] = None
    mode: str = "UPI"  # UPI, NEFT, RTGS, IMPS, Bank Transfer, Cheque, Cash, Other
    reference: Optional[str] = ""
    notes: Optional[str] = ""

class GSTInvoiceIn(BaseModel):
    client_id: str
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    line_items: List[Dict[str, Any]]  # [{description, hsn_sac, quantity, unit_price, discount}]
    gst_rate: float = 18
    agency_state: str = "Maharashtra"
    client_state: Optional[str] = "Maharashtra"
    client_gstin: Optional[str] = ""
    notes: Optional[str] = ""
    payment_terms: Optional[str] = "Net 15 days"

class MessageIn(BaseModel):
    thread_id: Optional[str] = None
    entity_type: str  # approval | task | campaign | content | general
    entity_id: Optional[str] = None
    client_id: str
    body: str

# ---------- INR / Indian financial year helpers ----------
def indian_fy() -> str:
    """Return current Indian financial year like '2026-27'."""
    now = datetime.now(timezone.utc)
    if now.month >= 4:
        return f"{now.year}-{str(now.year+1)[2:]}"
    return f"{now.year-1}-{str(now.year)[2:]}"

async def next_gst_invoice_number() -> str:
    fy = indian_fy()
    prefix = f"VTX/{fy}/"
    latest = await db.invoices.find({"number": {"$regex": f"^{prefix.replace('/', chr(92)+'/')}"}}).sort("created_at", -1).to_list(1)
    seq = 1
    if latest:
        try: seq = int(latest[0]["number"].split("/")[-1]) + 1
        except Exception: pass
    return f"{prefix}{seq:04d}"

# ---------- GST-aware Invoice endpoint (extends existing) ----------
@api.post("/invoices/gst")
async def create_gst_invoice(body: GSTInvoiceIn, user: dict = Depends(require_role("agency_admin","account_manager"))):
    """Create India GST-compliant invoice. Auto-splits CGST/SGST vs IGST based on states."""
    subtotal = 0
    for li in body.line_items:
        qty = float(li.get("quantity", 1))
        price = float(li.get("unit_price", 0))
        disc = float(li.get("discount", 0))
        li["taxable_value"] = round(qty * price - disc, 2)
        subtotal += li["taxable_value"]
    subtotal = round(subtotal, 2)
    intra_state = (body.client_state or "").strip().lower() == body.agency_state.strip().lower()
    gst = round(subtotal * body.gst_rate / 100, 2)
    if intra_state:
        cgst = round(gst / 2, 2); sgst = round(gst / 2, 2); igst = 0.0
    else:
        cgst = 0.0; sgst = 0.0; igst = gst
    grand_total = round(subtotal + cgst + sgst + igst, 2)
    doc = {
        "id": new_id(),
        "number": await next_gst_invoice_number(),
        "client_id": body.client_id,
        "invoice_date": body.invoice_date or datetime.now(timezone.utc).date().isoformat(),
        "due_date": body.due_date or (datetime.now(timezone.utc) + timedelta(days=15)).date().isoformat(),
        "line_items": body.line_items,
        "gst_rate": body.gst_rate,
        "agency_state": body.agency_state, "client_state": body.client_state,
        "client_gstin": body.client_gstin,
        "intra_state": intra_state,
        "subtotal": subtotal, "cgst": cgst, "sgst": sgst, "igst": igst,
        "total_tax": round(cgst + sgst + igst, 2), "grand_total": grand_total,
        "amount": subtotal, "tax": round(cgst + sgst + igst, 2), "total": grand_total,
        "status": "Draft", "paid_amount": 0, "remaining": grand_total,
        "currency": "INR",
        "notes": body.notes, "payment_terms": body.payment_terms,
        "created_at": now_iso(), "created_by": user["id"],
    }
    await db.invoices.insert_one(doc); strip_id(doc)
    await db.activity.insert_one({"id": new_id(), "client_id": body.client_id, "user_id": user["id"],
        "user_name": user["name"], "action": f"issued GST invoice {doc['number']} · ₹{grand_total:,.2f}",
        "created_at": now_iso()})
    return doc

@api.post("/invoices/{iid}/status")
async def update_invoice_status(iid: str, new_status: str, user: dict = Depends(require_role("agency_admin","account_manager"))):
    valid = ["Draft","Issued","Sent","Viewed","Partially_Paid","Paid","Overdue","Cancelled"]
    if new_status not in valid: raise HTTPException(400, f"Status must be one of {valid}")
    await db.invoices.update_one({"id": iid}, {"$set": {"status": new_status, "updated_at": now_iso()}})
    return await db.invoices.find_one({"id": iid}, {"_id": 0})

@api.post("/payments")
async def record_payment(body: PaymentIn, user: dict = Depends(require_role("agency_admin","account_manager"))):
    inv = await db.invoices.find_one({"id": body.invoice_id})
    if not inv: raise HTTPException(404, "Invoice not found")
    total = inv.get("grand_total") or inv.get("total") or 0
    paid_prev = inv.get("paid_amount", 0)
    new_paid = round(paid_prev + body.amount, 2)
    remaining = round(max(total - new_paid, 0), 2)
    new_status = "Paid" if remaining == 0 else ("Partially_Paid" if new_paid > 0 else inv.get("status"))
    await db.invoices.update_one({"id": body.invoice_id},
        {"$set": {"paid_amount": new_paid, "remaining": remaining, "status": new_status}})
    payment = {"id": new_id(), "invoice_id": body.invoice_id, "amount": body.amount,
               "payment_date": body.payment_date or datetime.now(timezone.utc).date().isoformat(),
               "mode": body.mode, "reference": body.reference, "notes": body.notes,
               "created_at": now_iso(), "created_by": user["id"], "client_id": inv.get("client_id")}
    await db.payments.insert_one(payment); strip_id(payment)
    await db.activity.insert_one({"id": new_id(), "client_id": inv.get("client_id"),
        "user_id": user["id"], "user_name": user["name"],
        "action": f"recorded ₹{body.amount:,.2f} payment ({body.mode}) on {inv.get('number')}",
        "created_at": now_iso()})
    return {"payment": payment, "invoice_status": new_status, "remaining": remaining}

@api.get("/payments")
async def list_payments(invoice_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {}
    if invoice_id: q["invoice_id"] = invoice_id
    if user["role"] == "client":
        # Payment visibility scoped to their client
        q["client_id"] = user.get("client_id")
    return await list_col(db.payments, q)

# ---------- File uploads ----------
@api.post("/uploads")
async def upload_file(client_id: str = Form(...), entity_type: str = Form("creative"),
                     entity_id: Optional[str] = Form(None), file: UploadFile = File(...),
                     user: dict = Depends(get_current_user)):
    if user["role"] == "client" and user.get("client_id") != client_id:
        raise HTTPException(403, "Forbidden")
    ct = (file.content_type or "").lower()
    if ct and ct not in ALLOWED_MIME:
        raise HTTPException(400, f"MIME type not allowed: {ct}")
    fid = new_id()
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    storage_path = f"{APP_NAME}/uploads/{client_id}/{fid}.{ext}"
    data = await file.read()
    try:
        result = put_object(storage_path, data, ct or "application/octet-stream")
    except Exception as e:
        logger.error(f"Object storage upload failed: {e}")
        raise HTTPException(502, "Storage upload failed")
    doc = {"id": fid, "filename": file.filename,
           "storage_path": result["path"], "content_type": ct,
           "size": result.get("size", len(data)), "client_id": client_id,
           "entity_type": entity_type, "entity_id": entity_id,
           "uploader_id": user["id"], "uploader_name": user["name"],
           "url": f"/api/files/{fid}", "is_deleted": False,
           "created_at": now_iso()}
    await db.assets.insert_one(doc); strip_id(doc)
    if entity_type == "creative" and entity_id:
        await db.creatives.update_one({"id": entity_id},
            {"$set": {"thumbnail_url": doc["url"], "asset_id": fid, "asset_content_type": ct}})
    return doc

@api.get("/files/{fid}")
async def get_file(fid: str):
    asset = await db.assets.find_one({"id": fid, "is_deleted": {"$ne": True}})
    if not asset: raise HTTPException(404, "File not found")
    try:
        data, ctype = get_object(asset["storage_path"])
    except Exception as e:
        logger.error(f"Object storage fetch failed: {e}")
        raise HTTPException(502, "Storage fetch failed")
    return Response(content=data, media_type=asset.get("content_type") or ctype)

@api.get("/assets")
async def list_assets(client_id: Optional[str] = None, entity_type: Optional[str] = None,
                       entity_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"is_deleted": {"$ne": True}}
    if client_id: q["client_id"] = client_id
    if entity_type: q["entity_type"] = entity_type
    if entity_id: q["entity_id"] = entity_id
    if user["role"] == "client": q["client_id"] = user.get("client_id")
    return await list_col(db.assets, q)

@api.delete("/assets/{aid}")
async def delete_asset(aid: str, user: dict = Depends(get_current_user)):
    # Soft-delete only — Emergent Object Storage has no delete API
    result = await db.assets.update_one({"id": aid}, {"$set": {"is_deleted": True, "deleted_at": now_iso()}})
    if result.matched_count == 0: raise HTTPException(404, "Asset not found")
    return {"ok": True}

# ---------- Messaging (threaded on entities) ----------
@api.get("/messages")
async def list_messages(client_id: str, entity_type: Optional[str] = None,
                          entity_id: Optional[str] = None, thread_id: Optional[str] = None,
                          user: dict = Depends(get_current_user)):
    if user["role"] == "client" and user.get("client_id") != client_id:
        raise HTTPException(403, "Forbidden")
    q = {"client_id": client_id}
    if thread_id: q["thread_id"] = thread_id
    if entity_type: q["entity_type"] = entity_type
    if entity_id: q["entity_id"] = entity_id
    return await db.messages.find(q, {"_id": 0}).sort("created_at", 1).to_list(500)

@api.post("/messages")
async def post_message(body: MessageIn, user: dict = Depends(get_current_user)):
    if user["role"] == "client" and user.get("client_id") != body.client_id:
        raise HTTPException(403, "Forbidden")
    thread_id = body.thread_id or f"{body.entity_type}:{body.entity_id or 'general'}:{body.client_id}"
    doc = {"id": new_id(), "thread_id": thread_id, "entity_type": body.entity_type,
           "entity_id": body.entity_id, "client_id": body.client_id,
           "sender_id": user["id"], "sender_name": user["name"],
           "sender_role": user["role"], "body": body.body,
           "read_by": [user["id"]], "created_at": now_iso()}
    await db.messages.insert_one(doc); strip_id(doc)
    # Notification for the other side
    notif_target_role = "client" if user["role"] != "client" else "agency"
    await db.notifications.insert_one({
        "id": new_id(), "kind": f"msg-{doc['id']}", "user_id": None,
        "client_id": body.client_id, "severity": "info",
        "title": f"New message from {user['name']}",
        "message": body.body[:120], "link": f"/workspace/{body.client_id}",
        "read": False, "created_at": now_iso()
    })
    return doc

# ---------- Global search ----------
@api.get("/search")
async def global_search(q: str, user: dict = Depends(get_current_user)):
    if not q or len(q) < 2: return {"query": q, "results": {}}
    rx = {"$regex": q, "$options": "i"}
    scope_client = None
    if user["role"] == "client": scope_client = user.get("client_id")

    async def find_in(col, fields, extra=None):
        or_q = [{f: rx} for f in fields]
        mq = {"$or": or_q}
        if scope_client and col not in ("users",):
            mq["client_id"] = scope_client
        if extra: mq.update(extra)
        return await db[col].find(mq, {"_id": 0}).limit(6).to_list(6)

    results = {
        "clients": [] if scope_client else await find_in("clients", ["name","industry","primary_contact"]),
        "campaigns": await find_in("campaigns", ["name","platform","objective"]),
        "projects": await find_in("projects", ["name","description"]),
        "tasks": await find_in("tasks", ["name","description"]),
        "content": await find_in("content", ["title","caption"]),
        "creatives": await find_in("creatives", ["name","caption","cta"]),
        "leads": await find_in("leads", ["name","company","email"]),
        "invoices": await find_in("invoices", ["number"]),
    }
    total = sum(len(v) for v in results.values())
    return {"query": q, "total": total, "results": results}

# ---------- Client profitability ----------
@api.get("/finance/profitability/{client_id}")
async def client_profitability(client_id: str, user: dict = Depends(require_role("agency_admin","account_manager"))):
    c = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not c: raise HTTPException(404, "Client not found")
    campaigns = await db.campaigns.find({"client_id": client_id}, {"_id": 0}).to_list(500)
    invoices = await db.invoices.find({"client_id": client_id}, {"_id": 0}).to_list(200)
    retainer = c.get("monthly_retainer", 0)
    # Revenue = retainer + management fee (~15% of ad spend)
    campaign_mgmt_fee = round(sum(cp.get("spend", 0) for cp in campaigns) * 0.15, 2)
    invoiced = round(sum(i.get("grand_total", i.get("total", i.get("amount", 0))) for i in invoices), 2)
    revenue = round(retainer + campaign_mgmt_fee, 2)
    # Estimated cost = internal team hours (30% of revenue) + creative production (10%)
    team_cost = round(revenue * 0.30, 2)
    creative_cost = round(revenue * 0.10, 2)
    vendor_cost = round(sum(cp.get("spend", 0) for cp in campaigns) * 0.02, 2)  # 2% platform vendor fees
    total_cost = round(team_cost + creative_cost + vendor_cost, 2)
    gross_profit = round(revenue - total_cost, 2)
    margin = round(gross_profit / revenue * 100, 1) if revenue else 0
    return {
        "revenue": {"retainer": retainer, "campaign_mgmt_fee": campaign_mgmt_fee,
                    "total": revenue, "invoiced": invoiced},
        "cost": {"team": team_cost, "creative": creative_cost, "vendor": vendor_cost, "total": total_cost},
        "gross_profit": gross_profit, "gross_margin_pct": margin,
        "note": "Estimated using standard agency cost heuristics (team 30% · creative 10% · vendor 2%)"
    }

@api.get("/finance/profitability")
async def all_profitability(user: dict = Depends(require_role("agency_admin","account_manager"))):
    clients = await db.clients.find({}, {"_id": 0}).to_list(500)
    out = []
    for c in clients:
        p = await client_profitability(c["id"], user)
        out.append({"id": c["id"], "name": c["name"], "logo_color": c.get("logo_color"),
                    "industry": c["industry"], **p})
    out.sort(key=lambda x: -x["gross_profit"])
    return out

# CTR / lead-conversion model endpoints live in intel.py (versioned registry)

# ---------- PDF Reports ----------
@api.get("/reports/{cid}/pdf")
async def generate_pdf_report(cid: str, user: dict = Depends(get_current_user)):
    if user["role"] == "client" and user.get("client_id") != cid:
        raise HTTPException(403, "Forbidden")
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from io import BytesIO

    c = await db.clients.find_one({"id": cid}, {"_id": 0})
    if not c: raise HTTPException(404, "Client not found")
    dash = await client_dashboard(cid, user)
    risk = await client_risk(cid, user)
    campaigns = await db.campaigns.find({"client_id": cid}, {"_id": 0}).to_list(200)
    top_camps = sorted([c for c in campaigns if c.get("spend", 0) > 0],
                        key=lambda x: -(x.get("revenue", 0) / max(x.get("spend", 1), 1)))[:3]
    poor_camps = sorted([c for c in campaigns if c.get("spend", 0) > 5000 and (c.get("revenue", 0) / max(c.get("spend", 1), 1)) < 1.5],
                         key=lambda x: (x.get("revenue", 0) / max(x.get("spend", 1), 1)))[:3]

    def inr(n):
        s = f"{int(round(n)):,}"
        # Convert to Indian grouping
        parts = s.split(",")
        if len(parts) <= 2: return f"₹{s}"
        return f"₹{parts[0]},{','.join(parts[1:-1])},{parts[-1]}" if len(parts) >= 3 else f"₹{s}"

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Heading0", fontSize=22, textColor=colors.HexColor("#FF9F1C"), leading=26, spaceAfter=6, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Sub", fontSize=9, textColor=colors.HexColor("#666666"), spaceAfter=10))
    styles.add(ParagraphStyle(name="H2", fontSize=13, textColor=colors.HexColor("#111111"), spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Body2", fontSize=9.5, textColor=colors.HexColor("#333333"), leading=13))
    period = f"Last 30 days · {datetime.now(timezone.utc).strftime('%d %b %Y')}"
    story = []
    story.append(Paragraph("VITRONX", styles["Heading0"]))
    story.append(Paragraph(f"Performance Report · {c['name']} · {c['industry']}", styles["Sub"]))
    story.append(Paragraph(f"Reporting Period: {period}", styles["Sub"]))
    story.append(Paragraph("Executive Summary", styles["H2"]))
    k = dash["kpis"]
    story.append(Paragraph(
        f"During this period {c['name']} generated {k['leads']} leads, drove {k['conversions']} conversions on "
        f"{inr(k['spend'])} ad spend, with a blended ROAS of {k['roas']}x. Client health score is "
        f"{risk['metrics']['health_score']}/100 with risk level marked <b>{risk['risk_level'].upper()}</b>.",
        styles["Body2"]))
    story.append(Paragraph("Key Metrics", styles["H2"]))
    kpi_data = [
        ["Metric", "Value"],
        ["Ad Spend", inr(k['spend'])], ["Ad Revenue", inr(k['revenue'])],
        ["ROAS", f"{k['roas']}x"], ["CTR", f"{k['ctr']}%"],
        ["CPA", inr(k['cpa'])], ["Leads", str(k['leads'])],
        ["Conversions", str(k['conversions'])], ["Website Visitors", f"{k['website_visitors']:,}"],
        ["Followers", f"{k['followers']:,}"], ["Engagement Rate", f"{k['engagement_rate']}%"],
        ["SEO Score", f"{k['seo_score']}/100"], ["Health Score", f"{risk['metrics']['health_score']}/100"],
    ]
    t = Table(kpi_data, colWidths=[80*mm, 90*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FF9F1C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f9")]),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    if top_camps:
        story.append(Paragraph("Top Performing Campaigns", styles["H2"]))
        rows = [["Campaign", "Platform", "Spend", "Revenue", "ROAS"]]
        for cp in top_camps:
            r = round((cp.get("revenue", 0) / max(cp.get("spend", 1), 1)), 2)
            rows.append([cp["name"][:40], cp.get("platform", "-"), inr(cp.get("spend", 0)), inr(cp.get("revenue", 0)), f"{r}x"])
        t2 = Table(rows, colWidths=[65*mm, 25*mm, 30*mm, 30*mm, 20*mm])
        t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10B981")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ("PADDING", (0, 0), (-1, -1), 4)]))
        story.append(t2)

    if poor_camps:
        story.append(Paragraph("Underperforming Campaigns (needs attention)", styles["H2"]))
        rows = [["Campaign", "Platform", "Spend", "Revenue", "ROAS"]]
        for cp in poor_camps:
            r = round((cp.get("revenue", 0) / max(cp.get("spend", 1), 1)), 2)
            rows.append([cp["name"][:40], cp.get("platform", "-"), inr(cp.get("spend", 0)), inr(cp.get("revenue", 0)), f"{r}x"])
        t3 = Table(rows, colWidths=[65*mm, 25*mm, 30*mm, 30*mm, 20*mm])
        t3.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EF4444")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
            ("PADDING", (0, 0), (-1, -1), 4)]))
        story.append(t3)

    if risk["drivers"]:
        story.append(Paragraph("Risk Drivers & Recommended Intervention", styles["H2"]))
        for d in risk["drivers"]:
            story.append(Paragraph(f"• <b>{d['factor']}</b> — {d['detail']} (weight +{d['weight']})", styles["Body2"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Recommended Action:</b> {risk['intervention']}", styles["Body2"]))

    story.append(Paragraph("Notes", styles["H2"]))
    story.append(Paragraph(
        "This report is auto-generated by VITRONX. Metrics derived from the platform database. "
        "Ad platform data marked as <b>DEMO</b> in the app is synthetic and not from a live provider. "
        "All figures shown in Indian Rupees (₹).", styles["Body2"]))
    doc.build(story)
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="VITRONX-{c["name"].replace(" ", "_")}-Report.pdf"'})

# ---------- Onboarding wizard endpoint ----------
class OnboardingIn(BaseModel):
    client: Dict[str, Any]
    brand: Optional[Dict[str, Any]] = None
    project: Optional[Dict[str, Any]] = None
    campaign: Optional[Dict[str, Any]] = None
    budget: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None

@api.post("/onboarding/complete")
async def complete_onboarding(body: OnboardingIn, user: dict = Depends(require_role("agency_admin","account_manager"))):
    """Create client + optional brand/project/campaign/budget/content in one flow."""
    created = {}
    # Client
    cdoc = {**body.client, "id": new_id(), "created_at": now_iso(),
            "status": body.client.get("status", "Active"),
            "health_score": 82, "account_manager_id": user["id"],
            "logo_color": body.client.get("logo_color") or random.choice(["#FF9F1C","#00E5FF","#10B981","#F43F5E","#8B5CF6"])}
    await db.clients.insert_one(cdoc); strip_id(cdoc); created["client"] = cdoc
    cid = cdoc["id"]
    # Brand info stored on client
    if body.brand:
        await db.clients.update_one({"id": cid}, {"$set": {"brand": body.brand}})
        created["brand"] = body.brand
    # Project
    if body.project and body.project.get("name"):
        pdoc = {**body.project, "id": new_id(), "client_id": cid,
                "status": body.project.get("status", "Active"), "progress": 0,
                "created_at": now_iso()}
        await db.projects.insert_one(pdoc); strip_id(pdoc); created["project"] = pdoc
    # Campaign
    if body.campaign and body.campaign.get("name"):
        cdoc2 = {**body.campaign, "id": new_id(), "client_id": cid,
                 "status": "Draft", "spend": 0, "impressions": 0, "clicks": 0,
                 "conversions": 0, "revenue": 0, "created_at": now_iso()}
        await db.campaigns.insert_one(cdoc2); strip_id(cdoc2); created["campaign"] = cdoc2
    # Budget
    if body.budget and body.budget.get("allocated"):
        bdoc = {**body.budget, "id": new_id(), "client_id": cid, "period": "monthly",
                "category": body.budget.get("category", "advertising"),
                "created_at": now_iso()}
        await db.budgets.insert_one(bdoc); strip_id(bdoc); created["budget"] = bdoc
    # First content
    if body.content and body.content.get("title"):
        codoc = {**body.content, "id": new_id(), "client_id": cid,
                 "status": "Idea", "created_at": now_iso()}
        await db.content.insert_one(codoc); strip_id(codoc); created["content"] = codoc
    await db.activity.insert_one({"id": new_id(), "client_id": cid, "user_id": user["id"],
        "user_name": user["name"], "action": f"onboarded new client: {cdoc['name']}",
        "created_at": now_iso()})
    return created

# ---------- Daily AI Brief ----------
@api.get("/analytics/daily-brief")
async def daily_brief(user: dict = Depends(get_current_user)):
    """Structured facts + optional LLM narrative. Backend calculates, LLM only explains."""
    attention = await needs_attention(user)
    unread = await db.notifications.count_documents({"read": False})
    top_creatives = await db.creatives.find(
        {"actual_ctr": {"$gt": 0}}, {"_id": 0}
    ).sort("actual_ctr", -1).to_list(3)
    bad_campaigns = await db.campaigns.find({"status": "Active", "spend": {"$gt": 5000}}, {"_id": 0}).to_list(200)
    bad_campaigns = [c for c in bad_campaigns if (c.get("revenue",0) / max(c.get("spend",1),1)) < 1.5][:3]

    facts = {
        "top_priorities": attention[:5],
        "unread_alerts": unread,
        "top_creatives": [{"name": c["name"], "ctr": c.get("actual_ctr"), "client_id": c["client_id"]} for c in top_creatives],
        "underperforming_campaigns": [{"name": c["name"], "roas": round(c.get("revenue",0)/max(c.get("spend",1),1),2),
                                       "spend": c.get("spend"), "client_id": c["client_id"]} for c in bad_campaigns],
        "generated_at": now_iso(),
    }
    # Optional LLM narrative (explains only — never calculates)
    narrative = None
    try:
        top_names = "; ".join([c['name'] + ' @ ' + str(c.get('actual_ctr')) + '%' for c in top_creatives]) or "none"
        top_priorities = "; ".join([a['title'] for a in attention[:3]]) or "none"
        summary_input = (f"Priorities: {len(attention)} items. Top: {top_priorities}. "
                         f"Top creatives (by actual CTR): {top_names}. "
                         f"Underperforming: {len(bad_campaigns)} campaigns.")
        sys_msg = "You are the VITRONX daily strategist for an Indian digital marketing agency. Write a crisp 3-bullet briefing summarizing what needs attention today. Use INR (₹). Do not invent metrics — only rephrase the facts given."
        narrative = await asyncio.wait_for(gen_ai_text(summary_input, sys_msg), timeout=15)
    except Exception:
        narrative = None
    return {"facts": facts, "narrative": narrative or "Focus on the top-priority items above and rotate creative on the underperforming campaigns."}

# ---------- Phase 3 seed: Indian campaigns + upgraded invoices + trained model ----------
async def seed_phase3():
    # Update existing invoices with GST fields if missing
    to_upgrade = await db.invoices.find({"currency": {"$exists": False}}, {"_id": 0}).to_list(200)
    for inv in to_upgrade:
        amount = inv.get("amount", 0)
        # Assume 18% GST intra-state Maharashtra
        gst = round(amount * 0.18, 2)
        cgst = round(gst / 2, 2); sgst = round(gst / 2, 2)
        grand = round(amount + gst, 2)
        # Regenerate number in FY format
        n = await db.invoices.count_documents({"number": {"$regex": "^VTX/"}})
        fy = indian_fy()
        new_num = f"VTX/{fy}/{n+1:04d}"
        await db.invoices.update_one({"id": inv["id"]}, {"$set": {
            "number": new_num, "currency": "INR",
            "subtotal": amount, "cgst": cgst, "sgst": sgst, "igst": 0.0,
            "total_tax": gst, "grand_total": grand, "gst_rate": 18,
            "agency_state": "Maharashtra", "client_state": "Maharashtra",
            "intra_state": True, "paid_amount": grand if inv.get("status") == "Paid" else 0,
            "remaining": 0 if inv.get("status") == "Paid" else grand,
            "payment_terms": "Net 15 days",
        }})

    # Seed Indian campaigns if not present
    if await db.campaigns.count_documents({"name": {"$regex": "Diwali|Holi|Independence"}}) == 0:
        indian_campaigns = [
            ("Diwali Festive Push", "Conversions", "Meta Ads"),
            ("Holi Colors Campaign", "Awareness", "Instagram"),
            ("Independence Day Sale", "Sales", "Google Ads"),
            ("Raksha Bandhan Gifting", "Conversions", "Meta Ads"),
            ("New Year Launch", "Awareness", "YouTube"),
        ]
        clients_list = await db.clients.find({}, {"_id": 0}).to_list(20)
        for i, c in enumerate(clients_list):
            if i >= len(indian_campaigns): break
            name, obj, plat = indian_campaigns[i]
            spend = random.randint(80000, 350000)  # in INR (₹80k–₹3.5L)
            imp = random.randint(200000, 1500000)
            clk = int(imp * random.uniform(0.018, 0.048))
            conv = int(clk * random.uniform(0.03, 0.11))
            rev = int(spend * random.uniform(1.8, 5.5))
            await db.campaigns.insert_one({
                "id": new_id(), "client_id": c["id"],
                "name": f"{name} — {c['name']}",
                "platform": plat, "objective": obj, "status": "Active",
                "budget": spend + random.randint(20000, 80000),
                "spend": spend, "impressions": imp, "clicks": clk,
                "conversions": conv, "revenue": rev,
                "target_cities": random.sample(["Mumbai","Delhi","Bengaluru","Hyderabad","Chennai","Pune","Kolkata","Ahmedabad"], 4),
                "start_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(5,25))).isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=random.randint(5,25))).isoformat(),
                "created_at": now_iso()
            })

    # Update client retainers to INR-appropriate ranges (if still in $ scale <5000)
    async for c in db.clients.find({"monthly_retainer": {"$lt": 10000}}):
        # Scale up to Indian retainer range
        new_r = c["monthly_retainer"] * 85  # roughly $→₹ + agency premium
        await db.clients.update_one({"id": c["id"]}, {"$set": {"monthly_retainer": new_r}})

    logger.info("Phase 3 seed complete")


from intel import build_router as build_intel_router
intel_router = build_intel_router(db, get_current_user, require_role, gen_ai_text, new_id, now_iso, client_profitability)
api.include_router(intel_router)
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

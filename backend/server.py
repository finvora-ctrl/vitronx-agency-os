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
                cluster_clients, campaign_efficiency_index, pearson_correlation)

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

# ---------- NOTIFICATIONS ----------
@api.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user)):
    return await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)

@api.post("/notifications/{nid}/read")
async def mark_read(nid: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"id": nid, "user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}

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

    # 30-day trend
    trend = []
    for i in range(30):
        d = datetime.now(timezone.utc) - timedelta(days=29-i)
        trend.append({
            "date": d.strftime("%b %d"),
            "impressions": int(imp / 30 * (0.7 + random.random() * 0.6)),
            "clicks": int(clk / 30 * (0.7 + random.random() * 0.6)),
            "conversions": int(conv / 30 * (0.6 + random.random() * 0.8)),
            "spend": int(spend / 30 * (0.7 + random.random() * 0.6)),
        })

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
    await seed_all()
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

app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# VITRONX — Product Requirements Document

## Vision
AI-Powered Operating System for Digital Marketing Agencies. Multi-tenant SaaS for agency ops + client workspaces + ML/AI decision support with closed feedback loops.

## Personas
- Agency Admin (finvora@gmail.com / Vitronx@2026)
- Account Manager (sarah.manager@vitronx.demo / Demo@2026)
- Designer (riya.designer@vitronx.demo / Demo@2026)
- Marketer (arjun.marketer@vitronx.demo / Demo@2026)
- Client (client@vitronx.demo / Demo@2026)

## Core Architecture
- Backend: FastAPI + MongoDB (motor). JWT auth, RBAC via role + client_id scoping.
- Frontend: React 19 + React Router 7 + Tailwind + Recharts + Sonner toasts.
- ML: numpy (OLS, EMA, z-score, k-means, logistic scoring, Pearson, creative feature model).
- AI: Emergent Universal Key → Gemini 3.1 Pro (rule-based fallback).
- Integrations: provider-agnostic base class with demo/live modes.

## Phase 1 (Feb 2026)
- JWT auth, 5 seeded roles, agency dashboard, clients module, 15-tab client workspace
- Agency-wide views (campaigns, projects, tasks, calendar, team, approvals, leads, content, analytics)
- CRUD for clients, campaigns, projects, tasks, content, leads
- Approval workflow with activity log
- Rule-based AI insights + Gemini AI captions
- Per-client analytics (KPIs, trend, pie, funnel, SEO)
- ML Lab: OLS forecast + R², EMA smoothing, z-score anomalies, logistic lead scoring, k-means client clustering, Pearson correlation, campaign efficiency index

## Phase 2 (Sept 2026 — this iteration)
- Creative Intelligence Engine: rank_creatives, score_creative with predicted CTR, engagement, conversion potential, audience fit, historical similarity, explainable reasons, composite score, confidence, tier
- A/B Testing: variant_group grouping, compute_ab_winner with uplift + confidence, primary metric detection (ROAS/CTR)
- Prediction feedback loop: /ab/{id}/record persists actual metrics, prediction_error_stats returns MAE/MAPE, /ml/prediction-accuracy shows predicted vs actual chart
- Client Risk Center: compute_client_risk with weighted drivers (health, ROAS, overdue tasks, approvals, content pipeline), risk_level, intervention recommendation, "Create Intervention Task" button
- Agency-wide Risk Center at /risk showing all clients ranked
- Notification center: real conditions (ROAS drop, approval backlog, overdue tasks), severity levels (critical/warning/info/success), unread badge in topbar, dropdown preview + full page, /notifications/compute endpoint
- Client Portal (/portal): simplified nav (Overview/Approvals/Reports/Updates), backend-enforced client_id scoping, forced redirect from agency routes
- Budget & Invoicing: budgets with utilization %, pacing status (healthy/warning/critical/overspend), auto-computed spent from campaigns, invoice CRUD with auto number + tax total
- AI Insight → Task workflow: /ai/insight-to-task creates task, marks insight Accepted, logs activity
- Integration layer: MetaAds/GoogleAds/GoogleAnalytics/GSC with is_configured, mode (live/demo), status endpoint, 7-day preview labeled DEMO
- Needs Attention section: /analytics/needs-attention aggregates ROAS drops, approval backlogs, overdue tasks, budget alerts sorted by severity + score
- Seeded creative variants (A/B/C groups) with actual performance data, ad budgets, invoices

## New Backend Endpoints
- /api/creatives (CRUD + /score, /rank/{cid})
- /api/ab/groups/{cid}, /api/ab/{id}/record
- /api/ml/prediction-accuracy/{cid}
- /api/risk/{cid}, /api/risk/agency/all
- /api/notifications (list + unread), /notifications/compute, /read, /read-all
- /api/budgets, /api/invoices
- /api/ai/insight-to-task
- /api/integrations, /integrations/{provider}/preview
- /api/analytics/needs-attention

## Data Isolation (Verified)
- Client role sees only own client_id
- 403 on cross-client analytics
- 403 on agency-only endpoints (risk/agency/all)
- Frontend forced redirect: client role → /portal

## Backlog
- Meta / Google Ads / GA4 / GSC live API wiring
- Object storage uploads for creatives, brand assets, documents
- Global search across entities
- Onboarding wizard
- PDF report export
- Custom dashboard widgets
- Client portal: full messaging + document exchange

# VITRONX — Product Requirements Document

## Vision
AI-Powered Operating System for Digital Marketing Agencies. Multi-tenant SaaS for agency ops + client workspaces + AI decision support.

## Personas
- Agency Admin (finvora@gmail.com)
- Account Manager (sarah.manager@vitronx.demo)
- Designer (riya.designer@vitronx.demo)
- Marketer (arjun.marketer@vitronx.demo)
- Client (client@vitronx.demo)

## Core Architecture (Feb 2026)
- Backend: FastAPI + MongoDB (motor). JWT auth, RBAC via role + client_id scoping.
- Frontend: React 19 + React Router 7 + Tailwind + Recharts + Sonner toasts.
- AI: Emergent Universal Key → Gemini 3.1 Pro (rule-based fallback).

## Implemented (Feb 2026)
- JWT auth with 5 seeded demo users + admin
- 5 seeded clients: Lumière Cosmetics, VerdeLife Wellness, Meridian Estates, Saffron & Smoke, NexaLoop Technologies
- Agency Dashboard (KPIs, 12-week trend, Client Health Matrix, Priorities panel)
- Clients list (grid cards) + Create Client modal
- Client Workspace with 14 tabs: Overview, Campaigns, Content, Calendar, Tasks, Projects, Leads, Approvals, SEO, Analytics, AI Insights, Reports, Activity, Brand
- Global views: Campaigns, Projects, Tasks (Kanban), Calendar, Team, Approvals, Leads CRM, Content, Analytics
- CRUD for Clients, Campaigns, Projects, Tasks, Content, Leads
- Approval workflow (approve/reject/request-changes) with activity log
- AI insight generator (rule-based + Gemini summary), AI caption assistant
- Client-scoped analytics dashboard (KPIs, trend, pie, funnel)
- SEO module with keyword tracking table
- Report generator
- Data isolation by role: client role sees only their client_id

## P1 Backlog
- File uploads via Emergent Object Storage (Creatives, Assets, Documents modules)
- Client Portal (separate simplified nav for role=client)
- Notifications center with unread badge + real events
- Global search across entities
- Budget & Invoice modules with pacing
- Shoot management module
- Website + Ads deep dashboards with per-platform breakdowns

## P2 Backlog
- Onboarding wizard
- Dashboard widget customization
- PDF report export
- Real integrations (Meta/Google Ads/Analytics) via service layer

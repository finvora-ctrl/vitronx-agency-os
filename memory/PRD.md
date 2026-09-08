# VITRONX — Product Requirements Document (Phase 3)

## Vision
India-first AI-powered Operating System for Digital Marketing Agencies. Multi-tenant SaaS with agency ops + client workspaces + ML/AI decision support + INR/GST financial layer.

## Personas
- Agency Admin (finvora@gmail.com / Vitronx@2026)
- Account Manager (sarah.manager@vitronx.demo / Demo@2026)
- Designer (riya.designer@vitronx.demo / Demo@2026)
- Marketer (arjun.marketer@vitronx.demo / Demo@2026)
- Client (client@vitronx.demo / Demo@2026)

## Phase 3 Highlights (Sept 2026 iteration)
- **INR everywhere**: fmtINR utility with Indian grouping (₹1,50,000 / ₹12,50,000). Every $ replaced with ₹ on dashboards, KPIs, budgets, invoices, retainers.
- **GST invoicing**: /api/invoices/gst with auto CGST/SGST vs IGST split based on agency vs client state. Indian FY numbering (VTX/2026-27/0001). HSN/SAC codes, GSTIN, taxable value, grand total.
- **Payment tracking**: /api/payments with UPI/NEFT/RTGS/IMPS/Bank Transfer/Cheque/Cash modes. Auto-updates invoice status to Partially_Paid / Paid.
- **Random Forest CTR model** (sklearn): trained on all creatives with actual performance. Train/test 75/25 split. MAE=0.32, RMSE=0.47, R²=0.75 (beats LR baseline R²=0.74). Feature importance chart, top feature = platform_objective_fit.
- **Global search** across clients/campaigns/projects/tasks/content/creatives/leads/invoices with grouped results and deep-link navigation.
- **Daily AI Brief** on Agency Command Center: backend calculates facts (priorities, top creatives, underperforming campaigns), Gemini 3.1 Pro writes 3-bullet narrative.
- **Client profitability**: /api/finance/profitability/{cid} — revenue (retainer + 15% mgmt fee), cost (team 30% + creative 10% + vendor 2%), gross profit + margin. Displayed on Client Overview.
- **File uploads**: /api/uploads with local storage + /api/files/{id} serving. Thumbnails auto-linked to creatives. Preview shown in Creative Intel ranking cards.
- **Client messaging**: threaded /api/messages tied to entities (approval/task/campaign/content/general). Full conversation panel in Client Portal + Client Overview.
- **Indian campaigns seed**: Diwali Festive Push, Holi Colors, Independence Day Sale, Raksha Bandhan Gifting, New Year Launch — with target cities (Mumbai/Delhi/Bengaluru/Hyderabad/Chennai/Pune/Kolkata/Ahmedabad).
- **Retainers rescaled**: All 5 clients now on realistic Indian retainers (₹2.4L–₹5.3L monthly).

## Data Isolation (Verified)
- Client role sees only own client_id
- HTTP 403 on cross-client analytics/risk/agency endpoints
- Search backend-scoped to client_id for client role

## New Backend Endpoints (Phase 3)
- POST /api/invoices/gst, POST /api/invoices/{id}/status
- POST /api/payments, GET /api/payments
- POST /api/uploads, GET /api/files/{id}, GET/DELETE /api/assets
- GET/POST /api/messages
- GET /api/search?q=
- GET /api/finance/profitability/{cid}, GET /api/finance/profitability
- POST /api/ml/ctr-model/train, GET /api/ml/ctr-model, GET /api/ml/ctr-model/predict/{cid}
- GET /api/analytics/daily-brief

## Tech
- Backend: FastAPI + MongoDB + numpy + sklearn (RF/LinReg) + bcrypt + PyJWT + Motor
- Frontend: React 19 + Router 7 + Tailwind + Recharts + Sonner
- AI: Emergent Universal Key → Gemini 3.1 Pro
- Storage: Local FS at /app/backend/uploads (preview-only; migrate to Emergent Object Storage for deployment)

## Known Limitations
- File uploads use pod-local storage — needs Emergent Object Storage before production deploy
- Meta/Google Ads/Analytics still in DEMO mode (integration layer ready for creds)
- No PDF report export yet
- Onboarding wizard not shipped this iteration

## Backlog / Recommended Next Steps
- Migrate uploads to Emergent Object Storage
- Onboarding wizard (5-min flow to first campaign)
- PDF branded reports (reportlab or WeasyPrint)
- Wire real Meta/Google Ads credentials into integration layer
- Lead conversion model (Logistic Regression) with probability + tier
- Isolation Forest anomaly detection for campaigns

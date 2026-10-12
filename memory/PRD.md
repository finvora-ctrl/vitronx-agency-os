# VITRONX — Product Requirements Document

## Original problem statement (latest, user's words, abridged headings)
"VITRONX — AI/ML INTELLIGENCE UPGRADE + VOICE-ENABLED AI COMPANION … Transform VITRONX into a genuinely useful, explainable AI/ML-powered agency operating system. It should identify business problems, predict outcomes where justified by data, explain findings, recommend actions, and measure whether those actions work. Also implement a persistent animated dog AI companion at the bottom-right of the application, with text chat, voice input, and spoken responses."
Phases: 1 Audit · 2 AI Campaign Doctor · 3 Prediction vs Actual Learning Lab · 4 Floating Dog AI Buddy (text + voice) · 5 Model Transparency · 6 Recommendations layer · 7 Test & protect existing app. Rules: reuse existing code, never invent data/metrics, label synthetic data, no auto-actions, respect role/client isolation, ~50 credits.

Earlier brief: AI-powered Digital Marketing Agency OS — multi-client workspaces, JWT RBAC (admin, account manager, designer, marketer, client), real scikit-learn ML, INR/GST finance, PDF reports, approvals, object storage, Gemini 3.1 Pro insights.

## Personas / credentials
See /app/memory/test_credentials.md (admin finvora@gmail.com).

## Architecture
- backend/server.py — core CRUD, auth, finance, reports (includes intel router)
- backend/intel.py — Campaign Doctor, ML Lab registry, transparency, recommendations, AI Buddy chat, startup seeding/restore
- backend/ml_lab.py — chronological training, metrics, gated promotion, explanations
- backend/ml.py — heuristics (forecast, z-score, risk, creative scoring); old lead/CTR trainers now unused
- frontend: pages/IntelKit.jsx (Doctor, Recommendations, Learning Lab, Transparency), components/AIBuddy.jsx (mounted in AppShell)

## New collections
campaign_daily (synthetic_demo seeded, 60 days/campaign; agency_entered via POST /api/campaign-daily), interventions, ml_model_versions, ml_predictions, buddy_messages. `data_source` field added to campaigns/creatives/leads/tasks.

## Changelog
### 2026-10-12 — AI/ML upgrade
- Audit findings fixed: lead model leaked label (pipeline stage feature) → perfect 1.0 scores; removed. CTR model trained & tested on the same 15 rows → now chronological split. Client 30-day trend was random per request → now from stored campaign_daily. Client role could read agency profitability → now admin/manager only. Models were retrained/overwritten every restart → now versioned, restored reproducibly from stored training ids.
- Campaign Doctor (Campaigns + AI Insights tabs), finding→task with suggested owner, intervention tracking.
- Learning Lab + Transparency + "How this prediction works" (ML Lab tab).
- Recommendations (Agency dashboard + AI Insights).
- AI Buddy: animated dog, text chat, Web Speech API voice in/out (en-IN), mute/stop/replay, offline/error states, grounded backend chat with role scoping, deterministic fallback.
- Testing: iteration_1 — backend 18/18 pass, frontend all flows pass.

## Model evaluation (actual, synthetic demo data)
- rf-ctr-v1: 15 creatives (11 train/4 test), MAE 1.29 vs baseline 1.02, R² −4.59 → REJECTED; CTR predictions disabled.
- lr-lead-v2 (active; v1 retired, identical): 26 Won/Lost leads (20/6), acc 0.833, precision 0.75, recall 1.0, F1 0.857, ROC-AUC 1.0 on 6 records (not meaningful), status "evaluated".

## Backlog
- P1: Real Meta/Google Ads ingestion into campaign_daily (needs credentials)
- P1: Overview KPIs followers/reach/visitors/SEO score are still random demo values (flagged via demo_fields) — replace with real sources
- P2: SEO/Website modules, Shoot management, global date filter, team workload
- P2: Split server.py/intel.py into smaller routers

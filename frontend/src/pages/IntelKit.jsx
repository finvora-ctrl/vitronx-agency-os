import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { SectionHeader, EmptyState } from "../components/atoms";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { Stethoscope, Sparkles, Zap, AlertTriangle, RefreshCw, Database, Info } from "lucide-react";

const SEV = { high: "vx-badge-danger", medium: "vx-badge-warning", low: "vx-badge-neutral" };
export const fv = (v, u) => u === "₹" ? `₹${v}` : `${v}${u || ""}`;
const Badge = ({ cls, children, testId }) => <span data-testid={testId} className={`vx-status-badge ${cls}`}>{children}</span>;

export const DataSourceTag = ({ sources }) => {
  const list = Array.isArray(sources) ? sources : Object.keys(sources || {});
  if (!list.length) return null;
  return <span className="inline-flex items-center gap-1 text-[10px] font-mono uppercase text-amber-300/90 bg-amber-500/10 border border-amber-500/20 rounded px-1.5 py-0.5" data-testid="data-source-tag">
    <Database size={10}/>{list.join(" · ").replace(/synthetic_demo/g, "SYNTHETIC DEMO DATA")}</span>;
};

function FindingCard({ f, cid, campaignId, onTask }) {
  const [busy, setBusy] = useState(false);
  const o = f.observed;
  const mk = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/doctor/task", { client_id: cid, campaign_id: campaignId, finding_id: f.id });
      toast.success(`Task created${data.suggested_owner ? ` → ${data.suggested_owner.name} (${data.suggested_owner.role})` : ""}`);
      onTask && onTask();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); } finally { setBusy(false); }
  };
  return (
    <div className="p-4 rounded-lg bg-[var(--vx-card-hover)] border border-[var(--vx-border)] space-y-2" data-testid={`finding-${f.id}`}>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="font-medium text-sm">{f.title}</div>
        <div className="flex gap-1"><Badge cls={SEV[f.severity]}>{f.severity}</Badge><Badge cls="vx-badge-ai" testId={`finding-confidence-${f.id}`}>{f.confidence} confidence</Badge></div>
      </div>
      <div className="grid sm:grid-cols-2 gap-2 text-xs">
        <div><div className="text-[10px] uppercase text-slate-500">Observed (fact)</div>
          <div className="font-mono text-slate-200">{f.metric}: {fv(o.baseline_value, o.unit)} → <b className="text-amber-400">{fv(o.recent_value, o.unit)}</b> ({o.change_pct}%)</div>
          <div className="text-slate-500">Baseline {o.baseline_period} · Recent {o.recent_period}{o.welch_t != null && ` · t=${o.welch_t}`}</div></div>
        <div><div className="text-[10px] uppercase text-slate-500">Possible causes (hypotheses)</div>
          <ul className="list-disc ml-4 text-slate-300">{f.possible_causes.map(c => <li key={c}>{c}</li>)}</ul></div>
      </div>
      <div className="text-xs"><div className="text-[10px] uppercase text-amber-400/90 font-bold">Recommended actions</div>
        <ul className="list-disc ml-4 text-slate-200">{f.recommended_actions.map(a => <li key={a}>{a}</li>)}</ul></div>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="text-[10px] text-slate-500 italic">{f.causality_note}</div>
        <button data-testid={`finding-task-btn-${f.id}`} disabled={busy} onClick={mk} className="vx-btn-primary text-xs flex items-center gap-1"><Zap size={12}/>{busy ? "Creating…" : `Create task (${f.suggested_owner_role}, ${f.priority})`}</button>
      </div>
    </div>
  );
}

function Interventions({ cid, tick }) {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get(`/doctor/interventions/${cid}`).then(r => setItems(r.data)).catch(() => {}); }, [cid, tick]);
  if (!items.length) return null;
  const cls = { improved: "vx-badge-success", worsened: "vx-badge-danger", awaiting_data: "vx-badge-neutral", no_clear_change: "vx-badge-warning" };
  return (
    <div className="vx-card p-5" data-testid="interventions-panel">
      <SectionHeader title="Intervention tracking" subtitle="Performance after tasks created from Campaign Doctor findings (before/after, not causal proof)"/>
      <div className="space-y-2">{items.map(iv => (
        <div key={iv.id} className="flex items-center justify-between gap-2 text-xs p-2 rounded bg-[var(--vx-card-hover)] flex-wrap" data-testid={`intervention-${iv.id}`}>
          <div><div className="font-medium text-sm">{iv.campaign_name}</div><div className="text-slate-500">{iv.finding_title} · started {iv.start_date} · task {iv.task_status}</div></div>
          <div className="text-right"><Badge cls={cls[iv.outcome] || "vx-badge-neutral"}>{iv.outcome?.replace(/_/g, " ")}{iv.change_pct != null && ` ${iv.change_pct}%`}</Badge>
            <div className="text-slate-500 mt-1 max-w-xs">{iv.outcome_note}</div></div>
        </div>))}</div>
    </div>
  );
}

export function CampaignDoctorPanel({ cid }) {
  const [d, setD] = useState(null);
  const [narr, setNarr] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);
  const load = () => api.get(`/doctor/${cid}`).then(r => setD(r.data)).catch(() => toast.error("Campaign Doctor failed to load"));
  useEffect(() => { load(); }, [cid]);
  const explain = async () => {
    setLoading(true);
    try { const { data } = await api.post(`/doctor/${cid}/explain`); setNarr(data); } catch { toast.error("Explanation failed"); } finally { setLoading(false); }
  };
  if (!d) return <div className="text-slate-400 text-sm">Running Campaign Doctor…</div>;
  return (
    <div className="space-y-4" data-testid="campaign-doctor-panel">
      <div className="vx-card p-5">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-cyan-400 font-bold flex items-center gap-1"><Stethoscope size={12}/>AI Campaign Doctor</div>
            <div className="text-sm text-slate-300 mt-1" data-testid="doctor-summary">{d.summary.findings} finding(s) across {d.summary.with_findings}/{d.summary.campaigns} campaigns{d.summary.insufficient_data ? ` · ${d.summary.insufficient_data} with insufficient data` : ""}</div>
            <div className="text-[11px] text-slate-500 mt-1 max-w-2xl">{d.method}</div>
            <div className="mt-2"><DataSourceTag sources={d.data_sources}/></div>
          </div>
          <div className="flex gap-2">
            <button data-testid="doctor-refresh-btn" onClick={load} className="vx-btn-secondary text-xs flex items-center gap-1"><RefreshCw size={12}/>Re-run</button>
            <button data-testid="doctor-explain-btn" onClick={explain} disabled={loading} className="vx-btn-primary text-xs flex items-center gap-1"><Sparkles size={12}/>{loading ? "Explaining…" : "Explain with AI"}</button>
          </div>
        </div>
        {narr && <div className="mt-4 p-4 rounded-lg border border-cyan-500/30 text-sm whitespace-pre-wrap text-slate-200" data-testid="doctor-narrative">
          <div className="text-[10px] uppercase text-cyan-400 font-bold mb-1">{narr.llm_used ? "AI interpretation of computed findings" : "AI unavailable"}</div>{narr.narrative}</div>}
      </div>
      {d.campaigns.length === 0 && <EmptyState title="No campaigns" hint="Add a campaign and record daily metrics to enable diagnosis."/>}
      {d.campaigns.filter(c => c.state !== "ok").map(c => (
        <div key={c.campaign_id} className="vx-card p-5 space-y-3" data-testid={`doctor-campaign-${c.campaign_id}`}>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div><div className="font-display font-semibold">{c.campaign_name}</div><div className="text-xs text-slate-500">{c.platform} · {c.status}</div></div>
            {c.recent && <div className="text-[11px] font-mono text-slate-400">7d CTR {c.recent.ctr}% · CPC ₹{c.recent.cpc} · CVR {c.recent.cvr}% · ROAS {c.recent.roas}x</div>}
          </div>
          {c.state === "insufficient_data" ? <div className="text-xs text-slate-400 flex items-center gap-1"><Info size={12}/>{c.message}</div> :
            c.findings.map(f => <FindingCard key={f.id} f={f} cid={cid} campaignId={c.campaign_id} onTask={() => setTick(t => t + 1)}/>)}
        </div>
      ))}
      {d.campaigns.some(c => c.state === "ok") && <div className="text-xs text-slate-500" data-testid="doctor-healthy-count">{d.campaigns.filter(c => c.state === "ok").length} campaign(s) show no significant deterioration.</div>}
      <Interventions cid={cid} tick={tick}/>
    </div>
  );
}

export function RecommendationsPanel({ cid, limit = 8 }) {
  const [recs, setRecs] = useState(null);
  useEffect(() => { api.get("/recommendations", { params: cid ? { client_id: cid } : {} }).then(r => setRecs(r.data)).catch(() => setRecs([])); }, [cid]);
  if (!recs) return null;
  return (
    <div className="vx-card p-5" data-testid="recommendations-panel">
      <SectionHeader title="Prioritised recommendations" subtitle="Evidence-backed next actions · nothing is executed automatically — human approval required"/>
      {recs.length === 0 ? <div className="text-sm text-slate-400">No issues detected in current data.</div> :
        <div className="space-y-2">{recs.slice(0, limit).map(r => (
          <Link to={r.link} key={r.id} className="block p-3 rounded-lg bg-[var(--vx-card-hover)] hover:border-amber-500/40 border border-transparent" data-testid={`rec-${r.id}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm font-medium">{!cid && <span className="text-amber-400">{r.client_name} · </span>}{r.issue}</div>
              <div className="flex gap-1 shrink-0"><Badge cls="vx-badge-neutral">{r.kind.replace("_", " ")}</Badge><Badge cls="vx-badge-ai">{r.confidence}</Badge></div>
            </div>
            <div className="text-xs text-slate-400 mt-1">{r.evidence} · <span className="text-slate-500">{r.period}</span></div>
            <div className="text-xs text-slate-200 mt-1">→ {r.action}</div>
            {r.expected_benefit && <div className="text-[11px] text-emerald-400 mt-1">{r.expected_benefit}</div>}
          </Link>))}</div>}
    </div>
  );
}

const READY = { insufficient_data: "vx-badge-danger", evaluated: "vx-badge-warning", ready_for_cautious_use: "vx-badge-success" };

function ModelLabCard({ kind, m, onRetrain }) {
  const a = m.active;
  const metricKeys = kind === "ctr_rf" ? ["mae", "rmse", "r2"] : ["accuracy", "precision", "recall", "f1", "roc_auc"];
  return (
    <div className="p-4 rounded-lg bg-[var(--vx-card-hover)] space-y-3" data-testid={`lab-${kind}`}>
      <div className="flex justify-between items-center flex-wrap gap-2">
        <div className="font-medium">{kind === "ctr_rf" ? "CTR Predictor (Random Forest)" : "Lead Conversion (Logistic Regression)"}</div>
        <div className="flex gap-2 items-center"><Badge cls={READY[m.readiness]} testId={`lab-readiness-${kind}`}>{m.readiness.replace(/_/g, " ")}</Badge>
          <button data-testid={`lab-retrain-${kind}`} onClick={() => onRetrain(kind)} className="vx-btn-secondary text-xs">Retrain (gated)</button></div>
      </div>
      {!a ? <div className="text-xs text-amber-300 flex gap-1"><AlertTriangle size={12}/>No version has passed the evaluation gate, so predictions are disabled. See rejected versions below.</div> :
        <div className="grid grid-cols-3 md:grid-cols-5 gap-2 text-xs">{metricKeys.map(k => (
          <div key={k} className="p-2 rounded bg-[var(--vx-card)]"><div className="text-[10px] uppercase text-slate-500">{k}</div><div className="font-mono font-bold">{a.metrics[k] ?? "n/a"}</div></div>))}</div>}
      {a && <div className="text-[11px] text-slate-400">Active {a.version_label} · trained {new Date(a.trained_at).toLocaleString()} · {a.metrics.train_records} train / {a.metrics.test_records} test · {a.metrics.validation}</div>}
      {(a?.warnings || []).map(w => <div key={w} className="text-[11px] text-amber-300 flex gap-1"><AlertTriangle size={11} className="shrink-0 mt-0.5"/>{w}</div>)}
      <div className="text-[11px] text-slate-400" data-testid={`lab-live-${kind}`}>Prediction vs actual: {m.live_evaluation.logged_predictions} logged · {m.live_evaluation.resolved_honest} honest pairs · {m.live_evaluation.message || (m.live_evaluation.metrics && JSON.stringify(m.live_evaluation.metrics))}{m.drift_flag && <b className="text-red-400"> · DRIFT FLAGGED</b>}</div>
      <table className="w-full text-[11px]"><thead><tr className="text-left text-slate-500"><th>Version</th><th>Status</th><th>Key metric</th><th>Samples</th><th>Reason</th></tr></thead>
        <tbody>{m.versions.map(v => (
          <tr key={v.id} className="border-t border-[var(--vx-border)]"><td className="py-1 font-mono">{v.version_label}</td><td>{v.status}</td>
            <td className="font-mono">{kind === "ctr_rf" ? `MAE ${v.metrics?.mae} (baseline ${v.metrics?.baseline_lr?.mae})` : `F1 ${v.metrics?.f1} · AUC ${v.metrics?.roc_auc}`}</td>
            <td>{v.total_samples}</td><td className="text-slate-500">{v.promotion_reason}</td></tr>))}</tbody></table>
    </div>
  );
}

export function LearningLabPanel() {
  const [d, setD] = useState(null);
  const load = () => api.get("/ml/lab").then(r => setD(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const retrain = async (kind) => {
    try {
      const { data } = await api.post(`/ml/lab/${kind}/retrain`);
      if (data.status === "skipped") toast.info(data.reason);
      else if (data.promoted) toast.success(`${data.version_label} promoted`);
      else toast.warning(data.promotion_reason || data.note || `Status: ${data.status}`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Retrain failed"); }
  };
  if (!d) return null;
  return (
    <div className="vx-card p-5 space-y-3" data-testid="learning-lab-panel">
      <SectionHeader title="Prediction vs Actual Learning Lab" subtitle="Versioned models · chronological validation · gated promotion · no automatic self-learning"/>
      {Object.entries(d).map(([k, m]) => <ModelLabCard key={k} kind={k} m={m} onRetrain={retrain}/>)}
    </div>
  );
}

function ExplainPicker({ cid }) {
  const [kind, setKind] = useState("lead");
  const [items, setItems] = useState([]);
  const [sel, setSel] = useState("");
  const [ex, setEx] = useState(null);
  useEffect(() => {
    setSel(""); setEx(null);
    api.get(kind === "lead" ? "/leads" : "/creatives", { params: { client_id: cid } }).then(r => setItems(r.data)).catch(() => setItems([]));
  }, [kind, cid]);
  const run = (id) => { setSel(id); if (id) api.get(`/ml/explain/${kind}/${id}`).then(r => setEx(r.data)); };
  return (
    <div className="p-4 rounded-lg bg-[var(--vx-card-hover)] space-y-3" data-testid="explain-picker">
      <div className="font-medium text-sm">How this prediction works</div>
      <div className="flex gap-2 flex-wrap">
        <select data-testid="explain-kind-select" className="vx-input max-w-[160px]" value={kind} onChange={e => setKind(e.target.value)}><option value="lead">Lead</option><option value="ctr">Creative (CTR)</option></select>
        <select data-testid="explain-entity-select" className="vx-input max-w-xs" value={sel} onChange={e => run(e.target.value)}>
          <option value="">Select a record…</option>{items.map(i => <option key={i.id} value={i.id}>{i.name}{i.status ? ` (${i.status})` : ""}</option>)}</select>
      </div>
      {ex && (ex.status === "model_not_trained" ? <div className="text-xs text-amber-300" data-testid="explain-result">No active model for this prediction type (none passed evaluation).</div> :
        <div className="text-xs space-y-2" data-testid="explain-result">
          <div className="text-sm">Prediction: <b className="text-amber-400 font-mono">{ex.prediction ?? `${ex.conversion_probability}% (${ex.tier})`}{ex.unit ? ` ${ex.unit}` : ""}</b> · model {ex.model_version} · {ex.readiness?.replace(/_/g, " ")} · trained on {ex.trained_on} records <DataSourceTag sources={ex.data_sources}/></div>
          {ex.in_training_data && <div className="text-amber-300">This record was part of the training/test data, so its prediction is not an independent test.</div>}
          <div className="text-slate-400">{ex.method}</div>
          <table className="w-full"><thead><tr className="text-left text-slate-500"><th>Feature</th><th>Value</th><th>Reference</th><th>Effect</th></tr></thead>
            <tbody>{ex.contributions.map(c => (<tr key={c.feature} className="border-t border-[var(--vx-border)]"><td className="py-1">{c.feature}</td><td className="font-mono">{c.value}</td>
              <td className="font-mono">{c.training_median ?? c.training_mean}</td><td className={`font-mono ${(c.effect_pp ?? c.log_odds_effect) >= 0 ? "text-emerald-400" : "text-red-400"}`}>{c.effect_pp ?? c.log_odds_effect}</td></tr>))}</tbody></table>
          <div className="text-slate-500">Actual outcome on record: {ex.actual ?? "Not recorded"}</div>
        </div>)}
    </div>
  );
}

export function TransparencyPanel({ cid }) {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/ml/transparency").then(r => setD(r.data)).catch(() => {}); }, []);
  if (!d) return null;
  const Row = ({ k, v }) => <div className="grid grid-cols-[140px_1fr] gap-2 py-1 border-t border-[var(--vx-border)]"><div className="text-slate-500">{k}</div><div className="text-slate-200 break-words">{v}</div></div>;
  const fmt = (v) => v == null ? "Not recorded" : typeof v === "object" ? JSON.stringify(v) : String(v);
  return (
    <div className="vx-card p-5 space-y-3" data-testid="transparency-panel">
      <SectionHeader title="AI/ML Model Transparency" subtitle="What each model does, what data it learned from, and how far to trust it"/>
      <div className="text-xs text-amber-300 flex gap-1"><AlertTriangle size={12}/>{d.integrations_note} {d.self_learning_note}</div>
      <ExplainPicker cid={cid}/>
      <div className="grid lg:grid-cols-2 gap-3">{d.models.map(m => (
        <details key={m.key} className="p-4 rounded-lg bg-[var(--vx-card-hover)] text-xs" data-testid={`model-doc-${m.key}`}>
          <summary className="cursor-pointer text-sm font-medium flex justify-between">{m.name}<span className="text-slate-500 font-mono text-[10px]">{m.type}</span></summary>
          <div className="mt-2">
            <Row k="Algorithm" v={m.algorithm}/><Row k="Business problem" v={m.problem}/><Row k="Target" v={m.target}/>
            <Row k="Input features" v={m.features.join(", ")}/><Row k="Training data" v={fmt(m.training_data)}/>
            {m.preprocessing && <Row k="Preprocessing" v={m.preprocessing.join("; ")}/>}
            <Row k="Validation" v={m.validation}/>{"metrics" in m && <Row k="Evaluation (actual run)" v={fmt(m.metrics)}/>}
            {"version" in m && <Row k="Version / trained" v={`${m.version || "Not recorded"} · ${m.trained_at || "Not recorded"} · ${m.versions_recorded} versions`}/>}
            {"readiness" in m && <Row k="Status" v={m.readiness}/>}
            <Row k="Limitations" v={[...(m.warnings || []), ...m.limitations].join(" · ")}/>
            {m.outcomes_and_retraining && <Row k="Outcomes & retraining" v={m.outcomes_and_retraining}/>}
            <Row k="Self-learning" v={m.self_learning ? "Yes" : "No"}/>
          </div>
        </details>))}</div>
    </div>
  );
}

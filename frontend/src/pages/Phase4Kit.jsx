import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { KpiCard, SectionHeader, StatusBadge, EmptyState } from "../components/atoms";
import { fmtINR } from "../lib/fmt";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { Sparkles, Download, ArrowRight, ArrowLeft, Check, Zap } from "lucide-react";
import { useApp } from "../context/AppContext";
import { MessagesPanel } from "./Phase3Kit";

// ================ ONBOARDING WIZARD ================
export function OnboardingWizard() {
  const [step, setStep] = useState(0);
  const [data, setData] = useState({
    client: {name:"", industry:"D2C Beauty", website:"", email:"", phone:"", primary_contact:"", monthly_retainer:150000, status:"Onboarding"},
    brand: {tone:"Premium & confident", audience:"Urban 22-38", positioning:"", competitors:""},
    project: {name:"Q1 Growth Sprint", description:"", priority:"High", budget:200000},
    campaign: {name:"", platform:"Meta Ads", objective:"Awareness", budget:100000},
    budget: {allocated:100000, category:"advertising"},
    content: {title:"", content_type:"Reel", platform:"Instagram", caption:""},
  });
  const nav = useNavigate();
  const { fetchClients, switchClient } = useApp();

  const steps = ["Client", "Brand", "Project", "Campaign", "Budget", "First Content", "Review"];
  const upd = (section, key, value) => setData({...data, [section]: {...data[section], [key]: value}});

  const finish = async () => {
    try {
      const {data: r} = await api.post("/onboarding/complete", data);
      toast.success(`Onboarded ${r.client.name}`);
      await fetchClients();
      switchClient(r.client.id);
      nav(`/workspace/${r.client.id}`);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const next = () => step < steps.length - 1 ? setStep(step + 1) : finish();
  const prev = () => step > 0 && setStep(step - 1);
  const canNext = step === 0 ? data.client.name && data.client.industry : true;

  return (
    <div className="max-w-3xl mx-auto space-y-6" data-testid="onboarding-wizard">
      <div>
        <div className="text-[11px] uppercase tracking-widest text-amber-400 font-bold flex items-center gap-1"><Sparkles size={12}/>Onboarding</div>
        <h1 className="font-display text-3xl font-extrabold mt-1">Set up a new client in 5 minutes</h1>
        <div className="flex gap-1 mt-4">
          {steps.map((s, i) => (
            <div key={s} className={`flex-1 h-1.5 rounded-full ${i <= step ? "bg-amber-400" : "bg-[var(--vx-border)]"}`}/>
          ))}
        </div>
        <div className="text-xs text-slate-500 mt-2">Step {step + 1} of {steps.length} · {steps[step]}</div>
      </div>

      <div className="vx-card p-6 space-y-4">
        {step === 0 && (
          <>
            <SectionHeader title="Client details" subtitle="Company + primary contact"/>
            <div className="grid grid-cols-2 gap-3">
              {[["name","Company name"],["industry","Industry"],["website","Website"],["primary_contact","Primary contact"],["email","Email"],["phone","Phone"]].map(([k,l])=>(
                <div key={k}><label className="text-xs text-slate-400 uppercase">{l}</label>
                  <input data-testid={`ow-client-${k}`} className="vx-input mt-1" value={data.client[k]} onChange={e=>upd("client",k,e.target.value)} required={k==="name"||k==="industry"}/></div>
              ))}
              <div><label className="text-xs text-slate-400 uppercase">Monthly retainer (₹)</label>
                <input data-testid="ow-client-retainer" type="number" className="vx-input mt-1" value={data.client.monthly_retainer} onChange={e=>upd("client","monthly_retainer",Number(e.target.value))}/></div>
            </div>
          </>
        )}
        {step === 1 && (
          <>
            <SectionHeader title="Brand" subtitle="Tone + audience — used by AI when generating captions"/>
            {[["tone","Brand tone"],["audience","Target audience"],["positioning","Positioning"],["competitors","Key competitors"]].map(([k,l])=>(
              <div key={k}><label className="text-xs text-slate-400 uppercase">{l}</label>
                <input data-testid={`ow-brand-${k}`} className="vx-input mt-1" value={data.brand[k]} onChange={e=>upd("brand",k,e.target.value)}/></div>
            ))}
          </>
        )}
        {step === 2 && (
          <>
            <SectionHeader title="First project"/>
            <div><label className="text-xs text-slate-400 uppercase">Project name</label>
              <input data-testid="ow-project-name" className="vx-input mt-1" value={data.project.name} onChange={e=>upd("project","name",e.target.value)}/></div>
            <div><label className="text-xs text-slate-400 uppercase">Description</label>
              <textarea data-testid="ow-project-desc" className="vx-input mt-1 min-h-[80px]" value={data.project.description} onChange={e=>upd("project","description",e.target.value)}/></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs text-slate-400 uppercase">Priority</label>
                <select data-testid="ow-project-priority" className="vx-input mt-1" value={data.project.priority} onChange={e=>upd("project","priority",e.target.value)}>{["Low","Medium","High","Critical"].map(o=><option key={o}>{o}</option>)}</select></div>
              <div><label className="text-xs text-slate-400 uppercase">Budget (₹)</label>
                <input data-testid="ow-project-budget" type="number" className="vx-input mt-1" value={data.project.budget} onChange={e=>upd("project","budget",Number(e.target.value))}/></div>
            </div>
          </>
        )}
        {step === 3 && (
          <>
            <SectionHeader title="First campaign"/>
            <div><label className="text-xs text-slate-400 uppercase">Campaign name</label>
              <input data-testid="ow-campaign-name" className="vx-input mt-1" value={data.campaign.name} onChange={e=>upd("campaign","name",e.target.value)} placeholder="e.g. Diwali Awareness Push"/></div>
            <div className="grid grid-cols-3 gap-3">
              <div><label className="text-xs text-slate-400 uppercase">Platform</label>
                <select data-testid="ow-campaign-platform" className="vx-input mt-1" value={data.campaign.platform} onChange={e=>upd("campaign","platform",e.target.value)}>{["Meta Ads","Google Ads","LinkedIn","YouTube"].map(o=><option key={o}>{o}</option>)}</select></div>
              <div><label className="text-xs text-slate-400 uppercase">Objective</label>
                <select data-testid="ow-campaign-objective" className="vx-input mt-1" value={data.campaign.objective} onChange={e=>upd("campaign","objective",e.target.value)}>{["Awareness","Engagement","Traffic","Lead Generation","Conversions","Sales"].map(o=><option key={o}>{o}</option>)}</select></div>
              <div><label className="text-xs text-slate-400 uppercase">Budget (₹)</label>
                <input data-testid="ow-campaign-budget" type="number" className="vx-input mt-1" value={data.campaign.budget} onChange={e=>upd("campaign","budget",Number(e.target.value))}/></div>
            </div>
          </>
        )}
        {step === 4 && (
          <>
            <SectionHeader title="Monthly ad budget"/>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs text-slate-400 uppercase">Allocated (₹)</label>
                <input data-testid="ow-budget-allocated" type="number" className="vx-input mt-1" value={data.budget.allocated} onChange={e=>upd("budget","allocated",Number(e.target.value))}/></div>
              <div><label className="text-xs text-slate-400 uppercase">Category</label>
                <select data-testid="ow-budget-category" className="vx-input mt-1" value={data.budget.category} onChange={e=>upd("budget","category",e.target.value)}>{["advertising","production","seo","retainer","other"].map(o=><option key={o}>{o}</option>)}</select></div>
            </div>
          </>
        )}
        {step === 5 && (
          <>
            <SectionHeader title="First content idea (optional)"/>
            <div><label className="text-xs text-slate-400 uppercase">Title</label>
              <input data-testid="ow-content-title" className="vx-input mt-1" value={data.content.title} onChange={e=>upd("content","title",e.target.value)} placeholder="e.g. Behind the Scenes #1"/></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs text-slate-400 uppercase">Type</label>
                <select data-testid="ow-content-type" className="vx-input mt-1" value={data.content.content_type} onChange={e=>upd("content","content_type",e.target.value)}>{["Reel","Carousel","Video","Story","Social Post","Blog"].map(o=><option key={o}>{o}</option>)}</select></div>
              <div><label className="text-xs text-slate-400 uppercase">Platform</label>
                <select data-testid="ow-content-platform" className="vx-input mt-1" value={data.content.platform} onChange={e=>upd("content","platform",e.target.value)}>{["Instagram","Facebook","LinkedIn","YouTube"].map(o=><option key={o}>{o}</option>)}</select></div>
            </div>
          </>
        )}
        {step === 6 && (
          <>
            <SectionHeader title="Review & finish" subtitle="Confirm everything looks correct"/>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 bg-[var(--vx-card-hover)] rounded-lg"><div className="text-[10px] uppercase text-slate-500">Client</div><div className="font-medium">{data.client.name}</div><div className="text-xs text-slate-500">{data.client.industry} · {fmtINR(data.client.monthly_retainer)} retainer</div></div>
              <div className="p-3 bg-[var(--vx-card-hover)] rounded-lg"><div className="text-[10px] uppercase text-slate-500">Project</div><div className="font-medium">{data.project.name || "—"}</div><div className="text-xs text-slate-500">{data.project.priority} · {fmtINR(data.project.budget)}</div></div>
              <div className="p-3 bg-[var(--vx-card-hover)] rounded-lg"><div className="text-[10px] uppercase text-slate-500">Campaign</div><div className="font-medium">{data.campaign.name || "(skipped)"}</div><div className="text-xs text-slate-500">{data.campaign.platform} · {data.campaign.objective} · {fmtINR(data.campaign.budget)}</div></div>
              <div className="p-3 bg-[var(--vx-card-hover)] rounded-lg"><div className="text-[10px] uppercase text-slate-500">Budget</div><div className="font-medium">{fmtINR(data.budget.allocated)}</div><div className="text-xs text-slate-500">{data.budget.category}</div></div>
              <div className="p-3 bg-[var(--vx-card-hover)] rounded-lg col-span-2"><div className="text-[10px] uppercase text-slate-500">First content</div><div className="font-medium">{data.content.title || "(skipped)"}</div></div>
            </div>
          </>
        )}
      </div>

      <div className="flex justify-between">
        <button data-testid="ow-prev" disabled={step===0} onClick={prev} className="vx-btn-ghost flex items-center gap-1 disabled:opacity-30"><ArrowLeft size={14}/>Back</button>
        <button data-testid="ow-next" disabled={!canNext} onClick={next} className="vx-btn-primary flex items-center gap-2 disabled:opacity-50">
          {step === steps.length - 1 ? <><Check size={14}/>Finish & open workspace</> : <>Next <ArrowRight size={14}/></>}
        </button>
      </div>
    </div>
  );
}

// ================ PDF DOWNLOAD BUTTON ================
export function DownloadPdfButton({clientId, clientName}) {
  const [busy, setBusy] = useState(false);
  const dl = async () => {
    setBusy(true);
    try {
      const r = await api.get(`/reports/${clientId}/pdf`, {responseType: "blob"});
      const url = URL.createObjectURL(new Blob([r.data], {type:"application/pdf"}));
      const a = document.createElement("a"); a.href = url;
      a.download = `VITRONX-${clientName.replace(/\s+/g,"_")}-Report.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("PDF downloaded");
    } catch (e) { toast.error("PDF generation failed"); }
    finally { setBusy(false); }
  };
  return <button data-testid="download-pdf-btn" onClick={dl} disabled={busy} className="vx-btn-primary flex items-center gap-2"><Download size={14}/>{busy?"Generating…":"Download PDF"}</button>;
}

// ================ LEAD CONVERSION ML PANEL ================
export function LeadConversionPanel({cid}) {
  const [status, setStatus] = useState(null);
  const [leads, setLeads] = useState([]);
  const [training, setTraining] = useState(false);

  const load = async () => {
    const [s, l] = await Promise.all([
      api.get("/ml/lead-conversion"),
      api.get(`/ml/lead-conversion/predict-batch/${cid}`),
    ]);
    setStatus(s.data); setLeads(l.data);
  };
  useEffect(()=>{load()}, [cid]);

  const train = async () => {
    setTraining(true);
    try { await api.post("/ml/lead-conversion/train"); toast.success("Model retrained"); load(); }
    finally { setTraining(false); }
  };

  if (!status) return null;
  return (
    <div className="vx-card p-5" data-testid="lead-conversion-panel">
      <div className="flex justify-between items-center mb-3">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-cyan-400 font-bold flex items-center gap-1"><Sparkles size={12}/>Lead Conversion — Logistic Regression</div>
          <div className="text-xs text-slate-500 mt-1">Predicts P(Won) from source, deal value, contact completeness · stage excluded (label leakage) · chronological split · trained on SYNTHETIC demo leads</div>
        </div>
        <button data-testid="retrain-lead" onClick={train} disabled={training} className="vx-btn-primary text-xs">{training?"Training…":"Retrain"}</button>
      </div>
      {status.status !== "trained" ? <div className="text-sm text-slate-400 py-4">Model status: {status.status}. {status.note || "Click Retrain to fit on current leads."}</div> :
      <>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard testId="lc-acc" label="Accuracy" value={status.metrics.accuracy}/>
          <KpiCard testId="lc-prec" label="Precision" value={status.metrics.precision}/>
          <KpiCard testId="lc-rec" label="Recall" value={status.metrics.recall}/>
          <KpiCard testId="lc-f1" label="F1" value={status.metrics.f1}/>
        </div>
        <div className="grid md:grid-cols-2 gap-4 mt-4">
          <div>
            <div className="text-[11px] uppercase text-amber-400/90 font-bold mb-2">Confusion Matrix</div>
            <table className="text-xs w-full">
              <thead><tr><th></th><th className="p-1 text-slate-500">Pred Lost</th><th className="p-1 text-slate-500">Pred Won</th></tr></thead>
              <tbody>
                <tr><td className="p-1 text-slate-500">Actual Lost</td><td className="p-2 bg-[var(--vx-card-hover)] font-mono text-emerald-400">{status.metrics.confusion_matrix[0][0]}</td><td className="p-2 bg-[var(--vx-card-hover)] font-mono text-red-400">{status.metrics.confusion_matrix[0][1]}</td></tr>
                <tr><td className="p-1 text-slate-500">Actual Won</td><td className="p-2 bg-[var(--vx-card-hover)] font-mono text-red-400">{status.metrics.confusion_matrix[1][0]}</td><td className="p-2 bg-[var(--vx-card-hover)] font-mono text-emerald-400">{status.metrics.confusion_matrix[1][1]}</td></tr>
              </tbody>
            </table>
          </div>
          <div>
            <div className="text-[11px] uppercase text-amber-400/90 font-bold mb-2">Feature Coefficients</div>
            <div className="space-y-1 text-xs">
              {Object.entries(status.metrics.coefficients).map(([k,v])=>(
                <div key={k} className="flex justify-between p-2 bg-[var(--vx-card-hover)] rounded"><span>{k}</span><span className={`font-mono ${v>=0?"text-emerald-400":"text-red-400"}`}>{v>=0?"+":""}{v}</span></div>
              ))}
            </div>
          </div>
        </div>
        {leads.length > 0 && (
          <div className="mt-5">
            <div className="text-[11px] uppercase text-amber-400/90 font-bold mb-2">Top Leads by Model Probability</div>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase text-slate-500"><th className="p-2">Lead</th><th>Source</th><th>Stage</th><th>Value</th><th>P(Won)</th><th>Tier</th></tr></thead>
              <tbody>
                {leads.slice(0,8).map(l=>(
                  <tr key={l.id} className="border-b border-[var(--vx-border)]/60">
                    <td className="p-2 font-medium">{l.name}</td>
                    <td className="p-2 text-slate-400">{l.source}</td>
                    <td className="p-2"><StatusBadge status={l.status}/></td>
                    <td className="p-2 font-mono">{fmtINR(l.value)}</td>
                    <td className="p-2 font-mono font-bold text-amber-400">{l.conversion_probability!=null?`${l.conversion_probability}%`:"—"}</td>
                    <td className="p-2"><span className={`vx-status-badge ${l.tier==="HOT"?"vx-badge-danger":l.tier==="WARM"?"vx-badge-warning":"vx-badge-neutral"}`}>{l.tier||"—"}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="mt-3 text-[10px] text-slate-500 font-mono">Trained {status.trained_at ? new Date(status.trained_at).toLocaleString() : "—"} · Model {status.model_version}</div>
      </>}
    </div>
  );
}

// ================ APPROVAL WITH THREAD ================
export function ApprovalCardWithThread({item, onAction, clientId}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="vx-card p-4" data-testid={`approval-thread-${item.id}`}>
      <div className="flex justify-between items-start">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-slate-500">{item.content_type} · {item.platform}</div>
          <div className="font-medium mt-1">{item.title}</div>
        </div>
        <StatusBadge status={item.status}/>
      </div>
      <div className="text-xs text-slate-400 mt-2">{item.caption}</div>
      <div className="flex gap-2 mt-3 flex-wrap">
        <button data-testid={`thread-approve-${item.id}`} onClick={()=>onAction(item.id, "approve")} className="vx-btn-primary flex-1 min-w-[100px]"><Check size={14} className="inline mr-1"/>Approve</button>
        <button data-testid={`thread-reject-${item.id}`} onClick={()=>onAction(item.id, "reject")} className="vx-btn-ghost flex-1 min-w-[100px]">Reject</button>
        <button data-testid={`toggle-thread-${item.id}`} onClick={()=>setOpen(!open)} className="vx-btn-ghost text-xs">{open?"Hide":"Comments"}</button>
      </div>
      {open && <div className="mt-3"><MessagesPanel clientId={clientId} entityType="approval" entityId={item.id} title={`Discussion — ${item.title}`}/></div>}
    </div>
  );
}

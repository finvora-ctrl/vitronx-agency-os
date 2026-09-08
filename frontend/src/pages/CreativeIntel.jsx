import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { KpiCard, StatusBadge, SectionHeader, EmptyState } from "../components/atoms";
import { toast } from "sonner";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";
import { Sparkles, Trophy, Zap, Plus, X, AlertTriangle, ArrowRight } from "lucide-react";

export function CreativeIntelTab({cid}) {
  const [ranked, setRanked] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selected, setSelected] = useState(null);
  const [groupFilter, setGroupFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({name:"", content_type:"Reel", platform:"Instagram", objective:"Awareness", caption:"", cta:"", offer:"", hashtags:"", variant_group:"", variant_label:""});
  const [showAB, setShowAB] = useState(null);
  const [abForm, setAbForm] = useState({impressions:0, clicks:0, conversions:0, spend:0, revenue:0, engagement:0});

  const load = async () => {
    const url = groupFilter ? `/creatives/rank/${cid}?variant_group=${groupFilter}` : `/creatives/rank/${cid}`;
    const [r, g] = await Promise.all([api.get(url), api.get(`/ab/groups/${cid}`)]);
    setRanked(r.data); setGroups(g.data);
    if (r.data.length && !selected) setSelected(r.data[0]);
  };
  useEffect(()=>{ load(); }, [cid, groupFilter]);

  const create = async (e) => {
    e.preventDefault();
    await api.post("/creatives", {...form, client_id: cid});
    toast.success("Creative added — scored automatically");
    setShowForm(false); setForm({name:"", content_type:"Reel", platform:"Instagram", objective:"Awareness", caption:"", cta:"", offer:"", hashtags:"", variant_group:"", variant_label:""});
    load();
  };

  const recordAB = async (e) => {
    e.preventDefault();
    await api.post(`/ab/${showAB.id}/record`, abForm);
    toast.success("Actual metrics recorded — prediction loop closed");
    setShowAB(null); setAbForm({impressions:0, clicks:0, conversions:0, spend:0, revenue:0, engagement:0});
    load();
  };

  return (
    <div className="space-y-6" data-testid="creative-intel-tab">
      <div className="flex justify-between items-end flex-wrap gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-cyan-400 font-bold flex items-center gap-1"><Sparkles size={12}/>Creative Intelligence</div>
          <h3 className="font-display text-2xl font-bold mt-1">Compare, rank & predict</h3>
          <p className="text-xs text-slate-500 mt-1">Structured feature model · Historical similarity · Explainable scoring · Not a guarantee</p>
        </div>
        <div className="flex gap-2 items-center">
          <select data-testid="ab-group-filter" className="vx-input py-1 text-xs w-auto" value={groupFilter} onChange={e=>setGroupFilter(e.target.value)}>
            <option value="">All creatives</option>
            {groups.map(g => <option key={g.group} value={g.group}>{g.group}</option>)}
          </select>
          <button data-testid="new-creative-btn" className="vx-btn-primary" onClick={()=>setShowForm(true)}><Plus size={14} className="inline mr-1"/>New Creative</button>
        </div>
      </div>

      {groups.length > 0 && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {groups.map(g => (
            <div key={g.group} className="vx-card p-4" data-testid={`ab-group-${g.group}`}>
              <div className="flex items-center gap-2 mb-2">
                <Trophy size={14} className={g.winner.verdict==="clear_winner"?"text-amber-400":"text-slate-500"}/>
                <span className="text-[10px] uppercase tracking-widest text-slate-400 font-bold">A/B Test</span>
                <span className="vx-status-badge vx-badge-ai ml-auto">{g.winner.confidence}% conf</span>
              </div>
              <div className="text-sm font-semibold">{g.group}</div>
              <div className="text-xs text-slate-500 mt-1">{g.variants} variants · primary: {g.winner.primary_metric}</div>
              <div className="mt-3 pt-3 border-t border-[var(--vx-border)]">
                <div className="text-[10px] uppercase text-slate-500">Verdict</div>
                <div className={`text-sm font-medium ${g.winner.verdict==="clear_winner"?"text-emerald-400":g.winner.verdict==="likely_winner"?"text-amber-400":"text-slate-300"}`}>
                  {g.winner.winner_name || "—"}
                </div>
                <div className="text-xs text-slate-500 mt-1">Uplift {g.winner.uplift_pct}% · {g.winner.total_impressions?.toLocaleString()} impressions</div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          <SectionHeader title="Creative Ranking" subtitle={`${ranked.length} scored · sorted by composite score`}/>
          {ranked.length === 0 && <EmptyState title="No creatives yet" hint="Add creative variants to compare their predicted performance."/>}
          {ranked.map((r, i) => (
            <div key={r.id} onClick={()=>setSelected(r)}
                 className={`vx-card p-4 cursor-pointer transition-all ${selected?.id===r.id?"border-amber-400":""} ${r.winner?"vx-glow-amber":""}`}
                 data-testid={`creative-rank-${i}`}>
              <div className="flex items-start gap-4">
                <div className="text-3xl font-mono font-extrabold text-slate-600">#{i+1}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {r.winner && <span className="vx-status-badge vx-badge-success flex items-center gap-1"><Trophy size={10}/>RECOMMENDED</span>}
                    <span className="text-[10px] uppercase tracking-widest text-slate-500">{r.content_type} · {r.platform} · {r.objective}</span>
                    {r.variant_label && <span className="vx-status-badge vx-badge-info">Variant {r.variant_label}</span>}
                  </div>
                  <div className="font-medium text-slate-100 mt-1">{r.name}</div>
                  <div className="grid grid-cols-4 gap-3 mt-3 text-xs">
                    <div><div className="text-slate-500">Score</div><div className="font-mono font-bold text-amber-400">{r.composite_score}/100</div></div>
                    <div><div className="text-slate-500">Pred. CTR</div><div className="font-mono">{r.predicted_ctr}%</div></div>
                    <div><div className="text-slate-500">Audience Fit</div><div className="font-mono">{r.audience_fit_score}%</div></div>
                    <div><div className="text-slate-500">Confidence</div><div className="font-mono">{r.confidence}%</div></div>
                  </div>
                  {r.actual_ctr !== undefined && r.actual_ctr !== null && (
                    <div className="mt-2 text-[11px] text-slate-500 font-mono">Actual CTR: <span className="text-cyan-400">{r.actual_ctr}%</span> · Err: {(r.actual_ctr - r.predicted_ctr).toFixed(2)}pp</div>
                  )}
                </div>
                <button data-testid={`record-actual-${r.id}`} onClick={(e)=>{e.stopPropagation(); setShowAB(r); setAbForm({impressions: r.actual_impressions||0, clicks: r.actual_clicks||0, conversions: r.actual_conversions||0, spend: r.actual_spend||0, revenue: r.actual_revenue||0, engagement: r.actual_engagement||0});}} className="vx-btn-ghost text-[10px] py-1">Record actual</button>
              </div>
            </div>
          ))}
        </div>

        {selected && <CreativeDetailPanel c={selected}/>}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={create} className="w-full max-w-lg vx-card p-6 space-y-3 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center"><h3 className="font-display text-xl font-bold">New Creative Variant</h3><button type="button" onClick={()=>setShowForm(false)}><X size={16}/></button></div>
            {[
              ["name","Name",""],["variant_group","Variant Group (optional, groups A/B/C)",""],["variant_label","Variant Label (A/B/C)",""],
              ["caption","Caption","textarea"],["cta","CTA (e.g. Shop Now)",""],["offer","Offer (e.g. 25% off)",""],["hashtags","Hashtags",""]
            ].map(([k,l,t]) => (
              <div key={k}>
                <label className="text-xs text-slate-400 uppercase tracking-widest">{l}</label>
                {t==="textarea" ? <textarea data-testid={`cf-${k}`} className="vx-input mt-1 min-h-[70px]" value={form[k]} onChange={e=>setForm({...form,[k]:e.target.value})}/> :
                 <input data-testid={`cf-${k}`} className="vx-input mt-1" value={form[k]} onChange={e=>setForm({...form,[k]:e.target.value})} required={k==="name"}/>}
              </div>
            ))}
            <div className="grid grid-cols-3 gap-2">
              {["content_type","platform","objective"].map(k => (
                <div key={k}>
                  <label className="text-[10px] text-slate-400 uppercase">{k}</label>
                  <select data-testid={`cf-${k}`} className="vx-input mt-1 text-xs" value={form[k]} onChange={e=>setForm({...form,[k]:e.target.value})}>
                    {k==="content_type" && ["Reel","Carousel","Video","Story","Social Post","Ad Creative","Blog"].map(o=><option key={o}>{o}</option>)}
                    {k==="platform" && ["Instagram","Facebook","LinkedIn","YouTube","X","TikTok"].map(o=><option key={o}>{o}</option>)}
                    {k==="objective" && ["Awareness","Engagement","Traffic","Lead Generation","Conversions","Sales"].map(o=><option key={o}>{o}</option>)}
                  </select>
                </div>
              ))}
            </div>
            <button type="submit" data-testid="submit-creative-btn" className="vx-btn-primary w-full">Score & Save</button>
          </form>
        </div>
      )}

      {showAB && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={recordAB} className="w-full max-w-md vx-card p-6 space-y-3">
            <div className="flex justify-between items-center"><h3 className="font-display text-xl font-bold">Record Actual Performance</h3><button type="button" onClick={()=>setShowAB(null)}><X size={16}/></button></div>
            <p className="text-xs text-slate-500">Closes the prediction feedback loop — {showAB.name}</p>
            {["impressions","clicks","conversions","spend","revenue","engagement"].map(k => (
              <div key={k}>
                <label className="text-xs text-slate-400 uppercase tracking-widest">{k}</label>
                <input data-testid={`ab-${k}`} type="number" step="any" className="vx-input mt-1" value={abForm[k]} onChange={e=>setAbForm({...abForm,[k]:parseFloat(e.target.value)||0})}/>
              </div>
            ))}
            <button type="submit" data-testid="submit-ab-btn" className="vx-btn-primary w-full">Record</button>
          </form>
        </div>
      )}
    </div>
  );
}

function CreativeDetailPanel({c}) {
  return (
    <div className="vx-card p-5 vx-glow-cyan sticky top-4 self-start" data-testid="creative-detail-panel">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles size={12} className="text-cyan-400"/>
        <span className="text-[10px] uppercase tracking-widest text-cyan-400 font-bold">Predicted Performance</span>
      </div>
      <div className="font-display text-lg font-semibold">{c.name}</div>
      <div className="grid grid-cols-2 gap-3 mt-4">
        <MetricBar label="Composite Score" value={c.composite_score} suffix="/100" color="#FF9F1C"/>
        <MetricBar label="Confidence" value={c.confidence} suffix="%" color="#00E5FF"/>
        <MetricBar label="Predicted CTR" value={c.predicted_ctr} suffix="%" color="#10B981" max={5}/>
        <MetricBar label="Pred. Engagement" value={c.predicted_engagement} suffix="%" color="#8B5CF6" max={10}/>
        <MetricBar label="Conversion Potential" value={c.conversion_potential} suffix="%" color="#F43F5E"/>
        <MetricBar label="Audience Fit" value={c.audience_fit_score} suffix="%" color="#3B82F6"/>
      </div>
      <div className="mt-4 p-3 bg-[var(--vx-card-hover)] rounded-lg">
        <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Historical Similarity</div>
        <div className="font-mono text-lg font-bold text-cyan-400">{c.historical_similarity}%</div>
        <div className="text-xs text-slate-500">{c.similar_creatives_count} similar past creatives</div>
      </div>
      <div className="mt-4 pt-4 border-t border-[var(--vx-border)]">
        <div className="text-[10px] uppercase tracking-widest text-amber-400/90 font-bold mb-2">Why this creative?</div>
        <ul className="space-y-1.5">
          {(c.reasons || []).map((r,i)=>(
            <li key={i} className="text-xs text-slate-300 flex gap-2"><ArrowRight size={11} className="text-amber-400 mt-0.5 shrink-0"/><span>{r}</span></li>
          ))}
        </ul>
      </div>
      <div className="mt-3 pt-3 border-t border-[var(--vx-border)] text-[10px] text-slate-500 font-mono">
        Model: {c.model_name} v{c.model_version} · Prediction, not a guarantee
      </div>
    </div>
  );
}

function MetricBar({label, value, suffix, color, max=100}) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div>
      <div className="flex justify-between text-[10px] mb-1"><span className="text-slate-500 uppercase tracking-wider">{label}</span><span className="font-mono font-bold" style={{color}}>{value}{suffix}</span></div>
      <div className="h-1.5 bg-[var(--vx-border)] rounded-full overflow-hidden"><div className="h-full rounded-full" style={{width:`${pct}%`, background: color}}/></div>
    </div>
  );
}

// ===================== RISK TAB =====================
export function RiskTab({cid}) {
  const [risk, setRisk] = useState(null);
  const [accuracy, setAccuracy] = useState(null);
  useEffect(() => {
    api.get(`/risk/${cid}`).then(r => setRisk(r.data));
    api.get(`/ml/prediction-accuracy/${cid}`).then(r => setAccuracy(r.data)).catch(()=>{});
  }, [cid]);

  const createTask = async () => {
    // Create risk-remediation task
    await api.post("/tasks", {
      client_id: cid, name: `Risk intervention — ${risk.risk_level.toUpperCase()}`,
      description: risk.intervention, priority: risk.risk_level === "critical" ? "Critical" : "High", status: "To Do"
    });
    toast.success("Intervention task created");
  };

  if (!risk) return <div className="text-slate-400">Analyzing client risk…</div>;
  const levelColor = {critical:"#EF4444", high:"#F59E0B", medium:"#F59E0B", low:"#10B981"}[risk.risk_level];

  return (
    <div className="space-y-6" data-testid="risk-tab">
      <div className="vx-card p-6" style={{borderLeft: `4px solid ${levelColor}`}}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-widest font-bold" style={{color: levelColor}}>Client Risk Center</div>
            <h3 className="font-display text-3xl font-extrabold mt-1">Risk Level: <span style={{color: levelColor}} className="uppercase">{risk.risk_level}</span></h3>
            <p className="text-sm text-slate-400 mt-1">Risk score {risk.risk_score}/100 · {risk.drivers.length} drivers detected</p>
          </div>
          <button data-testid="create-intervention-task" onClick={createTask} className="vx-btn-primary flex items-center gap-2"><Zap size={14}/>Create Intervention Task</button>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 vx-card p-5">
          <SectionHeader title="Risk Drivers" subtitle="Weighted contributors — transparent scoring"/>
          {risk.drivers.length === 0 ? <EmptyState title="No active risk drivers" hint="Client is stable — continue monitoring."/> :
            <div className="space-y-3">
              {risk.drivers.map((d, i) => (
                <div key={i} className="p-3 bg-[var(--vx-card-hover)] rounded-lg border-l-2" style={{borderLeftColor: levelColor}} data-testid={`risk-driver-${i}`}>
                  <div className="flex justify-between items-start">
                    <div><div className="font-medium text-slate-100">{d.factor}</div><div className="text-xs text-slate-500 mt-1">{d.detail}</div></div>
                    <span className="vx-status-badge vx-badge-warning font-mono">+{d.weight}</span>
                  </div>
                </div>
              ))}
            </div>
          }
          <div className="mt-5 pt-4 border-t border-[var(--vx-border)]">
            <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold">Recommended Intervention</div>
            <div className="text-sm text-slate-200 mt-2">{risk.intervention}</div>
          </div>
        </div>

        <div className="vx-card p-5">
          <SectionHeader title="Key Metrics"/>
          <div className="grid grid-cols-2 gap-3">
            <MiniStat label="ROAS" value={risk.metrics.roas} suffix="x" />
            <MiniStat label="Health" value={risk.metrics.health_score} />
            <MiniStat label="Overdue" value={risk.metrics.overdue_tasks} />
            <MiniStat label="Approvals" value={risk.metrics.pending_approvals} />
            <MiniStat label="Scheduled" value={risk.metrics.scheduled_content} />
            <MiniStat label="Spend" value={"$"+(risk.metrics.spend||0).toLocaleString()} />
          </div>
        </div>
      </div>

      {accuracy && accuracy.stats.samples > 0 && (
        <div className="vx-card p-5" data-testid="prediction-accuracy-card">
          <SectionHeader title="Prediction Accuracy" subtitle={`Model: ${accuracy.model} · ${accuracy.metric} · ${accuracy.stats.samples} closed loops`}/>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard testId="pa-mae" label="MAE" value={accuracy.stats.mae} suffix="pp"/>
            <KpiCard testId="pa-mape" label="MAPE" value={accuracy.stats.mape} suffix="%"/>
            <KpiCard testId="pa-avg-pred" label="Avg Predicted" value={accuracy.stats.avg_predicted} suffix="%"/>
            <KpiCard testId="pa-avg-act" label="Avg Actual" value={accuracy.stats.avg_actual} suffix="%"/>
          </div>
          {accuracy.samples.length > 0 && (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={accuracy.samples.slice().reverse().map((s,i) => ({i, predicted: s.predicted_ctr, actual: s.actual_ctr}))}>
                <CartesianGrid stroke="#1E2432" strokeDasharray="3 3"/>
                <XAxis dataKey="i" stroke="#64748B" fontSize={10}/>
                <YAxis stroke="#64748B" fontSize={10}/>
                <Tooltip contentStyle={{background:"#121620",border:"1px solid #2A3346",borderRadius:8,fontSize:12}}/>
                <Line type="monotone" dataKey="predicted" stroke="#00E5FF" strokeWidth={2} dot={{r:3}} name="Predicted"/>
                <Line type="monotone" dataKey="actual" stroke="#FF9F1C" strokeWidth={2} dot={{r:3}} name="Actual"/>
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      )}
    </div>
  );
}

function MiniStat({label, value, suffix=""}) {
  return (
    <div className="p-3 bg-[var(--vx-card-hover)] rounded-lg">
      <div className="text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className="font-mono font-bold text-slate-100 mt-1">{value}{suffix}</div>
    </div>
  );
}

// ===================== BUDGET TAB =====================
export function BudgetTab({cid}) {
  const [budgets, setBudgets] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({category:"advertising", allocated:0, period:"monthly", notes:""});
  const [showInv, setShowInv] = useState(false);
  const [invForm, setInvForm] = useState({amount:0, tax:0, due_date:""});

  const load = async () => {
    const [b, i] = await Promise.all([api.get(`/budgets?client_id=${cid}`), api.get(`/invoices?client_id=${cid}`)]);
    setBudgets(b.data); setInvoices(i.data);
  };
  useEffect(()=>{ load(); }, [cid]);

  const create = async (e) => {
    e.preventDefault();
    await api.post("/budgets", {...form, client_id: cid, allocated: Number(form.allocated)});
    toast.success("Budget created"); setShowForm(false); load();
  };
  const createInv = async (e) => {
    e.preventDefault();
    await api.post("/invoices", {...invForm, client_id: cid, amount: Number(invForm.amount), tax: Number(invForm.tax)});
    toast.success("Invoice created"); setShowInv(false); load();
  };

  const statusColor = s => ({healthy:"#10B981",warning:"#F59E0B",critical:"#F43F5E",overspend:"#EF4444"}[s]||"#94A3B8");

  return (
    <div className="space-y-6" data-testid="budget-tab">
      <div className="flex justify-between items-center flex-wrap gap-2">
        <div>
          <h3 className="font-display text-2xl font-bold">Budget & Invoicing</h3>
          <p className="text-xs text-slate-500 mt-1">Retainer usage · Ad spend pacing · Invoice tracking · Data from campaign records</p>
        </div>
        <div className="flex gap-2">
          <button data-testid="new-budget-btn" onClick={()=>setShowForm(true)} className="vx-btn-ghost"><Plus size={12} className="inline mr-1"/>Budget</button>
          <button data-testid="new-invoice-btn" onClick={()=>setShowInv(true)} className="vx-btn-primary"><Plus size={12} className="inline mr-1"/>Invoice</button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {budgets.length === 0 && <EmptyState title="No budgets configured" hint="Create a monthly ad budget to start tracking pacing."/>}
        {budgets.map(b => (
          <div key={b.id} className="vx-card p-5" data-testid={`budget-card-${b.id}`}>
            <div className="flex justify-between items-start">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">{b.period} · {b.category}</div>
                <div className="font-mono text-2xl font-bold mt-1">${b.allocated.toLocaleString()}</div>
              </div>
              <span className="vx-status-badge" style={{background: statusColor(b.status)+"22", color: statusColor(b.status), border: `1px solid ${statusColor(b.status)}55`}}>{b.status}</span>
            </div>
            <div className="mt-3">
              <div className="flex justify-between text-xs text-slate-500 mb-1"><span>{b.utilization_pct}% used</span><span>${b.spent.toLocaleString()} / ${b.allocated.toLocaleString()}</span></div>
              <div className="h-2 bg-[var(--vx-border)] rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all" style={{width:`${Math.min(b.utilization_pct,100)}%`, background: statusColor(b.status)}}/>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-[var(--vx-border)] text-xs">
              <div><div className="text-slate-500">Spent</div><div className="font-mono">${b.spent.toLocaleString()}</div></div>
              <div><div className="text-slate-500">Remaining</div><div className="font-mono">${b.remaining.toLocaleString()}</div></div>
              <div><div className="text-slate-500">Pacing</div><div className="font-mono">{b.utilization_pct}%</div></div>
            </div>
          </div>
        ))}
      </div>

      <div className="vx-card overflow-hidden">
        <div className="p-4 border-b border-[var(--vx-border)]"><h4 className="font-display font-bold">Invoices</h4></div>
        {invoices.length === 0 ? <div className="p-8 text-center text-slate-500 text-sm">No invoices yet.</div> :
        <table className="w-full text-sm" data-testid="invoices-table">
          <thead className="bg-[var(--vx-sidebar)]"><tr className="text-left text-xs uppercase text-slate-500">
            <th className="p-3">Number</th><th>Amount</th><th>Tax</th><th>Total</th><th>Due</th><th>Status</th>
          </tr></thead>
          <tbody>
            {invoices.map(i => (
              <tr key={i.id} className="border-b border-[var(--vx-border)]/60 hover:bg-[var(--vx-card-hover)]">
                <td className="p-3 font-mono font-medium">{i.number}</td>
                <td className="p-3 font-mono">${i.amount?.toLocaleString()}</td>
                <td className="p-3 font-mono text-slate-500">${i.tax?.toLocaleString()}</td>
                <td className="p-3 font-mono font-bold">${i.total?.toLocaleString()}</td>
                <td className="p-3 text-slate-400">{i.due_date ? new Date(i.due_date).toLocaleDateString() : "—"}</td>
                <td className="p-3"><StatusBadge status={i.status}/></td>
              </tr>
            ))}
          </tbody>
        </table>}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={create} className="w-full max-w-md vx-card p-6 space-y-3">
            <div className="flex justify-between items-center"><h3 className="font-display text-xl font-bold">New Budget</h3><button type="button" onClick={()=>setShowForm(false)}><X size={16}/></button></div>
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-xs text-slate-400 uppercase">Category</label>
                <select data-testid="bf-category" className="vx-input mt-1" value={form.category} onChange={e=>setForm({...form,category:e.target.value})}>
                  {["advertising","production","seo","retainer","other"].map(o=><option key={o}>{o}</option>)}
                </select></div>
              <div><label className="text-xs text-slate-400 uppercase">Period</label>
                <select data-testid="bf-period" className="vx-input mt-1" value={form.period} onChange={e=>setForm({...form,period:e.target.value})}>
                  {["monthly","campaign","project"].map(o=><option key={o}>{o}</option>)}
                </select></div>
            </div>
            <div><label className="text-xs text-slate-400 uppercase">Allocated ($)</label>
              <input data-testid="bf-allocated" type="number" className="vx-input mt-1" value={form.allocated} onChange={e=>setForm({...form,allocated:e.target.value})} required/></div>
            <button type="submit" data-testid="submit-budget-btn" className="vx-btn-primary w-full">Create</button>
          </form>
        </div>
      )}
      {showInv && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={createInv} className="w-full max-w-md vx-card p-6 space-y-3">
            <div className="flex justify-between items-center"><h3 className="font-display text-xl font-bold">New Invoice</h3><button type="button" onClick={()=>setShowInv(false)}><X size={16}/></button></div>
            <div><label className="text-xs text-slate-400 uppercase">Amount ($)</label>
              <input data-testid="if-amount" type="number" className="vx-input mt-1" value={invForm.amount} onChange={e=>setInvForm({...invForm,amount:e.target.value})} required/></div>
            <div><label className="text-xs text-slate-400 uppercase">Tax ($)</label>
              <input data-testid="if-tax" type="number" className="vx-input mt-1" value={invForm.tax} onChange={e=>setInvForm({...invForm,tax:e.target.value})}/></div>
            <div><label className="text-xs text-slate-400 uppercase">Due date</label>
              <input data-testid="if-due" type="date" className="vx-input mt-1" value={invForm.due_date} onChange={e=>setInvForm({...invForm,due_date:e.target.value})}/></div>
            <button type="submit" data-testid="submit-invoice-btn" className="vx-btn-primary w-full">Create Invoice</button>
          </form>
        </div>
      )}
    </div>
  );
}

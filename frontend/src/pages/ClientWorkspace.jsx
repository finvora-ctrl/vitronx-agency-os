import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { KpiCard, StatusBadge, SectionHeader, EmptyState } from "../components/atoms";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, CartesianGrid, Legend } from "recharts";
import { useApp } from "../context/AppContext";
import { toast } from "sonner";
import { Sparkles, Plus, Wand2, CheckCircle2, XCircle, Zap } from "lucide-react";
import { CreativeIntelTab, RiskTab, BudgetTab } from "./CreativeIntel";
import { CtrModelPanel, ProfitabilityCard, MessagesPanel, UploadButton } from "./Phase3Kit";
import { fmtINR } from "../lib/fmt";

const COLORS = ["#FF9F1C","#00E5FF","#10B981","#F43F5E","#8B5CF6","#3B82F6"];

const TABS = [
  "Overview","Campaigns","Creative Intel","Content","Calendar","Tasks","Projects","Leads",
  "Approvals","SEO","Analytics","AI Insights","ML Lab","Risk","Budget","Reports","Activity","Brand"
];

export default function ClientWorkspace() {
  const { cid } = useParams();
  const [tab, setTab] = useState("Overview");
  const [client, setClient] = useState(null);
  const [dash, setDash] = useState(null);
  const { switchClient } = useApp();
  const nav = useNavigate();

  useEffect(() => {
    if (!cid) return;
    switchClient(cid);
    api.get(`/clients/${cid}`).then(r => setClient(r.data)).catch(()=>nav("/clients"));
    api.get(`/analytics/client/${cid}`).then(r => setDash(r.data));
  }, [cid]);

  if (!client) return <div className="text-slate-400">Loading workspace…</div>;

  return (
    <div className="space-y-6" data-testid="client-workspace">
      <div className="vx-card p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-bold text-[var(--vx-canvas)]" style={{background:client.logo_color}}>{client.name[0]}</div>
            <div>
              <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold">Client Workspace</div>
              <h1 className="font-display text-3xl font-extrabold tracking-tight">{client.name}</h1>
              <div className="text-sm text-slate-400 mt-1">{client.industry} · {client.website}</div>
            </div>
          </div>
          <div className="flex items-center gap-6 flex-wrap">
            <div className="text-right"><div className="text-[10px] uppercase text-slate-500">Health</div><div className="font-mono text-2xl font-bold text-amber-400">{client.health_score}</div></div>
            <div className="text-right"><div className="text-[10px] uppercase text-slate-500">Retainer</div><div className="font-mono text-2xl font-bold">{fmtINR(client.monthly_retainer)}</div></div>
            <StatusBadge status={client.status}/>
          </div>
        </div>
      </div>

      <div className="border-b border-[var(--vx-border)] overflow-x-auto">
        <div className="flex gap-1 min-w-max">
          {TABS.map(t => (
            <button key={t} data-testid={`tab-${t.toLowerCase().replace(/\s/g,"-")}`}
              onClick={()=>setTab(t)} className={`vx-tab ${tab===t?"active":""}`}>{t}</button>
          ))}
        </div>
      </div>

      <div className="animate-fade-in-up">
        {tab === "Overview" && <OverviewTab dash={dash ? {...dash, _cid: cid} : null} client={client}/>}
        {tab === "Campaigns" && <CrudTab cid={cid} kind="campaigns" fields={["name","platform","objective","status","budget","spend","revenue","conversions"]} required={["name"]}/>}
        {tab === "Creative Intel" && <CreativeIntelTab cid={cid}/>}
        {tab === "Content" && <ContentTab cid={cid}/>}
        {tab === "Calendar" && <CalendarTab cid={cid}/>}
        {tab === "Tasks" && <TasksTab cid={cid}/>}
        {tab === "Projects" && <CrudTab cid={cid} kind="projects" fields={["name","status","priority","progress","budget"]} required={["name"]}/>}
        {tab === "Leads" && <LeadsTab cid={cid}/>}
        {tab === "Approvals" && <ApprovalsTab cid={cid}/>}
        {tab === "SEO" && <SeoTab cid={cid}/>}
        {tab === "Analytics" && <OverviewTab dash={dash ? {...dash, _cid: cid} : null} client={client}/>}
        {tab === "AI Insights" && <AITab cid={cid}/>}
        {tab === "ML Lab" && <MLTab cid={cid}/>}
        {tab === "Risk" && <RiskTab cid={cid}/>}
        {tab === "Budget" && <BudgetTab cid={cid}/>}
        {tab === "Reports" && <ReportsTab cid={cid} client={client}/>}
        {tab === "Activity" && <ActivityTab cid={cid}/>}
        {tab === "Brand" && <BrandTab client={client}/>}
      </div>
    </div>
  );
}

function OverviewTab({dash, client}){
  if (!dash) return <div className="text-slate-400">Loading…</div>;
  const k = dash.kpis;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <KpiCard testId="ov-followers" label="Followers" value={k.followers.toLocaleString()}/>
        <KpiCard testId="ov-engagement" label="Engagement" value={k.engagement_rate} suffix="%"/>
        <KpiCard testId="ov-reach" label="Reach" value={k.reach.toLocaleString()}/>
        <KpiCard testId="ov-visitors" label="Website Visits" value={k.website_visitors.toLocaleString()}/>
        <KpiCard testId="ov-leads" label="Leads" value={k.leads}/>
        <KpiCard testId="ov-conv" label="Conversions" value={k.conversions}/>
        <KpiCard testId="ov-spend" label="Ad Spend" value={fmtINR(k.spend)}/>
        <KpiCard testId="ov-revenue" label="Ad Revenue" value={fmtINR(k.revenue)}/>
        <KpiCard testId="ov-roas" label="ROAS" value={k.roas} suffix="x"/>
        <KpiCard testId="ov-cpa" label="CPA" prefix="$" value={k.cpa}/>
        <KpiCard testId="ov-ctr" label="CTR" value={k.ctr} suffix="%"/>
        <KpiCard testId="ov-seo" label="SEO Score" value={k.seo_score}/>
      </div>
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 vx-card p-5">
          <SectionHeader title="30-Day Performance" subtitle="Impressions, clicks, conversions"/>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={dash.trend}>
              <CartesianGrid stroke="#1E2432" strokeDasharray="3 3"/>
              <XAxis dataKey="date" stroke="#64748B" fontSize={10}/>
              <YAxis stroke="#64748B" fontSize={10}/>
              <Tooltip contentStyle={{background:"#121620",border:"1px solid #2A3346",borderRadius:8,fontSize:12}}/>
              <Line type="monotone" dataKey="impressions" stroke="#FF9F1C" strokeWidth={2} dot={false}/>
              <Line type="monotone" dataKey="clicks" stroke="#00E5FF" strokeWidth={2} dot={false}/>
              <Line type="monotone" dataKey="conversions" stroke="#10B981" strokeWidth={2} dot={false}/>
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="vx-card p-5">
          <SectionHeader title="Ad Spend by Platform"/>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={dash.platform_split} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={4}>
                {dash.platform_split.map((_,i)=> <Cell key={i} fill={COLORS[i%COLORS.length]}/>)}
              </Pie>
              <Tooltip contentStyle={{background:"#121620",border:"1px solid #2A3346",borderRadius:8,fontSize:12}}/>
              <Legend wrapperStyle={{fontSize:11,color:"#94A3B8"}}/>
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="vx-card p-5">
        <SectionHeader title="Lead Funnel"/>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={dash.lead_funnel}>
            <CartesianGrid stroke="#1E2432" strokeDasharray="3 3"/>
            <XAxis dataKey="stage" stroke="#64748B" fontSize={11}/>
            <YAxis stroke="#64748B" fontSize={11}/>
            <Tooltip contentStyle={{background:"#121620",border:"1px solid #2A3346",borderRadius:8,fontSize:12}}/>
            <Bar dataKey="count" fill="#FF9F1C" radius={[6,6,0,0]}/>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <ProfitabilityCard clientId={dash._cid || client?.id || ""}/>
        <MessagesPanel clientId={dash._cid || client?.id || ""} title="Client Conversation"/>
      </div>
    </div>
  );
}

function CrudTab({cid, kind, fields, required=[]}){
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({});

  const load = () => api.get(`/${kind}?client_id=${cid}`).then(r=>setItems(r.data));
  useEffect(()=>{ load(); }, [cid]);

  const submit = async (e) => {
    e.preventDefault();
    const payload = {client_id: cid};
    fields.forEach(f => { payload[f] = ["budget","spend","revenue","conversions","progress","value","impressions","clicks"].includes(f) ? Number(form[f] || 0) : (form[f] || ""); });
    if (required.some(r => !payload[r])) { toast.error("Missing required fields"); return; }
    try {
      await api.post(`/${kind}`, payload);
      toast.success(`${kind.slice(0,-1)} created`);
      setShowForm(false); setForm({}); load();
    } catch (e) { toast.error("Failed"); }
  };

  const del = async (id) => { await api.delete(`/${kind}/${id}`); toast.success("Deleted"); load(); };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-display text-xl font-bold capitalize">{kind}</h3>
        <button data-testid={`new-${kind}-btn`} className="vx-btn-primary" onClick={()=>setShowForm(true)}><Plus size={14} className="inline mr-1"/>New</button>
      </div>
      <div className="vx-card overflow-hidden">
        <table className="w-full text-sm" data-testid={`${kind}-table`}>
          <thead className="bg-[var(--vx-sidebar)] border-b border-[var(--vx-border)]">
            <tr className="text-left text-xs uppercase tracking-widest text-slate-500">
              {fields.map(f => <th key={f} className="p-3">{f}</th>)}<th></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={fields.length+1} className="p-8 text-center text-slate-500 text-sm">No records yet. Click "New" to add one.</td></tr>}
            {items.map(it => (
              <tr key={it.id} className="border-b border-[var(--vx-border)]/60 hover:bg-[var(--vx-card-hover)]">
                {fields.map(f => (
                  <td key={f} className="p-3">
                    {f === "status" || f === "priority" ? <StatusBadge status={it[f]}/> :
                     ["budget","spend","revenue","value"].includes(f) ? <span className="font-mono">${Number(it[f]||0).toLocaleString()}</span> :
                     <span>{it[f]}</span>}
                  </td>
                ))}
                <td className="p-3"><button data-testid={`delete-${kind}-${it.id}`} onClick={()=>del(it.id)} className="text-xs text-red-400 hover:underline">Delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showForm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid={`${kind}-form-modal`}>
          <form onSubmit={submit} className="w-full max-w-lg vx-card p-6 space-y-3 max-h-[90vh] overflow-y-auto">
            <h3 className="font-display text-xl font-bold capitalize">New {kind.slice(0,-1)}</h3>
            {fields.map(f => (
              <div key={f}>
                <label className="text-xs text-slate-400 uppercase tracking-widest">{f}</label>
                <input data-testid={`${kind}-form-${f}`} className="vx-input mt-1"
                  type={["budget","spend","revenue","conversions","progress","value","impressions","clicks"].includes(f) ? "number" : "text"}
                  value={form[f] || ""} onChange={e=>setForm({...form,[f]:e.target.value})}
                  required={required.includes(f)}/>
              </div>
            ))}
            <div className="flex gap-2">
              <button type="submit" className="vx-btn-primary flex-1" data-testid={`submit-${kind}-btn`}>Create</button>
              <button type="button" onClick={()=>setShowForm(false)} className="vx-btn-ghost">Cancel</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function ContentTab({cid}){
  const [items, setItems] = useState([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiOut, setAiOut] = useState("");
  const [aiLoad, setAiLoad] = useState(false);

  const load = () => api.get(`/content?client_id=${cid}`).then(r=>setItems(r.data));
  useEffect(()=>{load()}, [cid]);

  const submit = async () => {
    setAiOut(""); setAiLoad(true);
    try {
      const {data} = await api.post(`/ai/caption`, {prompt: aiPrompt, client_id: cid});
      setAiOut(data.caption);
    } finally { setAiLoad(false); }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-display text-xl font-bold">Content Library</h3>
        <button data-testid="ai-caption-btn" className="vx-btn-primary" onClick={()=>setAiOpen(true)}><Wand2 size={14} className="inline mr-1"/>AI Caption</button>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map(c => (
          <div key={c.id} className="vx-card p-4" data-testid={`content-card-${c.id}`}>
            <div className="flex items-start justify-between mb-2">
              <span className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">{c.content_type} · {c.platform}</span>
              <StatusBadge status={c.status}/>
            </div>
            <div className="font-medium text-slate-100">{c.title}</div>
            <div className="text-xs text-slate-500 mt-1 line-clamp-2">{c.caption}</div>
            <div className="text-[11px] font-mono text-slate-500 mt-3">Publish: {c.publish_date ? new Date(c.publish_date).toLocaleDateString() : "—"}</div>
          </div>
        ))}
      </div>

      {aiOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="ai-caption-modal">
          <div className="w-full max-w-lg vx-card p-6 space-y-3 vx-glow-cyan">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={16} className="text-cyan-400"/>
              <h3 className="font-display text-xl font-bold">AI Caption Assistant</h3>
            </div>
            <textarea data-testid="ai-prompt-input" className="vx-input min-h-[100px]" placeholder="What's the post about?" value={aiPrompt} onChange={e=>setAiPrompt(e.target.value)}/>
            <button data-testid="ai-generate-btn" onClick={submit} disabled={aiLoad} className="vx-btn-primary w-full">{aiLoad?"Generating…":"Generate caption"}</button>
            {aiOut && <div className="vx-card p-3 text-sm text-slate-200 whitespace-pre-wrap" data-testid="ai-output">{aiOut}</div>}
            <button onClick={()=>setAiOpen(false)} className="vx-btn-ghost w-full">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

function CalendarTab({cid}){
  const [items, setItems] = useState([]);
  useEffect(()=>{ api.get(`/content?client_id=${cid}`).then(r=>setItems(r.data)); }, [cid]);
  // Group by date
  const grouped = {};
  items.forEach(c => {
    if (!c.publish_date) return;
    const d = new Date(c.publish_date).toLocaleDateString('en-US',{month:'short',day:'numeric'});
    (grouped[d] = grouped[d] || []).push(c);
  });
  const days = Object.keys(grouped).sort((a,b) => new Date(a) - new Date(b));
  return (
    <div className="space-y-4" data-testid="calendar-tab">
      <h3 className="font-display text-xl font-bold">Content Calendar</h3>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {days.map(d => (
          <div key={d} className="vx-card p-4">
            <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold mb-2">{d}</div>
            <div className="space-y-2">
              {grouped[d].map(c => (
                <div key={c.id} className="p-2 bg-[var(--vx-card-hover)] rounded-lg border border-[var(--vx-border)]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] uppercase text-slate-500">{c.platform}</span>
                    <StatusBadge status={c.status}/>
                  </div>
                  <div className="text-sm font-medium">{c.title}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TasksTab({cid}){
  const cols = ["To Do","In Progress","Review","Completed"];
  const [items, setItems] = useState([]);
  const [newTask, setNewTask] = useState("");
  const load = () => api.get(`/tasks?client_id=${cid}`).then(r=>setItems(r.data));
  useEffect(()=>{load()}, [cid]);

  const create = async () => {
    if (!newTask) return;
    await api.post("/tasks", {client_id: cid, name: newTask, priority: "Medium", status: "To Do"});
    setNewTask(""); load(); toast.success("Task created");
  };

  const move = async (id, status) => { await api.patch(`/tasks/${id}`, {status}); load(); };

  return (
    <div className="space-y-4" data-testid="tasks-tab">
      <div className="flex gap-2">
        <input data-testid="quick-task-input" className="vx-input flex-1" placeholder="Add a task and press Enter…"
          value={newTask} onChange={e=>setNewTask(e.target.value)} onKeyDown={e=>e.key==='Enter'&&create()}/>
        <button data-testid="quick-task-btn" onClick={create} className="vx-btn-primary">Add</button>
      </div>
      <div className="grid md:grid-cols-4 gap-3">
        {cols.map(col => (
          <div key={col} className="vx-card p-3">
            <div className="text-[11px] uppercase tracking-widest text-slate-400 font-bold mb-2">{col} · {items.filter(i=>i.status===col).length}</div>
            <div className="space-y-2">
              {items.filter(i=>i.status===col).map(t => (
                <div key={t.id} className="p-3 bg-[var(--vx-card-hover)] rounded-lg border border-[var(--vx-border)]" data-testid={`task-card-${t.id}`}>
                  <div className="text-sm font-medium">{t.name}</div>
                  <div className="flex items-center gap-2 mt-2">
                    <StatusBadge status={t.priority}/>
                  </div>
                  <div className="flex gap-1 mt-2">
                    {cols.filter(c=>c!==col).map(c => (
                      <button key={c} onClick={()=>move(t.id, c)} className="text-[10px] text-slate-500 hover:text-amber-400">→{c}</button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function LeadsTab({cid}){
  const stages = ["New","Contacted","Qualified","Proposal","Won","Lost"];
  const [leads, setLeads] = useState([]);
  const load = () => api.get(`/leads?client_id=${cid}`).then(r=>setLeads(r.data));
  useEffect(()=>{load()}, [cid]);
  const move = async (id, status) => { await api.patch(`/leads/${id}`, {status}); load(); };
  return (
    <div className="space-y-4" data-testid="leads-tab">
      <h3 className="font-display text-xl font-bold">Lead CRM Pipeline</h3>
      <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-3">
        {stages.map(s => (
          <div key={s} className="vx-card p-3">
            <div className="text-[11px] uppercase tracking-widest font-bold mb-2 text-slate-400">{s} · {leads.filter(l=>l.status===s).length}</div>
            <div className="space-y-2">
              {leads.filter(l=>l.status===s).map(l => (
                <div key={l.id} className="p-2 bg-[var(--vx-card-hover)] rounded border border-[var(--vx-border)]" data-testid={`lead-${l.id}`}>
                  <div className="text-xs font-medium">{l.name}</div>
                  <div className="text-[10px] text-slate-500">{l.company}</div>
                  <div className="text-[10px] font-mono text-amber-400">${l.value?.toLocaleString()}</div>
                  <select className="vx-input mt-1 text-[10px] py-1" value={l.status} onChange={e=>move(l.id, e.target.value)}>
                    {stages.map(st => <option key={st}>{st}</option>)}
                  </select>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ApprovalsTab({cid}){
  const [items, setItems] = useState([]);
  const load = () => api.get(`/approvals?client_id=${cid}`).then(r=>setItems(r.data));
  useEffect(()=>{load()}, [cid]);
  const act = async (id, action) => {
    await api.post(`/content/${id}/approval`, {action, comment: ""});
    toast.success(action==="approve"?"Approved":"Recorded");
    load();
  };
  return (
    <div className="space-y-4" data-testid="approvals-tab">
      <h3 className="font-display text-xl font-bold">Client Approval Queue</h3>
      {items.length === 0 ? <EmptyState title="No pending approvals" hint="Content moves here when submitted for client review."/> :
       <div className="grid md:grid-cols-2 gap-4">
        {items.map(c => (
          <div key={c.id} className="vx-card p-4" data-testid={`approval-${c.id}`}>
            <div className="flex justify-between items-start">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-slate-500">{c.content_type} · {c.platform}</div>
                <div className="font-medium mt-1">{c.title}</div>
              </div>
              <StatusBadge status={c.status}/>
            </div>
            <div className="text-xs text-slate-400 mt-2">{c.caption}</div>
            <div className="flex gap-2 mt-3">
              <button data-testid={`approve-${c.id}`} onClick={()=>act(c.id,"approve")} className="vx-btn-primary flex-1 flex items-center justify-center gap-1"><CheckCircle2 size={14}/>Approve</button>
              <button data-testid={`reject-${c.id}`} onClick={()=>act(c.id,"reject")} className="vx-btn-ghost flex-1 flex items-center justify-center gap-1"><XCircle size={14}/>Reject</button>
            </div>
          </div>
        ))}
      </div>}
    </div>
  );
}

function SeoTab({cid}){
  const [seo, setSeo] = useState(null);
  useEffect(()=>{ api.get(`/seo/${cid}`).then(r=>setSeo(r.data)); }, [cid]);
  if (!seo) return <div className="text-slate-400">Loading SEO…</div>;
  return (
    <div className="space-y-4" data-testid="seo-tab">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KpiCard testId="seo-score" label="SEO Score" value={seo.score} suffix="/100"/>
        <KpiCard testId="seo-organic" label="Organic Traffic" value={seo.organic_traffic.toLocaleString()}/>
        <KpiCard testId="seo-kws" label="Keywords" value={seo.keywords_tracked}/>
        <KpiCard testId="seo-bl" label="Backlinks" value={seo.backlinks.toLocaleString()}/>
        <KpiCard testId="seo-da" label="Domain Authority" value={seo.domain_authority}/>
      </div>
      <div className="vx-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--vx-sidebar)]"><tr className="text-left text-xs uppercase text-slate-500">
            <th className="p-3">Keyword</th><th>Position</th><th>Change</th><th>Volume</th><th>Difficulty</th>
          </tr></thead>
          <tbody>
            {seo.keywords.map((k,i)=>(
              <tr key={i} className="border-b border-[var(--vx-border)]/60 hover:bg-[var(--vx-card-hover)]">
                <td className="p-3 font-medium">{k.keyword}</td>
                <td className="p-3 font-mono">#{k.position}</td>
                <td className="p-3 font-mono">{k.prev > k.position ? <span className="text-emerald-400">↑ {k.prev-k.position}</span> : <span className="text-red-400">↓ {k.position-k.prev}</span>}</td>
                <td className="p-3 font-mono">{k.volume.toLocaleString()}</td>
                <td className="p-3 font-mono">{k.difficulty}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AITab({cid}){
  const [insights, setInsights] = useState([]);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  const load = () => api.get(`/ai/insights/${cid}`).then(r=>setInsights(r.data));
  useEffect(()=>{load()}, [cid]);

  const generate = async () => {
    setLoading(true);
    try {
      const {data} = await api.post(`/ai/generate/${cid}`);
      setInsights(data.insights); setSummary(data.ai_summary);
      toast.success("AI insights generated");
    } finally { setLoading(false); }
  };

  return (
    <div className="space-y-4" data-testid="ai-tab">
      <div className="flex justify-between items-center">
        <h3 className="font-display text-xl font-bold">AI Insights & Recommendations</h3>
        <button data-testid="ai-generate-insights-btn" onClick={generate} disabled={loading} className="vx-btn-primary">
          <Sparkles size={14} className="inline mr-1"/>{loading?"Generating…":"Generate Insights"}
        </button>
      </div>
      {summary && (
        <div className="vx-card p-5 vx-glow-cyan border-cyan-500/30" data-testid="ai-summary">
          <div className="flex items-center gap-2 mb-2"><Sparkles size={14} className="text-cyan-400"/><span className="text-[10px] uppercase tracking-widest text-cyan-400 font-bold">AI Weekly Summary</span></div>
          <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">{summary}</div>
        </div>
      )}
      <div className="grid md:grid-cols-2 gap-4">
        {insights.length === 0 && <EmptyState title="No AI insights yet" hint="Click Generate Insights to run the AI analysis."/>}
        {insights.map(i => (
          <div key={i.id} className="vx-card p-5 vx-glow-cyan border-cyan-500/20" data-testid={`insight-${i.id}`}>
            <div className="flex items-start justify-between">
              <span className="vx-status-badge vx-badge-ai">{i.confidence}% Confidence</span>
              <StatusBadge status={i.priority}/>
            </div>
            <div className="font-display text-lg font-semibold mt-3">{i.title}</div>
            <div className="text-xs text-slate-500 mt-1">{i.category}</div>
            <div className="text-sm text-slate-300 mt-3">{i.evidence}</div>
            <div className="mt-3 pt-3 border-t border-[var(--vx-border)]">
              <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold">Recommendation</div>
              <div className="text-sm text-slate-200 mt-1">{i.recommendation}</div>
              <div className="mt-2 vx-status-badge vx-badge-success">{i.expected_impact}</div>
            </div>
            <button data-testid={`insight-to-task-${i.id}`}
              onClick={async ()=>{ try{ await api.post("/ai/insight-to-task", {insight_id: i.id, due_days: 3}); toast.success("Task created from recommendation"); load(); } catch(e){ toast.error("Failed"); } }}
              disabled={i.status === "Accepted"}
              className="vx-btn-primary w-full mt-3 flex items-center justify-center gap-2 disabled:opacity-50">
              <Zap size={12}/>{i.status === "Accepted" ? "Task created" : "Create Task"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function MLTab({cid}){
  const [forecast, setForecast] = useState(null);
  const [leads, setLeads] = useState(null);
  const [eff, setEff] = useState([]);
  const [anom, setAnom] = useState(null);
  const [metric, setMetric] = useState("spend");
  const [loading, setLoading] = useState(false);

  const run = async (m = metric) => {
    setLoading(true);
    try {
      const [f, l, e, a] = await Promise.all([
        api.get(`/ml/forecast/${cid}?metric=${m}&horizon=7`),
        api.get(`/ml/lead-scoring/${cid}`),
        api.get(`/ml/campaign-efficiency/${cid}`),
        api.get(`/ml/anomalies/${cid}`),
      ]);
      setForecast(f.data); setLeads(l.data); setEff(e.data); setAnom(a.data);
    } finally { setLoading(false); }
  };
  useEffect(()=>{run()}, [cid]);
  useEffect(()=>{if(forecast) run(metric)}, [metric]);

  if (!forecast) return <div className="text-slate-400">Running ML models…</div>;

  const chartData = forecast.labels.map((d, i) => ({
    date: d, actual: forecast.history[i], smoothed: forecast.smoothed[i]
  })).concat(forecast.forecast.map((v, i) => ({date: `+${i+1}d`, forecast: v})));

  return (
    <div className="space-y-6" data-testid="ml-tab">
      <div className="flex justify-between items-center flex-wrap gap-2">
        <div>
          <h3 className="font-display text-xl font-bold">ML Laboratory</h3>
          <p className="text-xs text-slate-500 mt-1">Real algorithms: OLS regression · Z-score anomaly · Logistic lead scoring · K-means clustering · Pearson correlation</p>
        </div>
        <div className="flex gap-2">
          {["spend","conversions","clicks","impressions"].map(m => (
            <button key={m} data-testid={`ml-metric-${m}`} onClick={()=>setMetric(m)}
              className={`vx-btn-ghost text-xs ${metric===m?"border-amber-400 text-amber-400":""}`}>{m}</button>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <KpiCard testId="ml-slope" label="Trend Slope (OLS)" value={forecast.slope} hint={forecast.trend}/>
        <KpiCard testId="ml-r2" label="Model R²" value={forecast.r2} suffix="/1.0" hint="fit quality"/>
        <KpiCard testId="ml-anomalies" label={`${metric} anomalies`} value={forecast.anomalies.length} hint="|z|>1.8"/>
      </div>

      <div className="vx-card p-5">
        <SectionHeader title={`Linear Forecast — ${metric}`} subtitle={`OLS regression + EMA smoothing (α=0.3) · 7-day horizon`}/>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData}>
            <CartesianGrid stroke="#1E2432" strokeDasharray="3 3"/>
            <XAxis dataKey="date" stroke="#64748B" fontSize={10}/>
            <YAxis stroke="#64748B" fontSize={10}/>
            <Tooltip contentStyle={{background:"#121620",border:"1px solid #2A3346",borderRadius:8,fontSize:12}}/>
            <Legend wrapperStyle={{fontSize:11,color:"#94A3B8"}}/>
            <Line type="monotone" dataKey="actual" stroke="#FF9F1C" strokeWidth={2} dot={false} name="Actual"/>
            <Line type="monotone" dataKey="smoothed" stroke="#00E5FF" strokeWidth={2} dot={false} strokeDasharray="4 2" name="EMA smoothed"/>
            <Line type="monotone" dataKey="forecast" stroke="#10B981" strokeWidth={2} dot={{r:3}} name="Forecast"/>
          </LineChart>
        </ResponsiveContainer>
      </div>

      {leads && (
        <div className="grid lg:grid-cols-3 gap-4">
          <div className="vx-card p-5">
            <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold">Lead Scoring Model</div>
            <div className="text-sm text-slate-400 mt-1">Logistic-weighted sigmoid over source, stage, deal value</div>
            <div className="grid grid-cols-3 gap-3 mt-4">
              <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/20"><div className="text-[10px] uppercase text-red-400">Hot</div><div className="font-mono text-2xl font-bold text-red-400">{leads.summary.hot}</div></div>
              <div className="p-3 bg-amber-500/10 rounded-lg border border-amber-500/20"><div className="text-[10px] uppercase text-amber-400">Warm</div><div className="font-mono text-2xl font-bold text-amber-400">{leads.summary.warm}</div></div>
              <div className="p-3 bg-slate-500/10 rounded-lg border border-slate-500/20"><div className="text-[10px] uppercase text-slate-400">Cold</div><div className="font-mono text-2xl font-bold text-slate-400">{leads.summary.cold}</div></div>
            </div>
          </div>
          <div className="lg:col-span-2 vx-card overflow-hidden">
            <div className="p-4 border-b border-[var(--vx-border)]">
              <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold">Top Scored Leads</div>
            </div>
            <table className="w-full text-sm" data-testid="scored-leads-table">
              <thead className="bg-[var(--vx-sidebar)]"><tr className="text-left text-xs uppercase text-slate-500">
                <th className="p-3">Lead</th><th>Source</th><th>Stage</th><th>Value</th><th>ML Score</th>
              </tr></thead>
              <tbody>
                {leads.leads.slice(0,8).map(l => (
                  <tr key={l.id} className="border-b border-[var(--vx-border)]/60 hover:bg-[var(--vx-card-hover)]">
                    <td className="p-3 font-medium">{l.name}</td>
                    <td className="p-3 text-slate-400">{l.source}</td>
                    <td className="p-3"><StatusBadge status={l.status}/></td>
                    <td className="p-3 font-mono">${l.value?.toLocaleString()}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-[var(--vx-border)] rounded-full overflow-hidden">
                          <div className="h-full" style={{width:`${l.ml_score}%`, background: l.ml_tier==="hot"?"#EF4444":l.ml_tier==="warm"?"#F59E0B":"#94A3B8"}}/>
                        </div>
                        <span className="font-mono text-xs">{l.ml_score}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="vx-card overflow-hidden">
        <div className="p-4 border-b border-[var(--vx-border)]">
          <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold">Campaign Efficiency Index</div>
          <div className="text-xs text-slate-500 mt-1">Composite: ROAS×20 + CTR×500 + CVR×300, capped 0-100</div>
        </div>
        <table className="w-full text-sm" data-testid="campaign-efficiency-table">
          <thead className="bg-[var(--vx-sidebar)]"><tr className="text-left text-xs uppercase text-slate-500">
            <th className="p-3">Campaign</th><th>Platform</th><th>Spend</th><th>ROAS</th><th>Efficiency Index</th>
          </tr></thead>
          <tbody>
            {eff.slice(0,8).map(c => (
              <tr key={c.id} className="border-b border-[var(--vx-border)]/60 hover:bg-[var(--vx-card-hover)]">
                <td className="p-3 font-medium">{c.name}</td>
                <td className="p-3 text-slate-400">{c.platform}</td>
                <td className="p-3 font-mono">${c.spend?.toLocaleString()}</td>
                <td className="p-3 font-mono text-amber-400">{c.roas}x</td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-1.5 bg-[var(--vx-border)] rounded-full overflow-hidden">
                      <div className="h-full vx-topline" style={{width:`${c.efficiency_index}%`}}/>
                    </div>
                    <span className="font-mono text-xs font-bold">{c.efficiency_index}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {anom && (
        <div className="vx-card p-5">
          <SectionHeader title="Anomaly Detection & Correlations" subtitle="Z-score threshold |z|>1.8 · Pearson correlation coefficients"/>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-slate-500 font-bold mb-2">Pearson Correlations</div>
              <div className="space-y-2">
                <div className="p-3 bg-[var(--vx-card-hover)] rounded-lg flex justify-between">
                  <span className="text-sm">Spend ↔ Conversions</span>
                  <span className="font-mono font-bold text-amber-400">{anom.correlation_spend_conversions}</span>
                </div>
                <div className="p-3 bg-[var(--vx-card-hover)] rounded-lg flex justify-between">
                  <span className="text-sm">Clicks ↔ Conversions</span>
                  <span className="font-mono font-bold text-cyan-400">{anom.correlation_clicks_conversions}</span>
                </div>
              </div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-widest text-slate-500 font-bold mb-2">Anomalies Detected</div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {["spend","conversions","clicks","impressions"].flatMap(m =>
                  (anom[m] || []).map(a => (
                    <div key={`${m}-${a.index}`} className="p-2 bg-[var(--vx-card-hover)] rounded-lg text-xs flex justify-between">
                      <span>{m} · day {a.index}</span>
                      <span className={`font-mono font-bold ${a.direction==="spike"?"text-emerald-400":"text-red-400"}`}>{a.direction} z={a.z}</span>
                    </div>
                  ))
                )}
                {["spend","conversions","clicks","impressions"].every(m => !anom[m]?.length) &&
                  <div className="text-xs text-slate-500 p-3">No anomalies at |z|>1.8. Series stable.</div>}
              </div>
            </div>
          </div>
        </div>
      )}

      <CtrModelPanel/>
    </div>
  );
}

function ReportsTab({cid, client}){
  const [report, setReport] = useState(null);
  const gen = async () => { const {data} = await api.get(`/reports/${cid}`); setReport(data); toast.success("Report generated"); };
  return (
    <div className="space-y-4" data-testid="reports-tab">
      <div className="flex justify-between items-center">
        <h3 className="font-display text-xl font-bold">Monthly Client Report</h3>
        <button data-testid="generate-report-btn" onClick={gen} className="vx-btn-primary">Generate Report</button>
      </div>
      {report && (
        <div className="vx-card p-6" data-testid="report-preview">
          <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold">{report.period}</div>
          <h2 className="font-display text-2xl font-bold mt-1">{client.name} — Performance Report</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            {Object.entries(report.kpis).slice(0,8).map(([k,v]) => (
              <div key={k} className="p-3 bg-[var(--vx-card-hover)] rounded-lg">
                <div className="text-[10px] uppercase text-slate-500">{k.replace(/_/g," ")}</div>
                <div className="font-mono font-bold text-slate-100 mt-1">{typeof v === "number" ? v.toLocaleString() : v}</div>
              </div>
            ))}
          </div>
          <div className="text-xs text-slate-500 mt-4">Generated at {new Date(report.generated_at).toLocaleString()}</div>
        </div>
      )}
    </div>
  );
}

function ActivityTab({cid}){
  const [items, setItems] = useState([]);
  useEffect(()=>{ api.get(`/activity?client_id=${cid}`).then(r=>setItems(r.data)); }, [cid]);
  return (
    <div className="vx-card p-5" data-testid="activity-tab">
      <h3 className="font-display text-xl font-bold mb-4">Activity Feed</h3>
      <div className="space-y-3">
        {items.map(a => (
          <div key={a.id} className="flex gap-3 pb-3 border-b border-[var(--vx-border)]/60 last:border-0">
            <div className="w-8 h-8 rounded-full vx-topline flex items-center justify-center text-[11px] font-bold text-[var(--vx-canvas)]">{a.user_name?.[0]}</div>
            <div className="flex-1">
              <div className="text-sm"><span className="font-semibold">{a.user_name}</span> <span className="text-slate-400">{a.action}</span></div>
              <div className="text-[11px] text-slate-500 mt-0.5">{new Date(a.created_at).toLocaleString()}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BrandTab({client}){
  return (
    <div className="vx-card p-6" data-testid="brand-tab">
      <h3 className="font-display text-xl font-bold mb-4">Brand & Strategy</h3>
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-slate-500 font-bold">Brand Name</div>
          <div className="text-lg font-semibold">{client.name}</div>
          <div className="mt-4 text-[11px] uppercase tracking-widest text-slate-500 font-bold">Industry</div>
          <div className="text-slate-200">{client.industry}</div>
          <div className="mt-4 text-[11px] uppercase tracking-widest text-slate-500 font-bold">Website</div>
          <div className="text-cyan-400">{client.website}</div>
          <div className="mt-4 text-[11px] uppercase tracking-widest text-slate-500 font-bold">Primary Contact</div>
          <div className="text-slate-200">{client.primary_contact}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-widest text-slate-500 font-bold">Brand Color</div>
          <div className="flex items-center gap-3 mt-2">
            <div className="w-16 h-16 rounded-xl" style={{background: client.logo_color}}/>
            <span className="font-mono text-sm">{client.logo_color}</span>
          </div>
          <div className="mt-4 text-[11px] uppercase tracking-widest text-slate-500 font-bold">Tone of Voice</div>
          <div className="text-slate-300 text-sm mt-1">Premium, confident, aspirational. Empowers customers with clear value propositions.</div>
        </div>
      </div>
    </div>
  );
}

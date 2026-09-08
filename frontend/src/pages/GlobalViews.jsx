import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { StatusBadge, SectionHeader, KpiCard, EmptyState } from "../components/atoms";
import { useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { toast } from "sonner";
import { CheckCircle2, XCircle } from "lucide-react";

function useClientsMap(){
  const {clients} = useApp();
  const map = {};
  clients.forEach(c => map[c.id] = c);
  return map;
}

export function GlobalCampaigns(){
  const [items, setItems] = useState([]);
  const cmap = useClientsMap();
  useEffect(()=>{ api.get("/campaigns").then(r=>setItems(r.data)); }, []);
  return (
    <div className="space-y-4" data-testid="global-campaigns">
      <SectionHeader title="All Campaigns" subtitle={`${items.length} campaigns across all clients`}/>
      <div className="vx-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--vx-sidebar)]"><tr className="text-left text-xs uppercase text-slate-500">
            <th className="p-3">Campaign</th><th>Client</th><th>Platform</th><th>Status</th><th>Spend</th><th>Revenue</th><th>ROAS</th>
          </tr></thead>
          <tbody>
            {items.map(c => {
              const roas = c.spend ? (c.revenue/c.spend).toFixed(2) : "—";
              return (
              <tr key={c.id} className="border-b border-[var(--vx-border)]/60 hover:bg-[var(--vx-card-hover)]">
                <td className="p-3 font-medium">{c.name}</td>
                <td className="p-3 text-slate-400">{cmap[c.client_id]?.name || "—"}</td>
                <td className="p-3">{c.platform}</td>
                <td className="p-3"><StatusBadge status={c.status}/></td>
                <td className="p-3 font-mono">${c.spend?.toLocaleString()}</td>
                <td className="p-3 font-mono">${c.revenue?.toLocaleString()}</td>
                <td className="p-3 font-mono text-amber-400">{roas}x</td>
              </tr>);
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function GlobalProjects(){
  const [items, setItems] = useState([]);
  const cmap = useClientsMap();
  useEffect(()=>{ api.get("/projects").then(r=>setItems(r.data)); }, []);
  return (
    <div className="space-y-4" data-testid="global-projects">
      <SectionHeader title="All Projects" subtitle={`${items.length} projects across all clients`}/>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map(p => (
          <div key={p.id} className="vx-card p-4">
            <div className="flex justify-between items-start"><StatusBadge status={p.status}/><StatusBadge status={p.priority}/></div>
            <div className="font-medium mt-2">{p.name}</div>
            <div className="text-xs text-slate-500">{cmap[p.client_id]?.name}</div>
            <div className="mt-3">
              <div className="flex justify-between text-[10px] text-slate-500 mb-1"><span>Progress</span><span>{p.progress}%</span></div>
              <div className="h-1.5 bg-[var(--vx-border)] rounded-full overflow-hidden">
                <div className="h-full vx-topline" style={{width:`${p.progress}%`}}/>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function GlobalTasks(){
  const [items, setItems] = useState([]);
  const cmap = useClientsMap();
  const load = () => api.get("/tasks").then(r=>setItems(r.data));
  useEffect(()=>{load()}, []);
  const cols = ["To Do","In Progress","Review","Completed"];
  const move = async (id, status) => { await api.patch(`/tasks/${id}`, {status}); load(); };
  return (
    <div className="space-y-4" data-testid="global-tasks">
      <SectionHeader title="Team Task Board" subtitle="All tasks across agency"/>
      <div className="grid md:grid-cols-4 gap-3">
        {cols.map(col => (
          <div key={col} className="vx-card p-3">
            <div className="text-[11px] uppercase tracking-widest font-bold text-slate-400 mb-2">{col} · {items.filter(t=>t.status===col).length}</div>
            <div className="space-y-2">
              {items.filter(t=>t.status===col).slice(0,10).map(t=>(
                <div key={t.id} className="p-2 bg-[var(--vx-card-hover)] rounded border border-[var(--vx-border)]">
                  <div className="text-xs font-medium">{t.name}</div>
                  <div className="text-[10px] text-slate-500 mt-1">{cmap[t.client_id]?.name}</div>
                  <div className="mt-1"><StatusBadge status={t.priority}/></div>
                  <select className="vx-input mt-1 text-[10px] py-1" value={t.status} onChange={e=>move(t.id,e.target.value)}>{cols.map(c=><option key={c}>{c}</option>)}</select>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function GlobalCalendar(){
  const [items, setItems] = useState([]);
  const cmap = useClientsMap();
  useEffect(()=>{ api.get("/content").then(r=>setItems(r.data)); }, []);
  const grouped = {};
  items.forEach(c => { if (!c.publish_date) return;
    const d = new Date(c.publish_date).toLocaleDateString('en-US',{month:'short',day:'numeric',weekday:'short'});
    (grouped[d] = grouped[d]||[]).push(c);
  });
  return (
    <div className="space-y-4" data-testid="global-calendar">
      <SectionHeader title="Content Calendar" subtitle="All scheduled content"/>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(grouped).slice(0,15).map(([d, arr]) => (
          <div key={d} className="vx-card p-4">
            <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold mb-2">{d}</div>
            <div className="space-y-2">
              {arr.map(c=>(
                <div key={c.id} className="p-2 bg-[var(--vx-card-hover)] rounded border border-[var(--vx-border)]">
                  <div className="flex justify-between text-[10px] text-slate-500 mb-1"><span>{c.platform}</span><StatusBadge status={c.status}/></div>
                  <div className="text-sm font-medium">{c.title}</div>
                  <div className="text-[10px] text-slate-500">{cmap[c.client_id]?.name}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function GlobalTeam(){
  const [team, setTeam] = useState([]);
  useEffect(()=>{ api.get("/team").then(r=>setTeam(r.data)); }, []);
  return (
    <div className="space-y-4" data-testid="global-team">
      <SectionHeader title="Team" subtitle={`${team.length} members`}/>
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {team.map(m => (
          <div key={m.id} className="vx-card p-4">
            <div className="w-12 h-12 rounded-full vx-topline flex items-center justify-center text-lg font-bold text-[var(--vx-canvas)]">{m.name[0]}</div>
            <div className="font-medium mt-2">{m.name}</div>
            <div className="text-xs text-slate-500 capitalize">{m.role.replace(/_/g," ")}</div>
            <div className="mt-3 flex justify-between text-xs">
              <span className="text-slate-500">Active tasks</span>
              <span className="font-mono font-bold text-amber-400">{m.active_tasks}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function GlobalApprovals(){
  const [items, setItems] = useState([]);
  const cmap = useClientsMap();
  const load = () => api.get("/approvals").then(r=>setItems(r.data));
  useEffect(()=>{load()}, []);
  const act = async (id, action) => { await api.post(`/content/${id}/approval`, {action}); toast.success("Done"); load(); };
  return (
    <div className="space-y-4" data-testid="global-approvals">
      <SectionHeader title="Approval Queue" subtitle={`${items.length} items awaiting client approval`}/>
      {items.length === 0 ? <EmptyState title="Inbox zero" hint="No pending approvals across all clients."/> :
       <div className="grid md:grid-cols-2 gap-4">
        {items.map(c => (
          <div key={c.id} className="vx-card p-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-slate-500">{cmap[c.client_id]?.name} · {c.platform}</div>
                <div className="font-medium mt-1">{c.title}</div>
              </div>
              <StatusBadge status={c.status}/>
            </div>
            <div className="flex gap-2 mt-3">
              <button data-testid={`global-approve-${c.id}`} onClick={()=>act(c.id,"approve")} className="vx-btn-primary flex-1"><CheckCircle2 size={14} className="inline mr-1"/>Approve</button>
              <button data-testid={`global-reject-${c.id}`} onClick={()=>act(c.id,"reject")} className="vx-btn-ghost flex-1"><XCircle size={14} className="inline mr-1"/>Reject</button>
            </div>
          </div>
        ))}
      </div>}
    </div>
  );
}

export function GlobalLeads(){
  const [items, setItems] = useState([]);
  const cmap = useClientsMap();
  useEffect(()=>{ api.get("/leads").then(r=>setItems(r.data)); }, []);
  const total = items.reduce((s,l)=>s+(l.value||0),0);
  return (
    <div className="space-y-4" data-testid="global-leads">
      <SectionHeader title="Agency Leads CRM" subtitle={`${items.length} leads · $${total.toLocaleString()} pipeline`}/>
      <div className="vx-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--vx-sidebar)]"><tr className="text-left text-xs uppercase text-slate-500">
            <th className="p-3">Name</th><th>Company</th><th>Client</th><th>Source</th><th>Status</th><th>Value</th>
          </tr></thead>
          <tbody>
            {items.slice(0,50).map(l => (
              <tr key={l.id} className="border-b border-[var(--vx-border)]/60 hover:bg-[var(--vx-card-hover)]">
                <td className="p-3 font-medium">{l.name}</td>
                <td className="p-3 text-slate-400">{l.company}</td>
                <td className="p-3 text-slate-400">{cmap[l.client_id]?.name}</td>
                <td className="p-3">{l.source}</td>
                <td className="p-3"><StatusBadge status={l.status}/></td>
                <td className="p-3 font-mono">${l.value?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function GlobalContent(){
  const [items, setItems] = useState([]);
  const cmap = useClientsMap();
  useEffect(()=>{ api.get("/content").then(r=>setItems(r.data)); }, []);
  return (
    <div className="space-y-4" data-testid="global-content">
      <SectionHeader title="Content Library" subtitle={`${items.length} pieces across all clients`}/>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.slice(0,30).map(c=>(
          <div key={c.id} className="vx-card p-4">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] uppercase tracking-widest text-slate-500">{c.content_type} · {c.platform}</span>
              <StatusBadge status={c.status}/>
            </div>
            <div className="font-medium">{c.title}</div>
            <div className="text-xs text-slate-500 mt-1">{cmap[c.client_id]?.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function GlobalAds(){
  return <GlobalCampaigns/>;
}

export function GlobalSocial(){
  return <GlobalContent/>;
}

export function GlobalAnalytics(){
  const nav = useNavigate();
  const {clients, switchClient} = useApp();
  return (
    <div className="space-y-4" data-testid="global-analytics">
      <SectionHeader title="Analytics" subtitle="Select a client workspace for detailed analytics"/>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {clients.map(c => (
          <button key={c.id} onClick={()=>{switchClient(c.id); nav(`/workspace/${c.id}`)}} className="vx-card p-4 text-left hover:-translate-y-0.5 transition-transform" data-testid={`analytics-client-${c.id}`}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold text-[var(--vx-canvas)]" style={{background:c.logo_color}}>{c.name[0]}</div>
              <div><div className="font-medium">{c.name}</div><div className="text-xs text-slate-500">{c.industry}</div></div>
            </div>
            <div className="mt-3 text-sm text-slate-400">Open analytics →</div>
          </button>
        ))}
      </div>
    </div>
  );
}

export function GlobalReports(){ return <GlobalAnalytics/>; }
export function GlobalAI(){ return <GlobalAnalytics/>; }

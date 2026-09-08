import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { StatusBadge, SectionHeader, EmptyState } from "../components/atoms";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Bell, AlertTriangle, Zap, Plug, Check } from "lucide-react";

export function NotificationsPage() {
  const [data, setData] = useState({notifications: [], unread: 0});
  const nav = useNavigate();
  const load = () => api.get("/notifications").then(r => setData(r.data));
  useEffect(()=>{load()}, []);

  const compute = async () => {
    const {data: r} = await api.post("/notifications/compute");
    toast.success(`Scanned agency — ${r.created} new alerts`);
    load();
  };
  const readAll = async () => { await api.post("/notifications/read-all"); load(); };
  const readOne = async (id) => { await api.post(`/notifications/${id}/read`); load(); };

  const sevIcon = { critical: <AlertTriangle size={14} className="text-red-400"/>, warning: <AlertTriangle size={14} className="text-amber-400"/>, info: <Bell size={14} className="text-cyan-400"/>, success: <Check size={14} className="text-emerald-400"/> };

  return (
    <div className="space-y-4" data-testid="notifications-page">
      <SectionHeader title="Notification Center" subtitle={`${data.unread} unread · ${data.notifications.length} total`}
        action={<div className="flex gap-2">
          <button data-testid="compute-notifications-btn" onClick={compute} className="vx-btn-ghost text-xs"><Zap size={12} className="inline mr-1"/>Scan Agency</button>
          <button data-testid="read-all-btn" onClick={readAll} className="vx-btn-primary text-xs">Mark all read</button>
        </div>}/>
      {data.notifications.length === 0 ? <EmptyState title="All clear" hint="No notifications right now. Run 'Scan Agency' to generate alerts from live conditions."/> :
       <div className="space-y-2">
        {data.notifications.map(n => (
          <div key={n.id} className={`vx-card p-4 flex items-start gap-3 cursor-pointer ${!n.read?"border-amber-400/40":""}`}
               data-testid={`notif-${n.id}`} onClick={()=>{ readOne(n.id); if(n.link) nav(n.link); }}>
            <div className="mt-1">{sevIcon[n.severity] || sevIcon.info}</div>
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-slate-100">{n.title}</span>
                {!n.read && <span className="w-2 h-2 rounded-full bg-amber-400"/>}
                <span className="text-[10px] text-slate-500 ml-auto">{new Date(n.created_at).toLocaleString()}</span>
              </div>
              <div className="text-xs text-slate-400 mt-1">{n.message}</div>
            </div>
          </div>
        ))}
       </div>}
    </div>
  );
}

export function IntegrationsPage() {
  const [items, setItems] = useState([]);
  const [preview, setPreview] = useState(null);
  useEffect(()=>{ api.get("/integrations").then(r=>setItems(r.data)); }, []);
  const showPreview = async (provider) => {
    const {data} = await api.get(`/integrations/${provider}/preview`);
    setPreview({provider, ...data});
  };
  return (
    <div className="space-y-4" data-testid="integrations-page">
      <SectionHeader title="Integrations" subtitle="Provider-agnostic layer · Live mode requires configured API credentials · Never fake real data"/>
      <div className="grid md:grid-cols-2 gap-4">
        {items.map(it => (
          <div key={it.provider} className="vx-card p-5" data-testid={`integration-${it.provider}`}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[var(--vx-card-hover)] flex items-center justify-center"><Plug size={16} className="text-amber-400"/></div>
                <div>
                  <div className="font-semibold capitalize">{it.provider.replace(/_/g," ")}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{it.configured ? "Credentials configured" : `${it.missing_env.length} env vars missing`}</div>
                </div>
              </div>
              <span className={`vx-status-badge ${it.mode==="live"?"vx-badge-success":"vx-badge-warning"}`}>{it.mode.toUpperCase()}</span>
            </div>
            <div className="mt-3 text-[10px] text-slate-500 font-mono">Requires: {it.required_env.join(", ")}</div>
            <button data-testid={`preview-${it.provider}`} onClick={()=>showPreview(it.provider)} className="vx-btn-ghost text-xs mt-3 w-full">Preview 7-day data</button>
          </div>
        ))}
      </div>
      {preview && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={()=>setPreview(null)}>
          <div className="w-full max-w-2xl vx-card p-6 max-h-[80vh] overflow-y-auto" onClick={e=>e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-display text-xl font-bold capitalize">{preview.provider.replace(/_/g," ")} Preview</h3>
              <span className={`vx-status-badge ${preview.mode==="live"?"vx-badge-success":"vx-badge-warning"}`}>{preview.mode?.toUpperCase()}</span>
            </div>
            <div className="text-xs text-amber-400 mb-3">{preview.note}</div>
            {preview.data && preview.data.length > 0 ? (
              <table className="w-full text-xs">
                <thead><tr className="text-left text-slate-500"><th className="p-2">Date</th><th>Impr</th><th>Clicks</th><th>Conv</th><th>Spend</th><th>ROAS</th></tr></thead>
                <tbody>{preview.data.map((d,i)=>(<tr key={i} className="border-t border-[var(--vx-border)]"><td className="p-2 font-mono">{d.date}</td><td className="font-mono">{d.impressions?.toLocaleString()||'-'}</td><td className="font-mono">{d.clicks?.toLocaleString()||'-'}</td><td className="font-mono">{d.conversions??'-'}</td><td className="font-mono">${d.spend??'-'}</td><td className="font-mono">{d.roas??'-'}x</td></tr>))}</tbody>
              </table>
            ) : <div className="text-sm text-slate-400">{preview.message || "No data available."}</div>}
          </div>
        </div>
      )}
    </div>
  );
}

// Client Portal — simplified layout
export function ClientPortalHome() {
  const [risk, setRisk] = useState(null);
  const [pending, setPending] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [user, setUser] = useState(null);
  useEffect(()=>{
    api.get("/auth/me").then(r=>{ setUser(r.data); const cid = r.data.client_id;
      if (cid) {
        api.get(`/risk/${cid}`).then(x=>setRisk(x.data));
        api.get(`/approvals?client_id=${cid}`).then(x=>setPending(x.data));
        api.get(`/invoices?client_id=${cid}`).then(x=>setInvoices(x.data));
      }
    });
  }, []);
  const nav = useNavigate();
  const act = async (id, action) => { await api.post(`/content/${id}/approval`, {action}); toast.success("Recorded"); api.get(`/approvals?client_id=${user.client_id}`).then(x=>setPending(x.data)); };

  return (
    <div className="space-y-6" data-testid="client-portal-home">
      <div>
        <div className="text-[11px] uppercase tracking-widest text-cyan-400 font-bold">Client Portal</div>
        <h1 className="font-display text-3xl font-extrabold mt-1">Welcome back, {user?.name}</h1>
        <p className="text-slate-400 text-sm mt-1">Your dedicated view — approvals, reports, invoices and messages.</p>
      </div>
      {risk && (
        <div className="vx-card p-5" style={{borderLeft: `3px solid ${{critical:"#EF4444",high:"#F59E0B",medium:"#F59E0B",low:"#10B981"}[risk.risk_level]}`}}>
          <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold">Your account health</div>
          <div className="flex items-center justify-between mt-2">
            <div>
              <div className="font-display text-2xl font-bold capitalize">{risk.risk_level} risk</div>
              <div className="text-xs text-slate-500">Score {risk.risk_score}/100 · ROAS {risk.metrics.roas}x</div>
            </div>
            <div className="text-right"><div className="font-mono text-3xl font-bold text-amber-400">{risk.metrics.health_score}</div><div className="text-[10px] uppercase text-slate-500">Health</div></div>
          </div>
        </div>
      )}
      <div className="vx-card p-5">
        <SectionHeader title="Awaiting your approval" subtitle={`${pending.length} items ready for review`}/>
        {pending.length === 0 ? <EmptyState title="Nothing to approve" hint="You're all caught up."/> :
         <div className="space-y-3">
          {pending.map(c => (
            <div key={c.id} className="p-4 bg-[var(--vx-card-hover)] rounded-lg flex items-center justify-between gap-4" data-testid={`portal-approval-${c.id}`}>
              <div className="flex-1">
                <div className="text-[10px] uppercase text-slate-500">{c.platform} · {c.content_type}</div>
                <div className="font-medium">{c.title}</div>
                <div className="text-xs text-slate-500 mt-1">{c.caption}</div>
              </div>
              <div className="flex gap-2">
                <button data-testid={`portal-approve-${c.id}`} onClick={()=>act(c.id,"approve")} className="vx-btn-primary text-xs">Approve</button>
                <button data-testid={`portal-reject-${c.id}`} onClick={()=>act(c.id,"reject")} className="vx-btn-ghost text-xs">Reject</button>
              </div>
            </div>
          ))}
         </div>
        }
      </div>
      <div className="vx-card p-5">
        <SectionHeader title="Recent invoices"/>
        {invoices.length === 0 ? <div className="text-slate-500 text-sm">No invoices.</div> :
         <div className="space-y-2">
          {invoices.slice(0,5).map(i => (
            <div key={i.id} className="flex justify-between p-3 bg-[var(--vx-card-hover)] rounded-lg">
              <div><div className="font-mono font-medium">{i.number}</div><div className="text-xs text-slate-500">Due {i.due_date?new Date(i.due_date).toLocaleDateString():"—"}</div></div>
              <div className="text-right"><div className="font-mono font-bold">${i.total?.toLocaleString()}</div><StatusBadge status={i.status}/></div>
            </div>
          ))}
         </div>}
      </div>
    </div>
  );
}

// Needs Attention widget for agency dashboard
export function NeedsAttentionSection() {
  const [items, setItems] = useState([]);
  const nav = useNavigate();
  useEffect(()=>{ api.get("/analytics/needs-attention").then(r=>setItems(r.data)); }, []);
  if (items.length === 0) return null;
  const sevColor = {critical:"#EF4444", high:"#F59E0B", warning:"#F59E0B", info:"#3B82F6"};
  return (
    <div className="vx-card p-5" data-testid="needs-attention">
      <SectionHeader title="Needs Attention" subtitle={`${items.length} prioritized items across the agency`}/>
      <div className="space-y-2">
        {items.slice(0,8).map((it, i) => (
          <div key={i} onClick={()=>nav(it.link)} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[var(--vx-card-hover)] cursor-pointer border-l-2" style={{borderLeftColor: sevColor[it.severity]}} data-testid={`attention-${i}`}>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-[var(--vx-canvas)]" style={{background: it.logo_color || "#94A3B8"}}>{it.client_name?.[0]}</div>
            <div className="flex-1">
              <div className="text-sm font-medium">{it.title}</div>
              <div className="text-[11px] text-slate-500">{it.detail}</div>
            </div>
            <span className="vx-status-badge" style={{background: sevColor[it.severity]+"22", color: sevColor[it.severity], border: `1px solid ${sevColor[it.severity]}55`}}>{it.severity}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

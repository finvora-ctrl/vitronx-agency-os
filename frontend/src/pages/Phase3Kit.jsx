import React, { useEffect, useState, useRef } from "react";
import { api } from "../lib/api";
import { fmtINR, fmtDateIN, INDIAN_STATES } from "../lib/fmt";
import { SectionHeader, KpiCard, StatusBadge, EmptyState } from "../components/atoms";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { Sparkles, Search as SearchIcon, Upload, Send, Trophy, Plus, X, FileText, Zap, TrendingUp, TrendingDown } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

// ================ DAILY BRIEF ================
export function DailyBriefCard() {
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();
  const load = async () => { setLoading(true); try { const {data} = await api.get("/analytics/daily-brief"); setBrief(data); } finally { setLoading(false); } };
  useEffect(()=>{load()}, []);
  return (
    <div className="vx-card p-5 vx-glow-cyan border-cyan-500/20" data-testid="daily-brief">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-cyan-400"/>
          <span className="text-[10px] uppercase tracking-widest text-cyan-400 font-bold">VITRONX Daily Brief</span>
        </div>
        <button data-testid="refresh-brief" onClick={load} className="vx-btn-ghost text-xs">{loading?"…":"Refresh"}</button>
      </div>
      {!brief ? <div className="text-sm text-slate-400">Generating…</div> :
      <>
        <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">{brief.narrative}</div>
        {brief.facts.top_priorities.length > 0 && (
          <div className="mt-4 pt-3 border-t border-[var(--vx-border)]">
            <div className="text-[10px] uppercase text-slate-500 font-bold mb-2">Top Priorities</div>
            {brief.facts.top_priorities.slice(0,3).map((p, i) => (
              <div key={i} onClick={()=>nav(p.link)} className="text-xs text-slate-300 cursor-pointer hover:text-amber-400 py-1">
                <span className="text-amber-400 mr-2">●</span>{p.title}
              </div>
            ))}
          </div>
        )}
        {brief.facts.top_creatives.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[var(--vx-border)]">
            <div className="text-[10px] uppercase text-slate-500 font-bold mb-2">Top Performing Creatives</div>
            {brief.facts.top_creatives.map((c,i)=>(
              <div key={i} className="text-xs text-slate-300 py-1 flex justify-between"><span>{c.name}</span><span className="font-mono text-emerald-400">{c.ctr}%</span></div>
            ))}
          </div>
        )}
      </>}
    </div>
  );
}

// ================ GLOBAL SEARCH ================
export function GlobalSearchBox() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const ref = useRef();
  useEffect(() => {
    if (q.length < 2) { setResults(null); return; }
    const t = setTimeout(async () => {
      try { const {data} = await api.get(`/search?q=${encodeURIComponent(q)}`); setResults(data); setOpen(true); } catch {}
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const go = (path) => { setOpen(false); setQ(""); nav(path); };

  return (
    <div className="flex-1 max-w-xl relative" ref={ref} data-testid="global-search-wrap">
      <SearchIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 z-10"/>
      <input data-testid="global-search-input" value={q} onFocus={()=>results && setOpen(true)}
        onChange={e=>setQ(e.target.value)} placeholder="Search clients, campaigns, creatives, leads, invoices…"
        className="vx-input pl-9" onBlur={()=>setTimeout(()=>setOpen(false), 200)}/>
      {open && results && (
        <div className="absolute left-0 right-0 top-full mt-1 bg-[var(--vx-popover)] border border-[var(--vx-border-active)] rounded-xl shadow-2xl z-50 max-h-[70vh] overflow-y-auto" data-testid="search-results">
          {results.total === 0 ? <div className="p-6 text-center text-xs text-slate-500">No matches for "{q}"</div> :
           Object.entries(results.results).map(([kind, items]) => items.length ? (
            <div key={kind} className="border-b border-[var(--vx-border)] last:border-0">
              <div className="px-3 py-2 text-[10px] uppercase tracking-widest text-slate-500 font-bold bg-[var(--vx-canvas)]/40">{kind}</div>
              {items.map(it => {
                const label = it.name || it.title || it.number;
                const sub = it.industry || it.platform || it.company || it.content_type || "";
                const path = kind === "clients" ? `/workspace/${it.id}` :
                             kind === "campaigns" ? `/workspace/${it.client_id}` :
                             kind === "creatives" ? `/workspace/${it.client_id}` :
                             kind === "content" ? `/workspace/${it.client_id}` :
                             kind === "leads" ? `/leads` :
                             kind === "invoices" ? `/workspace/${it.client_id}` :
                             kind === "tasks" ? `/tasks` :
                             kind === "projects" ? `/projects` : "/";
                return (
                  <div key={it.id} onClick={()=>go(path)} className="px-3 py-2 hover:bg-[var(--vx-card-hover)] cursor-pointer" data-testid={`search-result-${kind}-${it.id}`}>
                    <div className="text-sm font-medium">{label}</div>
                    {sub && <div className="text-[11px] text-slate-500">{sub}</div>}
                  </div>
                );
              })}
            </div>
          ) : null)}
        </div>
      )}
    </div>
  );
}

// ================ MESSAGES ================
export function MessagesPanel({clientId, entityType = "general", entityId = null, title = "Messages"}) {
  const [messages, setMessages] = useState([]);
  const [body, setBody] = useState("");
  const [user, setUser] = useState(null);
  const load = async () => {
    let url = `/messages?client_id=${clientId}&entity_type=${entityType}`;
    if (entityId) url += `&entity_id=${entityId}`;
    const {data} = await api.get(url); setMessages(data);
  };
  useEffect(()=>{ if (clientId) { load(); api.get("/auth/me").then(r=>setUser(r.data)); } }, [clientId, entityType, entityId]);

  const send = async () => {
    if (!body.trim()) return;
    await api.post("/messages", {client_id: clientId, entity_type: entityType, entity_id: entityId, body});
    setBody(""); load();
  };

  return (
    <div className="vx-card overflow-hidden flex flex-col" style={{maxHeight: 480}} data-testid="messages-panel">
      <div className="p-3 border-b border-[var(--vx-border)] text-[11px] uppercase tracking-widest font-bold text-slate-400">{title}</div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-[200px]">
        {messages.length === 0 ? <div className="text-center text-xs text-slate-500 py-8">No messages yet. Start the conversation.</div> :
         messages.map(m => {
          const mine = user && m.sender_id === user.id;
          return (
            <div key={m.id} className={`flex ${mine?"justify-end":""}`} data-testid={`msg-${m.id}`}>
              <div className={`max-w-[75%] p-3 rounded-lg text-sm ${mine ? "bg-amber-500/15 border border-amber-500/30 text-slate-100" : "bg-[var(--vx-card-hover)] border border-[var(--vx-border)]"}`}>
                <div className="text-[10px] uppercase tracking-widest opacity-70 mb-1">{m.sender_name} · {m.sender_role}</div>
                <div className="whitespace-pre-wrap">{m.body}</div>
                <div className="text-[10px] opacity-50 mt-1">{new Date(m.created_at).toLocaleString()}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="p-3 border-t border-[var(--vx-border)] flex gap-2">
        <input data-testid="msg-input" className="vx-input" value={body} onChange={e=>setBody(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&send()} placeholder="Type a message…"/>
        <button data-testid="msg-send" onClick={send} className="vx-btn-primary"><Send size={14}/></button>
      </div>
    </div>
  );
}

// ================ FILE UPLOAD BUTTON ================
export function UploadButton({clientId, entityType, entityId, onUploaded, label = "Upload asset", accept}) {
  const [busy, setBusy] = useState(false);
  const inputRef = useRef();
  const handle = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file); fd.append("client_id", clientId);
      fd.append("entity_type", entityType); if (entityId) fd.append("entity_id", entityId);
      const {data} = await api.post("/uploads", fd, {headers: {"Content-Type": "multipart/form-data"}});
      toast.success(`Uploaded ${data.filename}`);
      onUploaded && onUploaded(data);
    } catch (e) { toast.error(e?.response?.data?.detail || "Upload failed"); }
    finally { setBusy(false); if (inputRef.current) inputRef.current.value = ""; }
  };
  return (
    <>
      <input ref={inputRef} type="file" onChange={handle} accept={accept} className="hidden" data-testid="upload-input"/>
      <button data-testid="upload-btn" onClick={()=>inputRef.current?.click()} disabled={busy} className="vx-btn-ghost text-xs flex items-center gap-1">
        <Upload size={12}/>{busy?"Uploading…":label}
      </button>
    </>
  );
}

// ================ GST INVOICE FORM ================
export function GSTInvoiceForm({clientId, onCreated, onClose}) {
  const [form, setForm] = useState({
    gst_rate: 18, agency_state: "Maharashtra", client_state: "Maharashtra",
    client_gstin: "", due_date: "", notes: "", payment_terms: "Net 15 days",
    line_items: [{description: "Social Media Management", hsn_sac: "998314", quantity: 1, unit_price: 50000, discount: 0}]
  });

  const subtotal = form.line_items.reduce((s, li) => s + (Number(li.quantity)||0) * (Number(li.unit_price)||0) - (Number(li.discount)||0), 0);
  const gst = subtotal * form.gst_rate / 100;
  const intra = form.agency_state.toLowerCase() === (form.client_state||"").toLowerCase();
  const cgst = intra ? gst/2 : 0, sgst = intra ? gst/2 : 0, igst = intra ? 0 : gst;
  const grand = subtotal + gst;

  const addLine = () => setForm({...form, line_items:[...form.line_items, {description:"", hsn_sac:"998314", quantity:1, unit_price:0, discount:0}]});
  const updateLine = (i, k, v) => { const arr=[...form.line_items]; arr[i][k]=v; setForm({...form, line_items: arr}); };
  const removeLine = (i) => setForm({...form, line_items: form.line_items.filter((_,idx)=>idx!==i)});

  const submit = async (e) => {
    e.preventDefault();
    try {
      const {data} = await api.post("/invoices/gst", {...form, client_id: clientId,
        line_items: form.line_items.map(li=>({...li, quantity:Number(li.quantity), unit_price:Number(li.unit_price), discount:Number(li.discount)}))});
      toast.success(`Invoice ${data.number} created`);
      onCreated && onCreated(data); onClose && onClose();
    } catch (e) { toast.error("Failed"); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-3xl vx-card p-6 space-y-4 max-h-[92vh] overflow-y-auto" data-testid="gst-invoice-form">
        <div className="flex justify-between items-center">
          <h3 className="font-display text-xl font-bold">New GST Invoice</h3>
          <button type="button" onClick={onClose}><X size={16}/></button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <div><label className="text-[10px] uppercase text-slate-400">Agency State</label>
            <select data-testid="gst-agency-state" className="vx-input mt-1 text-xs" value={form.agency_state} onChange={e=>setForm({...form,agency_state:e.target.value})}>{INDIAN_STATES.map(s=><option key={s}>{s}</option>)}</select></div>
          <div><label className="text-[10px] uppercase text-slate-400">Client State</label>
            <select data-testid="gst-client-state" className="vx-input mt-1 text-xs" value={form.client_state} onChange={e=>setForm({...form,client_state:e.target.value})}>{INDIAN_STATES.map(s=><option key={s}>{s}</option>)}</select></div>
          <div><label className="text-[10px] uppercase text-slate-400">Client GSTIN</label>
            <input data-testid="gst-gstin" className="vx-input mt-1 text-xs font-mono" value={form.client_gstin} onChange={e=>setForm({...form,client_gstin:e.target.value})} placeholder="27ABCDE1234F1Z5"/></div>
          <div><label className="text-[10px] uppercase text-slate-400">GST Rate %</label>
            <select data-testid="gst-rate" className="vx-input mt-1 text-xs" value={form.gst_rate} onChange={e=>setForm({...form,gst_rate:Number(e.target.value)})}>{[0,5,12,18,28].map(r=><option key={r}>{r}</option>)}</select></div>
        </div>
        <div>
          <div className="flex justify-between items-center mb-2"><span className="text-[10px] uppercase text-slate-400 font-bold">Line Items</span><button type="button" onClick={addLine} className="text-xs text-amber-400">+ Add row</button></div>
          <div className="space-y-2">
            {form.line_items.map((li, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 items-end p-2 bg-[var(--vx-card-hover)] rounded-lg">
                <div className="col-span-4"><label className="text-[9px] text-slate-500 uppercase">Description</label><input data-testid={`li-desc-${i}`} className="vx-input text-xs" value={li.description} onChange={e=>updateLine(i,"description",e.target.value)} required/></div>
                <div className="col-span-2"><label className="text-[9px] text-slate-500 uppercase">HSN/SAC</label><input data-testid={`li-hsn-${i}`} className="vx-input text-xs font-mono" value={li.hsn_sac} onChange={e=>updateLine(i,"hsn_sac",e.target.value)}/></div>
                <div className="col-span-1"><label className="text-[9px] text-slate-500 uppercase">Qty</label><input data-testid={`li-qty-${i}`} type="number" className="vx-input text-xs" value={li.quantity} onChange={e=>updateLine(i,"quantity",e.target.value)}/></div>
                <div className="col-span-2"><label className="text-[9px] text-slate-500 uppercase">Unit ₹</label><input data-testid={`li-price-${i}`} type="number" className="vx-input text-xs" value={li.unit_price} onChange={e=>updateLine(i,"unit_price",e.target.value)}/></div>
                <div className="col-span-2"><label className="text-[9px] text-slate-500 uppercase">Discount ₹</label><input data-testid={`li-disc-${i}`} type="number" className="vx-input text-xs" value={li.discount} onChange={e=>updateLine(i,"discount",e.target.value)}/></div>
                <div className="col-span-1"><button type="button" onClick={()=>removeLine(i)} className="text-red-400 text-xs pb-2">✕</button></div>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-[var(--vx-card-hover)] rounded-lg p-4 space-y-1 text-sm">
          <div className="flex justify-between"><span className="text-slate-400">Subtotal</span><span className="font-mono font-bold">{fmtINR(subtotal, {decimals:2})}</span></div>
          {intra ? (<>
            <div className="flex justify-between"><span className="text-slate-400">CGST ({form.gst_rate/2}%)</span><span className="font-mono">{fmtINR(cgst,{decimals:2})}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">SGST ({form.gst_rate/2}%)</span><span className="font-mono">{fmtINR(sgst,{decimals:2})}</span></div>
          </>) : (
            <div className="flex justify-between"><span className="text-slate-400">IGST ({form.gst_rate}%) · Inter-state</span><span className="font-mono">{fmtINR(igst,{decimals:2})}</span></div>
          )}
          <div className="flex justify-between pt-2 border-t border-[var(--vx-border)]"><span className="font-bold text-amber-400">Grand Total</span><span className="font-mono font-bold text-lg text-amber-400" data-testid="gst-grand-total">{fmtINR(grand, {decimals:2})}</span></div>
        </div>
        <button type="submit" data-testid="gst-submit" className="vx-btn-primary w-full">Create Invoice</button>
      </form>
    </div>
  );
}

// ================ RANDOM FOREST CTR MODEL PANEL ================
export function CtrModelPanel() {
  const [status, setStatus] = useState(null);
  const [training, setTraining] = useState(false);
  const load = () => api.get("/ml/ctr-model").then(r=>setStatus(r.data));
  useEffect(()=>{load()}, []);
  const train = async () => {
    setTraining(true);
    try { const {data} = await api.post("/ml/ctr-model/train"); toast.success("Model retrained"); load(); }
    finally { setTraining(false); }
  };
  if (!status) return null;
  return (
    <div className="vx-card p-5" data-testid="ctr-model-panel">
      <div className="flex justify-between items-center mb-3">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-cyan-400 font-bold flex items-center gap-1"><Sparkles size={12}/>Random Forest CTR Model</div>
          <div className="text-xs text-slate-500 mt-1">RandomForestRegressor · 80 trees · max_depth=6 · train/test 75/25 split</div>
        </div>
        <button data-testid="retrain-ctr" onClick={train} disabled={training} className="vx-btn-primary text-xs">{training?"Training…":"Retrain"}</button>
      </div>
      {status.status !== "trained" ? <div className="text-sm text-slate-400 py-4 text-center">Model not trained yet. Click Retrain.</div> :
      <>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard testId="ctr-r2" label="R²" value={status.metrics.r2} suffix="/1.0"/>
          <KpiCard testId="ctr-mae" label="MAE" value={status.metrics.mae} suffix="pp"/>
          <KpiCard testId="ctr-rmse" label="RMSE" value={status.metrics.rmse} suffix="pp"/>
          <KpiCard testId="ctr-samples" label="Test Records" value={status.metrics.test_records}/>
        </div>
        <div className="grid md:grid-cols-2 gap-4 mt-4">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold mb-2">Baseline Comparison</div>
            <div className="p-3 bg-[var(--vx-card-hover)] rounded-lg space-y-1 text-xs">
              <div className="flex justify-between"><span>Linear Regression baseline R²</span><span className="font-mono">{status.metrics.baseline_lr.r2}</span></div>
              <div className="flex justify-between"><span>Linear Regression baseline MAE</span><span className="font-mono">{status.metrics.baseline_lr.mae}</span></div>
              <div className="flex justify-between font-bold text-emerald-400 pt-1 border-t border-[var(--vx-border)]"><span>RF improvement (R²)</span><span className="font-mono">+{(status.metrics.r2 - status.metrics.baseline_lr.r2).toFixed(3)}</span></div>
            </div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold mb-2">Feature Importance</div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={status.importance.slice(0,7)} layout="vertical" margin={{left: 10}}>
                <CartesianGrid stroke="#1E2432" strokeDasharray="3 3"/>
                <XAxis type="number" stroke="#64748B" fontSize={10}/>
                <YAxis type="category" dataKey="feature" stroke="#64748B" fontSize={10} width={110}/>
                <Tooltip contentStyle={{background:"#121620",border:"1px solid #2A3346",borderRadius:8,fontSize:12}}/>
                <Bar dataKey="importance" fill="#FF9F1C" radius={[0,4,4,0]}/>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="mt-3 text-[10px] text-slate-500 font-mono">Trained {new Date(status.trained_at).toLocaleString()} · Model {status.model_version}</div>
      </>}
    </div>
  );
}

// ================ CLIENT PROFITABILITY ================
export function ProfitabilityCard({clientId}) {
  const [p, setP] = useState(null);
  useEffect(()=>{ api.get(`/finance/profitability/${clientId}`).then(r=>setP(r.data)); }, [clientId]);
  if (!p) return null;
  const positive = p.gross_profit >= 0;
  return (
    <div className="vx-card p-5" data-testid="profitability-card">
      <SectionHeader title="Client Profitability" subtitle={p.note}/>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <div className="text-[10px] uppercase text-slate-500 font-bold mb-2">Revenue</div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between"><span className="text-slate-400">Retainer</span><span className="font-mono">{fmtINR(p.revenue.retainer)}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Mgmt fee</span><span className="font-mono">{fmtINR(p.revenue.campaign_mgmt_fee)}</span></div>
            <div className="flex justify-between pt-1 border-t border-[var(--vx-border)] font-bold"><span>Total</span><span className="font-mono text-emerald-400">{fmtINR(p.revenue.total)}</span></div>
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase text-slate-500 font-bold mb-2">Estimated Cost</div>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between"><span className="text-slate-400">Team</span><span className="font-mono">{fmtINR(p.cost.team)}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Creative</span><span className="font-mono">{fmtINR(p.cost.creative)}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Vendor</span><span className="font-mono">{fmtINR(p.cost.vendor)}</span></div>
            <div className="flex justify-between pt-1 border-t border-[var(--vx-border)] font-bold"><span>Total</span><span className="font-mono text-red-400">{fmtINR(p.cost.total)}</span></div>
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase text-slate-500 font-bold mb-2">Gross</div>
          <div className="text-3xl font-mono font-extrabold mt-2" style={{color: positive?"#10B981":"#EF4444"}}>{fmtINR(p.gross_profit)}</div>
          <div className={`vx-status-badge mt-2 ${positive?"vx-badge-success":"vx-badge-danger"} flex items-center gap-1 w-fit`}>{positive?<TrendingUp size={11}/>:<TrendingDown size={11}/>}{p.gross_margin_pct}% margin</div>
        </div>
      </div>
    </div>
  );
}

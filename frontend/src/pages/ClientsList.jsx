import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { StatusBadge, SectionHeader } from "../components/atoms";
import { useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { Plus, X } from "lucide-react";
import { toast } from "sonner";

export default function ClientsList() {
  const [clients, setClients] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({name:"",industry:"",website:"",email:"",phone:"",monthly_retainer:0,status:"Active"});
  const nav = useNavigate();
  const { switchClient, fetchClients } = useApp();

  const load = () => api.get("/clients").then(r => setClients(r.data));
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post("/clients", {...form, monthly_retainer: Number(form.monthly_retainer)});
      toast.success("Client created");
      setShowForm(false); setForm({name:"",industry:"",website:"",email:"",phone:"",monthly_retainer:0,status:"Active"});
      load(); fetchClients();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div className="space-y-6" data-testid="clients-page">
      <SectionHeader title="Clients" subtitle={`${clients.length} client workspaces`}
        action={<button data-testid="new-client-btn" className="vx-btn-primary" onClick={()=>setShowForm(true)}><Plus size={14} className="inline mr-1"/>New Client</button>}/>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {clients.map(c => (
          <div key={c.id} className="vx-card p-5 cursor-pointer hover:-translate-y-0.5 transition-transform" data-testid={`client-card-${c.id}`}
               onClick={()=>{ switchClient(c.id); nav(`/workspace/${c.id}`); }}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold text-[var(--vx-canvas)]" style={{background:c.logo_color}}>{c.name[0]}</div>
                <div>
                  <div className="font-semibold text-slate-100">{c.name}</div>
                  <div className="text-xs text-slate-500">{c.industry}</div>
                </div>
              </div>
              <StatusBadge status={c.status}/>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-[var(--vx-border)]">
              <div><div className="text-[10px] uppercase text-slate-500">Projects</div><div className="font-mono font-semibold">{c.active_projects}</div></div>
              <div><div className="text-[10px] uppercase text-slate-500">Campaigns</div><div className="font-mono font-semibold">{c.active_campaigns}</div></div>
              <div><div className="text-[10px] uppercase text-slate-500">Health</div><div className="font-mono font-semibold text-amber-400">{c.health_score}</div></div>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs">
              <span className="text-slate-500">Retainer</span>
              <span className="font-mono font-semibold">${c.monthly_retainer?.toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="new-client-modal">
          <form onSubmit={submit} className="w-full max-w-lg vx-card p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-xl font-bold">New Client</h3>
              <button type="button" onClick={()=>setShowForm(false)} data-testid="close-client-modal"><X size={16}/></button>
            </div>
            {["name","industry","website","email","phone"].map(f => (
              <div key={f}>
                <label className="text-xs text-slate-400 uppercase tracking-widest">{f}</label>
                <input data-testid={`client-form-${f}`} className="vx-input mt-1" value={form[f]} onChange={e=>setForm({...form,[f]:e.target.value})} required={f==="name"||f==="industry"}/>
              </div>
            ))}
            <div>
              <label className="text-xs text-slate-400 uppercase tracking-widest">Monthly Retainer ($)</label>
              <input data-testid="client-form-retainer" type="number" className="vx-input mt-1" value={form.monthly_retainer} onChange={e=>setForm({...form,monthly_retainer:e.target.value})}/>
            </div>
            <button type="submit" className="vx-btn-primary w-full" data-testid="submit-client-btn">Create Client</button>
          </form>
        </div>
      )}
    </div>
  );
}

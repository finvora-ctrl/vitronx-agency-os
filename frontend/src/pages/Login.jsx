import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";

export default function Login() {
  const { user, login } = useApp();
  const [email, setEmail] = useState("finvora@gmail.com");
  const [password, setPassword] = useState("Vitronx@2026");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  useEffect(() => { if (user && user !== false) nav("/"); }, [user, nav]);

  const submit = async (e) => {
    e.preventDefault(); setErr(""); setLoading(true);
    try { await login(email, password); nav("/"); }
    catch (e) { setErr(e?.response?.data?.detail || "Login failed"); }
    finally { setLoading(false); }
  };

  const quick = (u, p) => { setEmail(u); setPassword(p); };

  return (
    <div className="min-h-screen flex" data-testid="login-page">
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl vx-topline flex items-center justify-center font-bold text-[var(--vx-canvas)]">V</div>
            <div>
              <div className="font-display text-2xl font-extrabold tracking-tight">VITRONX</div>
              <div className="text-[11px] uppercase tracking-widest text-slate-500">Agency Operating System</div>
            </div>
          </div>
          <h1 className="font-display text-3xl font-bold text-slate-50 tracking-tight">Sign in to your agency</h1>
          <p className="text-slate-400 text-sm mt-2">Command center for multi-client digital marketing operations.</p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div>
              <label className="text-xs text-slate-400 font-medium">Email</label>
              <input data-testid="login-email-input" className="vx-input mt-1" value={email} onChange={e=>setEmail(e.target.value)} required/>
            </div>
            <div>
              <label className="text-xs text-slate-400 font-medium">Password</label>
              <input data-testid="login-password-input" type="password" className="vx-input mt-1" value={password} onChange={e=>setPassword(e.target.value)} required/>
            </div>
            {err && <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-2" data-testid="login-error">{err}</div>}
            <button data-testid="login-submit-btn" disabled={loading} className="vx-btn-primary w-full">{loading ? "Signing in…" : "Sign in"}</button>
          </form>

          <div className="mt-6 vx-card p-4">
            <div className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold mb-2">Demo accounts (click to autofill)</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button data-testid="demo-admin" onClick={()=>quick("finvora@gmail.com","Vitronx@2026")} className="vx-btn-ghost text-left">Agency Admin</button>
              <button data-testid="demo-manager" onClick={()=>quick("sarah.manager@vitronx.demo","Demo@2026")} className="vx-btn-ghost text-left">Account Manager</button>
              <button data-testid="demo-designer" onClick={()=>quick("riya.designer@vitronx.demo","Demo@2026")} className="vx-btn-ghost text-left">Designer</button>
              <button data-testid="demo-client" onClick={()=>quick("client@vitronx.demo","Demo@2026")} className="vx-btn-ghost text-left">Client Portal</button>
            </div>
          </div>
        </div>
      </div>

      <div className="hidden lg:flex flex-1 items-center justify-center p-8 relative overflow-hidden">
        <div className="absolute inset-0 opacity-40"
             style={{background: "radial-gradient(circle at 30% 30%, rgba(255,159,28,0.20), transparent 60%), radial-gradient(circle at 70% 70%, rgba(0,229,255,0.15), transparent 60%)"}}/>
        <div className="relative z-10 max-w-lg">
          <div className="vx-card p-6 vx-glow-cyan">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={14} className="text-cyan-400"/>
              <span className="text-[10px] uppercase tracking-widest text-cyan-400 font-bold">AI Recommendation</span>
            </div>
            <div className="font-display text-lg font-semibold text-slate-100">Scale Meta campaign for Lumière Cosmetics</div>
            <div className="text-xs text-slate-400 mt-2">Blended ROAS 4.2x, budget utilization 93%. Recommended action: increase budget +18%.</div>
            <div className="mt-3 flex gap-2">
              <span className="vx-status-badge vx-badge-ai">98% Confidence</span>
              <span className="vx-status-badge vx-badge-success">+$42K est.</span>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-3 gap-3">
            {[["12","Clients"],["47","Campaigns"],["₹18.4M","Revenue"]].map(([v,l]) => (
              <div key={l} className="vx-card p-4">
                <div className="font-mono text-xl font-bold">{v}</div>
                <div className="text-[10px] uppercase tracking-widest text-slate-500 mt-1">{l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

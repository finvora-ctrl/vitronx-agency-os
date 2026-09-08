import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { KpiCard, StatusBadge, SectionHeader } from "../components/atoms";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar, CartesianGrid } from "recharts";
import { useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { AlertTriangle, Zap } from "lucide-react";
import { NeedsAttentionSection } from "./Phase2Pages";
import { DailyBriefCard } from "./Phase3Kit";
import { fmtINR } from "../lib/fmt";

const CHART_COLORS = ["#FF9F1C","#00E5FF","#10B981","#F43F5E","#8B5CF6","#3B82F6"];

export default function AgencyDashboard() {
  const [data, setData] = useState(null);
  const nav = useNavigate();
  const { switchClient } = useApp();

  useEffect(() => { api.get("/analytics/agency").then(r => setData(r.data)); }, []);

  if (!data) return <div className="text-slate-400">Loading agency overview…</div>;
  const k = data.kpis;

  return (
    <div className="space-y-6" data-testid="agency-dashboard">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-amber-400/90 font-bold">Agency Command Center</div>
          <h1 className="font-display text-4xl font-extrabold tracking-tight text-slate-50 mt-1">Good afternoon 👋</h1>
          <p className="text-slate-400 text-sm mt-1">Cross-client health, revenue, campaigns and today's priorities.</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <KpiCard testId="kpi-clients" label="Total Clients" value={k.total_clients}/>
        <KpiCard testId="kpi-campaigns" label="Active Campaigns" value={k.active_campaigns}/>
        <KpiCard testId="kpi-projects" label="Active Projects" value={k.active_projects}/>
        <KpiCard testId="kpi-approvals" label="Pending Approvals" value={k.pending_approvals}/>
        <KpiCard testId="kpi-leads" label="Leads (30d)" value={k.total_leads}/>
        <KpiCard testId="kpi-health" label="Avg Health" value={k.avg_health} suffix="/100"/>
        <KpiCard testId="kpi-retainer" label="Monthly Retainer" value={fmtINR(k.monthly_retainer)}/>
        <KpiCard testId="kpi-spend" label="Ad Spend" value={fmtINR(k.monthly_spend)}/>
        <KpiCard testId="kpi-revenue" label="Ad Revenue" value={fmtINR(k.monthly_revenue)}/>
        <KpiCard testId="kpi-roas" label="Blended ROAS" value={k.avg_roas} suffix="x"/>
        <KpiCard testId="kpi-tasks" label="Open Tasks" value={k.tasks_due_today}/>
        <KpiCard testId="kpi-alerts" label="Today's Alerts" value={4} hint="triage"/>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 vx-card p-5">
          <SectionHeader title="12-Week Performance" subtitle="Revenue vs Ad spend across all clients"/>          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={data.trend}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#FF9F1C" stopOpacity={0.4}/><stop offset="95%" stopColor="#FF9F1C" stopOpacity={0}/></linearGradient>
                <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#00E5FF" stopOpacity={0.4}/><stop offset="95%" stopColor="#00E5FF" stopOpacity={0}/></linearGradient>
              </defs>
              <CartesianGrid stroke="#1E2432" strokeDasharray="3 3"/>
              <XAxis dataKey="week" stroke="#64748B" fontSize={11}/>
              <YAxis stroke="#64748B" fontSize={11}/>
              <Tooltip contentStyle={{background:"#121620",border:"1px solid #2A3346",borderRadius:8,fontSize:12}}/>
              <Area type="monotone" dataKey="spend" stroke="#FF9F1C" fill="url(#g1)" strokeWidth={2}/>
              <Area type="monotone" dataKey="revenue" stroke="#00E5FF" fill="url(#g2)" strokeWidth={2}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="vx-card p-5">
          <SectionHeader title="Today's Priorities" subtitle="Requires attention"/>
          <div className="space-y-3">
            {[
              {icon: AlertTriangle, color:"text-amber-400", text:`${k.pending_approvals} approvals waiting`, sub:"3 due today"},
              {icon: AlertTriangle, color:"text-red-400", text:"2 campaigns underperforming", sub:"ROAS < 1.5x"},
              {icon: Zap, color:"text-cyan-400", text:"New AI recommendation", sub:"Lumière — scale Meta budget +18%"},
              {icon: AlertTriangle, color:"text-amber-400", text:`${k.tasks_due_today} open tasks`, sub:"5 overdue"},
            ].map((it, i) => (
              <div key={i} className="flex gap-3 p-3 bg-[var(--vx-card-hover)] rounded-lg border border-[var(--vx-border)]">
                <it.icon size={16} className={it.color + " mt-0.5"}/>
                <div className="flex-1">
                  <div className="text-sm font-medium text-slate-100">{it.text}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{it.sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <NeedsAttentionSection/>

      <div className="grid lg:grid-cols-2 gap-6">
        <DailyBriefCard/>
        <div className="vx-card p-5">
          <SectionHeader title="Client Retainer Breakdown" subtitle="Monthly recurring revenue by client"/>
          <div className="space-y-2">
            {data.clients.map(c => (
              <div key={c.id} className="flex justify-between items-center p-2 bg-[var(--vx-card-hover)] rounded-lg">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-md flex items-center justify-center text-xs font-bold text-[var(--vx-canvas)]" style={{background:c.logo_color}}>{c.name[0]}</div>
                  <span className="text-sm">{c.name}</span>
                </div>
                <span className="font-mono text-sm">{fmtINR(c.monthly_retainer)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="vx-card p-5">
        <SectionHeader title="Client Health Matrix" subtitle="Open a workspace to drill into a client"/>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="client-health-table">
            <thead>
              <tr className="text-left text-xs uppercase tracking-widest text-slate-500 border-b border-[var(--vx-border)]">
                <th className="py-3">Client</th><th>Industry</th><th>Campaigns</th><th>Leads</th><th>Retainer</th><th>Health</th><th></th>
              </tr>
            </thead>
            <tbody>
              {data.clients.map(c => (
                <tr key={c.id} className="border-b border-[var(--vx-border)]/60 hover:bg-[var(--vx-card-hover)]">
                  <td className="py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-[var(--vx-canvas)]" style={{background: c.logo_color}}>{c.name[0]}</div>
                      <span className="font-medium">{c.name}</span>
                    </div>
                  </td>
                  <td className="text-slate-400">{c.industry}</td>
                  <td className="font-mono">{c.campaigns}</td>
                  <td className="font-mono">{c.leads}</td>
                  <td className="font-mono">{fmtINR(c.monthly_retainer)}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-[var(--vx-border)] rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{width:`${c.health}%`, background: c.health > 80 ? "#10B981" : c.health > 65 ? "#F59E0B" : "#EF4444"}}/>
                      </div>
                      <span className="font-mono text-xs">{c.health}</span>
                    </div>
                  </td>
                  <td>
                    <button data-testid={`open-workspace-${c.id}`} onClick={() => { switchClient(c.id); nav(`/workspace/${c.id}`); }} className="vx-btn-ghost text-xs">Open workspace</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";

export function KpiCard({ label, value, delta, prefix = "", suffix = "", testId, hint }) {
  const positive = delta != null ? delta >= 0 : null;
  return (
    <div className="vx-card p-5 relative overflow-hidden" data-testid={testId}>
      <div className="absolute top-0 left-0 right-0 h-[2px] vx-topline opacity-70"/>
      <div className="text-[11px] uppercase tracking-widest text-slate-500 font-semibold">{label}</div>
      <div className="text-2xl font-mono font-bold text-slate-50 mt-2 tracking-tight">{prefix}{value}{suffix}</div>
      <div className="flex items-center justify-between mt-2">
        {delta != null && (
          <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${positive ? "text-emerald-400 bg-emerald-500/10" : "text-red-400 bg-red-500/10"}`}>
            {positive ? <TrendingUp size={11}/> : <TrendingDown size={11}/>} {Math.abs(delta)}%
          </span>
        )}
        {hint && <span className="text-[10px] text-slate-500">{hint}</span>}
      </div>
    </div>
  );
}

export function StatusBadge({ status }) {
  const map = {
    Active: "vx-badge-success", Completed: "vx-badge-info", Paused: "vx-badge-warning",
    "In Progress": "vx-badge-info", "To Do": "vx-badge-neutral", Review: "vx-badge-warning",
    Blocked: "vx-badge-danger", "On Hold": "vx-badge-warning", Planning: "vx-badge-info",
    Draft: "vx-badge-neutral", "Client Review": "vx-badge-warning", Approved: "vx-badge-success",
    Rejected: "vx-badge-danger", Scheduled: "vx-badge-info", Published: "vx-badge-success",
    New: "vx-badge-info", Contacted: "vx-badge-warning", Qualified: "vx-badge-info",
    Proposal: "vx-badge-warning", Won: "vx-badge-success", Lost: "vx-badge-danger",
    Idea: "vx-badge-neutral", Brief: "vx-badge-neutral", Design: "vx-badge-info",
    "Internal Review": "vx-badge-warning",
    High: "vx-badge-warning", Medium: "vx-badge-info", Low: "vx-badge-neutral", Critical: "vx-badge-danger",
  };
  const cls = map[status] || "vx-badge-neutral";
  return <span className={`vx-status-badge ${cls}`}>{status}</span>;
}

export function SectionHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-end justify-between mb-4">
      <div>
        <h2 className="font-display text-2xl font-bold text-slate-50 tracking-tight">{title}</h2>
        {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ title, hint, action }) {
  return (
    <div className="vx-card p-10 text-center">
      <div className="text-lg font-semibold text-slate-200">{title}</div>
      {hint && <div className="text-sm text-slate-500 mt-1">{hint}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

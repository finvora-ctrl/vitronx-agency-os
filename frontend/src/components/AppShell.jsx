import React, { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import {
  LayoutDashboard, Users, Briefcase, Megaphone, ListTodo, CalendarDays,
  UsersRound, CheckCircle2, LineChart, FileBarChart, Share2, Sparkles,
  Bell, Search, ChevronDown, LogOut, Settings, PanelLeftClose, PanelLeftOpen,
  Radio, Target, FileText, Plug, AlertTriangle
} from "lucide-react";
import { api } from "../lib/api";

const NAV_GROUPS = [
  { label: "Global", items: [
    { to: "/", icon: LayoutDashboard, name: "Agency Overview", testId: "nav-agency-overview" },
    { to: "/clients", icon: Users, name: "Clients", testId: "nav-clients" },
    { to: "/projects", icon: Briefcase, name: "Projects", testId: "nav-projects" },
    { to: "/campaigns", icon: Megaphone, name: "Campaigns", testId: "nav-campaigns" },
    { to: "/tasks", icon: ListTodo, name: "Tasks", testId: "nav-tasks" },
    { to: "/calendar", icon: CalendarDays, name: "Calendar", testId: "nav-calendar" },
    { to: "/team", icon: UsersRound, name: "Team", testId: "nav-team" },
    { to: "/approvals", icon: CheckCircle2, name: "Approvals", testId: "nav-approvals" },
    { to: "/reports", icon: FileBarChart, name: "Reports", testId: "nav-reports" },
  ]},
  { label: "Marketing", items: [
    { to: "/social", icon: Share2, name: "Social Hub", testId: "nav-social" },
    { to: "/content", icon: FileText, name: "Content", testId: "nav-content" },
    { to: "/ads", icon: Target, name: "Ads Manager", testId: "nav-ads" },
    { to: "/leads", icon: Radio, name: "Leads CRM", testId: "nav-leads" },
  ]},
  { label: "Intelligence", items: [
    { to: "/analytics", icon: LineChart, name: "Analytics", testId: "nav-analytics" },
    { to: "/ai", icon: Sparkles, name: "AI Insights", testId: "nav-ai" },
    { to: "/risk", icon: AlertTriangle, name: "Risk Center", testId: "nav-risk" },
  ]},
  { label: "Operations", items: [
    { to: "/notifications", icon: Bell, name: "Notifications", testId: "nav-notifications" },
    { to: "/integrations", icon: Plug, name: "Integrations", testId: "nav-integrations" },
  ]},
];

const CLIENT_PORTAL_NAV = [
  { label: "Portal", items: [
    { to: "/portal", icon: LayoutDashboard, name: "Overview", testId: "nav-portal-overview" },
    { to: "/portal/approvals", icon: CheckCircle2, name: "Approvals", testId: "nav-portal-approvals" },
    { to: "/portal/reports", icon: FileBarChart, name: "Reports", testId: "nav-portal-reports" },
    { to: "/portal/notifications", icon: Bell, name: "Updates", testId: "nav-portal-notifications" },
  ]},
];

export default function AppShell({ children }) {
  const { user, clients, activeClient, switchClient, logout } = useApp();
  const [collapsed, setCollapsed] = useState(false);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifData, setNotifData] = useState({notifications: [], unread: 0});
  const nav = useNavigate();

  const isClientRole = user?.role === "client";
  const groups = isClientRole ? CLIENT_PORTAL_NAV : NAV_GROUPS;

  useEffect(() => {
    if (!user) return;
    const fetchNotif = () => api.get("/notifications").then(r => setNotifData(r.data)).catch(()=>{});
    fetchNotif();
    const t = setInterval(fetchNotif, 30000);
    return () => clearInterval(t);
  }, [user]);

  if (user === null) return <div className="p-8 text-slate-400">Loading…</div>;

  return (
    <div className={`vx-shell-grid ${collapsed ? "collapsed" : ""}`} data-testid="app-shell">
      {/* Sidebar */}
      <aside className="bg-[var(--vx-sidebar)] border-r border-[var(--vx-border)] flex flex-col" data-testid="sidebar">
        <div className="p-4 border-b border-[var(--vx-border)] flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg vx-topline flex items-center justify-center font-bold text-[var(--vx-canvas)]">V</div>
          {!collapsed && <div className="flex-1"><div className="font-display font-extrabold text-lg tracking-tight">VITRONX</div><div className="text-[10px] uppercase tracking-widest text-slate-500">Agency OS</div></div>}
          <button data-testid="sidebar-collapse-btn" onClick={() => setCollapsed(!collapsed)} className="text-slate-400 hover:text-white p-1">
            {collapsed ? <PanelLeftOpen size={16}/> : <PanelLeftClose size={16}/>}
          </button>
        </div>

        {/* Client Switcher — hidden for client role */}
        {!collapsed && !isClientRole && (
          <div className="p-3 border-b border-[var(--vx-border)] relative">
            <button data-testid="client-switcher-btn" onClick={() => setSwitcherOpen(!switcherOpen)}
              className="w-full flex items-center gap-2 p-2 rounded-lg bg-[var(--vx-card)] hover:bg-[var(--vx-card-hover)] border border-[var(--vx-border)]">
              <div className="w-7 h-7 rounded-md flex items-center justify-center text-xs font-bold text-[var(--vx-canvas)]" style={{background: activeClient?.logo_color || "#FF9F1C"}}>
                {activeClient?.name?.[0] || "?"}
              </div>
              <div className="flex-1 text-left">
                <div className="text-xs text-slate-500 uppercase tracking-widest">Workspace</div>
                <div className="text-sm font-semibold truncate">{activeClient?.name || "Select client"}</div>
              </div>
              <ChevronDown size={14} className="text-slate-500"/>
            </button>
            {switcherOpen && (
              <div className="absolute left-3 right-3 top-full mt-1 bg-[var(--vx-popover)] border border-[var(--vx-border-active)] rounded-lg shadow-2xl z-50 overflow-hidden" data-testid="client-switcher-menu">
                {clients.map(c => (
                  <button key={c.id} data-testid={`switch-client-${c.id}`}
                    onClick={() => { switchClient(c.id); setSwitcherOpen(false); nav(`/workspace/${c.id}`); }}
                    className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[var(--vx-card-hover)] text-left">
                    <div className="w-6 h-6 rounded-md flex items-center justify-center text-[10px] font-bold text-[var(--vx-canvas)]" style={{background: c.logo_color}}>{c.name[0]}</div>
                    <div className="flex-1 text-sm">{c.name}</div>
                    <div className="text-[10px] text-slate-500">{c.health_score}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <nav className="flex-1 overflow-y-auto p-3 space-y-4">
          {groups.map(g => (
            <div key={g.label}>
              {!collapsed && <div className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold px-2 mb-2">{g.label}</div>}
              <div className="space-y-1">
                {g.items.map(it => (
                  <NavLink key={it.to} to={it.to} end={it.to === "/"} data-testid={it.testId}
                    className={({isActive}) => `vx-nav-item ${isActive ? "active" : ""}`}>
                    <it.icon size={16}/>
                    {!collapsed && <span>{it.name}</span>}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-3 border-t border-[var(--vx-border)]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full vx-topline flex items-center justify-center text-xs font-bold text-[var(--vx-canvas)]">{user?.name?.[0] || "U"}</div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold truncate">{user?.name}</div>
                <div className="text-[10px] text-slate-500 truncate">{user?.role}</div>
              </div>
            )}
            <button data-testid="logout-btn" onClick={logout} className="p-1 text-slate-400 hover:text-red-400"><LogOut size={14}/></button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex flex-col min-h-screen">
        <header className="h-14 border-b border-[var(--vx-border)] px-6 flex items-center gap-4 bg-[var(--vx-canvas)] sticky top-0 z-20">
          <div className="flex-1 max-w-xl relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/>
            <input data-testid="global-search-input" placeholder="Search clients, campaigns, tasks…" className="vx-input pl-9"/>
          </div>
          <button data-testid="notifications-btn" onClick={()=>setNotifOpen(!notifOpen)} className="relative p-2 text-slate-400 hover:text-white">
            <Bell size={16}/>
            {notifData.unread > 0 && <span className="absolute top-0.5 right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-[var(--vx-amber)] text-[9px] font-bold text-[var(--vx-canvas)] flex items-center justify-center">{notifData.unread}</span>}
          </button>
          {notifOpen && (
            <div className="absolute right-4 top-14 w-96 bg-[var(--vx-popover)] border border-[var(--vx-border-active)] rounded-xl shadow-2xl z-50 overflow-hidden" data-testid="notifications-dropdown">
              <div className="p-3 border-b border-[var(--vx-border)] flex justify-between items-center">
                <span className="text-sm font-semibold">Notifications</span>
                <button data-testid="notif-see-all" onClick={()=>{setNotifOpen(false); nav("/notifications");}} className="text-xs text-amber-400 hover:underline">See all</button>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {notifData.notifications.length === 0 ? <div className="p-6 text-center text-xs text-slate-500">No notifications</div> :
                 notifData.notifications.slice(0,6).map(n => (
                  <div key={n.id} onClick={()=>{setNotifOpen(false); if(n.link) nav(n.link);}} className={`p-3 border-b border-[var(--vx-border)] hover:bg-[var(--vx-card-hover)] cursor-pointer ${!n.read?"bg-amber-500/5":""}`}>
                    <div className="flex items-start gap-2">
                      <span className={`w-1.5 h-1.5 mt-1.5 rounded-full shrink-0 ${n.severity==="critical"?"bg-red-400":n.severity==="warning"?"bg-amber-400":"bg-cyan-400"}`}/>
                      <div className="flex-1"><div className="text-xs font-medium">{n.title}</div><div className="text-[11px] text-slate-500 mt-0.5">{n.message}</div></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <button data-testid="settings-btn" onClick={() => nav("/settings")} className="p-2 text-slate-400 hover:text-white"><Settings size={16}/></button>
        </header>
        <div className="flex-1 p-6 animate-fade-in-up">{children}</div>
      </main>
    </div>
  );
}

import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppProvider, useApp } from "./context/AppContext";
import AppShell from "./components/AppShell";
import Login from "./pages/Login";
import AgencyDashboard from "./pages/AgencyDashboard";
import ClientsList from "./pages/ClientsList";
import ClientWorkspace from "./pages/ClientWorkspace";
import { NotificationsPage, IntegrationsPage, ClientPortalHome } from "./pages/Phase2Pages";
import {
  GlobalCampaigns, GlobalProjects, GlobalTasks, GlobalCalendar, GlobalTeam,
  GlobalApprovals, GlobalLeads, GlobalContent, GlobalAds, GlobalSocial,
  GlobalAnalytics, GlobalReports, GlobalAI
} from "./pages/GlobalViews";
import { Toaster } from "sonner";

function Protected({ children, clientOnly = false, agencyOnly = false }) {
  const { user } = useApp();
  if (user === null) return <div className="p-8 text-slate-400">Loading…</div>;
  if (!user) return <Navigate to="/login" replace/>;
  if (user.role === "client" && !clientOnly && !window.location.pathname.startsWith("/portal") && !window.location.pathname.startsWith("/login"))
    return <Navigate to="/portal" replace/>;
  if (agencyOnly && user.role === "client") return <Navigate to="/portal" replace/>;
  return <AppShell>{children}</AppShell>;
}

function AgencyRiskCenter() {
  const [risks, setRisks] = React.useState([]);
  React.useEffect(()=>{ import("./lib/api").then(({api})=>api.get("/risk/agency/all").then(r=>setRisks(r.data))); }, []);
  return (
    <div className="space-y-4" data-testid="risk-center">
      <div><h1 className="font-display text-3xl font-extrabold">Client Risk Center</h1><p className="text-slate-400 text-sm mt-1">All clients ranked by risk level with intervention recommendations</p></div>
      <div className="grid md:grid-cols-2 gap-4">
        {risks.map(r => (
          <a key={r.id} href={`/workspace/${r.id}`} className="vx-card p-5" style={{borderLeft: `3px solid ${{critical:"#EF4444",high:"#F59E0B",medium:"#F59E0B",low:"#10B981"}[r.risk_level]}`}} data-testid={`risk-${r.id}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold text-[var(--vx-canvas)]" style={{background: r.logo_color}}>{r.name[0]}</div>
                <div><div className="font-medium">{r.name}</div><div className="text-xs text-slate-500">{r.industry}</div></div>
              </div>
              <span className="vx-status-badge" style={{background: `${{critical:"#EF4444",high:"#F59E0B",medium:"#F59E0B",low:"#10B981"}[r.risk_level]}22`, color: {critical:"#EF4444",high:"#F59E0B",medium:"#F59E0B",low:"#10B981"}[r.risk_level]}}>{r.risk_level} · {r.risk_score}</span>
            </div>
            <div className="text-xs text-slate-400 mt-3">{r.intervention}</div>
            {r.drivers.length > 0 && <div className="text-[11px] text-slate-500 mt-2">Drivers: {r.drivers.map(d=>d.factor).join(" · ")}</div>}
          </a>
        ))}
      </div>
    </div>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AppProvider>
          <Toaster theme="dark" position="top-right" richColors/>
          <Routes>
            <Route path="/login" element={<Login/>}/>
            <Route path="/" element={<Protected><AgencyDashboard/></Protected>}/>
            <Route path="/clients" element={<Protected><ClientsList/></Protected>}/>
            <Route path="/workspace/:cid" element={<Protected><ClientWorkspace/></Protected>}/>
            <Route path="/campaigns" element={<Protected><GlobalCampaigns/></Protected>}/>
            <Route path="/projects" element={<Protected><GlobalProjects/></Protected>}/>
            <Route path="/tasks" element={<Protected><GlobalTasks/></Protected>}/>
            <Route path="/calendar" element={<Protected><GlobalCalendar/></Protected>}/>
            <Route path="/team" element={<Protected><GlobalTeam/></Protected>}/>
            <Route path="/approvals" element={<Protected><GlobalApprovals/></Protected>}/>
            <Route path="/leads" element={<Protected><GlobalLeads/></Protected>}/>
            <Route path="/content" element={<Protected><GlobalContent/></Protected>}/>
            <Route path="/social" element={<Protected><GlobalSocial/></Protected>}/>
            <Route path="/ads" element={<Protected><GlobalAds/></Protected>}/>
            <Route path="/analytics" element={<Protected><GlobalAnalytics/></Protected>}/>
            <Route path="/reports" element={<Protected><GlobalReports/></Protected>}/>
            <Route path="/ai" element={<Protected><GlobalAI/></Protected>}/>
            <Route path="/risk" element={<Protected agencyOnly><AgencyRiskCenter/></Protected>}/>
            <Route path="/notifications" element={<Protected><NotificationsPage/></Protected>}/>
            <Route path="/integrations" element={<Protected agencyOnly><IntegrationsPage/></Protected>}/>
            <Route path="/portal" element={<Protected clientOnly><ClientPortalHome/></Protected>}/>
            <Route path="/portal/approvals" element={<Protected clientOnly><ClientPortalHome/></Protected>}/>
            <Route path="/portal/reports" element={<Protected clientOnly><ClientPortalHome/></Protected>}/>
            <Route path="/portal/notifications" element={<Protected clientOnly><NotificationsPage/></Protected>}/>
            <Route path="/settings" element={<Protected><div className="text-slate-400">Settings coming soon</div></Protected>}/>
            <Route path="*" element={<Navigate to="/"/>}/>
          </Routes>
        </AppProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;

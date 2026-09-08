import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppProvider, useApp } from "./context/AppContext";
import AppShell from "./components/AppShell";
import Login from "./pages/Login";
import AgencyDashboard from "./pages/AgencyDashboard";
import ClientsList from "./pages/ClientsList";
import ClientWorkspace from "./pages/ClientWorkspace";
import {
  GlobalCampaigns, GlobalProjects, GlobalTasks, GlobalCalendar, GlobalTeam,
  GlobalApprovals, GlobalLeads, GlobalContent, GlobalAds, GlobalSocial,
  GlobalAnalytics, GlobalReports, GlobalAI
} from "./pages/GlobalViews";
import { Toaster } from "sonner";

function Protected({ children }) {
  const { user } = useApp();
  if (user === null) return <div className="p-8 text-slate-400">Loading…</div>;
  if (!user) return <Navigate to="/login" replace/>;
  return <AppShell>{children}</AppShell>;
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
            <Route path="/settings" element={<Protected><div className="text-slate-400">Settings coming soon</div></Protected>}/>
            <Route path="*" element={<Navigate to="/"/>}/>
          </Routes>
        </AppProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;

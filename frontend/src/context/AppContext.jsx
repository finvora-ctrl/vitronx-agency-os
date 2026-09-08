import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

export function AppProvider({ children }) {
  const [user, setUser] = useState(null); // null=loading, false=logged out
  const [clients, setClients] = useState([]);
  const [activeClientId, setActiveClientId] = useState(localStorage.getItem("vx_client") || null);

  const fetchMe = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      return data;
    } catch {
      setUser(false);
      return null;
    }
  }, []);

  const fetchClients = useCallback(async () => {
    try {
      const { data } = await api.get("/clients");
      setClients(data);
      if (!activeClientId && data.length) {
        setActiveClientId(data[0].id);
        localStorage.setItem("vx_client", data[0].id);
      }
      return data;
    } catch {
      return [];
    }
  }, [activeClientId]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    if (data.token) localStorage.setItem("vx_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("vx_token");
    localStorage.removeItem("vx_client");
    setUser(false); setActiveClientId(null); setClients([]);
  };

  const switchClient = (id) => {
    setActiveClientId(id);
    localStorage.setItem("vx_client", id);
  };

  useEffect(() => { fetchMe(); }, [fetchMe]);
  useEffect(() => { if (user) fetchClients(); }, [user, fetchClients]);

  const activeClient = clients.find(c => c.id === activeClientId) || null;

  return (
    <Ctx.Provider value={{ user, clients, activeClient, activeClientId, login, logout, switchClient, fetchClients, refreshMe: fetchMe }}>
      {children}
    </Ctx.Provider>
  );
}

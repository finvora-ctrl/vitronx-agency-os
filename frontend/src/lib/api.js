import axios from "axios";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("vx_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

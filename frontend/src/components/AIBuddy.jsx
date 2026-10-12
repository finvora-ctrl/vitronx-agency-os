import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../lib/api";
import { useApp } from "../context/AppContext";
import { Mic, MicOff, Send, X, Volume2, VolumeX, Square, RotateCcw, Minus } from "lucide-react";

const SR = typeof window !== "undefined" ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null;
const TTS = typeof window !== "undefined" && "speechSynthesis" in window;
const SUGGESTIONS = ["Which campaign needs attention first?", "Why is this client's risk score high?", "Which tasks are overdue?", "How was the CTR prediction generated?"];

export const DogAvatar = ({ size = 56, mood = "idle" }) => (
  <svg viewBox="0 0 64 64" width={size} height={size} className={`vx-dog vx-dog-${mood}`} aria-hidden="true">
    <g className="vx-dog-tail"><path d="M50 44 q10 -4 8 -14" stroke="#FF9F1C" strokeWidth="5" fill="none" strokeLinecap="round"/></g>
    <ellipse cx="32" cy="46" rx="18" ry="12" fill="#FF9F1C"/>
    <circle cx="32" cy="28" r="15" fill="#FFB547"/>
    <ellipse cx="18" cy="22" rx="5" ry="10" fill="#C2410C" transform="rotate(-20 18 22)"/>
    <ellipse cx="46" cy="22" rx="5" ry="10" fill="#C2410C" transform="rotate(20 46 22)"/>
    <g className="vx-dog-eyes"><circle cx="26" cy="27" r="2.4" fill="#0A0C10"/><circle cx="38" cy="27" r="2.4" fill="#0A0C10"/></g>
    <ellipse cx="32" cy="34" rx="6" ry="4.5" fill="#FFE2B8"/>
    <circle cx="32" cy="32.5" r="2" fill="#0A0C10"/>
    <path className="vx-dog-mouth" d="M29 36 q3 3 6 0" stroke="#0A0C10" strokeWidth="1.4" fill="none" strokeLinecap="round"/>
    <rect x="22" y="40" width="20" height="3" rx="1.5" fill="#00E5FF"/>
  </svg>
);

function useSpeech(muted) {
  const [speaking, setSpeaking] = useState(false);
  const speak = (text) => {
    if (!TTS || muted || !text) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/[•*#_`]/g, "").slice(0, 1200));
    const v = window.speechSynthesis.getVoices();
    u.voice = v.find(x => x.lang === "en-IN") || v.find(x => x.lang?.startsWith("en")) || null;
    u.lang = u.voice?.lang || "en-IN";
    u.onstart = () => setSpeaking(true); u.onend = () => setSpeaking(false); u.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(u);
  };
  const stop = () => { if (TTS) window.speechSynthesis.cancel(); setSpeaking(false); };
  return { speaking, speak, stop };
}

function Message({ m, onReplay }) {
  const mine = m.role === "user";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap ${mine ? "bg-amber-500/15 text-amber-50" : m.error ? "bg-red-500/10 text-red-200" : "bg-[var(--vx-card-hover)] text-slate-200"}`} data-testid={`buddy-msg-${m.role}`}>
        {m.text}
        {!mine && !m.error && (
          <div className="flex items-center gap-2 mt-1.5 text-[10px] text-slate-500 flex-wrap">
            {!m.llm && m.llm !== undefined && <span className="text-amber-300">AI offline · computed facts</span>}
            {(m.sources || []).map(s => <a key={s.label} href={s.link} className="text-cyan-400 hover:underline">{s.label}</a>)}
            {TTS && <button onClick={() => onReplay(m.text)} className="hover:text-white flex items-center gap-0.5" data-testid="buddy-replay-btn"><RotateCcw size={10}/>Replay</button>}
          </div>)}
      </div>
    </div>
  );
}

export default function AIBuddy() {
  const { user, activeClientId } = useApp();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [muted, setMuted] = useState(localStorage.getItem("vx_buddy_muted") === "1");
  const [online, setOnline] = useState(navigator.onLine);
  const [notice, setNotice] = useState(false);
  const recRef = useRef(null);
  const endRef = useRef(null);
  const { speaking, speak, stop } = useSpeech(muted);
  const session = useRef(sessionStorage.getItem("vx_buddy_session") || `${Date.now()}-${Math.random().toString(36).slice(2)}`);

  useEffect(() => { sessionStorage.setItem("vx_buddy_session", session.current); }, []);
  useEffect(() => { const on = () => setOnline(true), off = () => setOnline(false); window.addEventListener("online", on); window.addEventListener("offline", off); return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); }; }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, loading]);
  useEffect(() => { if (user && user.role !== "client") api.get("/recommendations").then(r => setNotice(r.data.some(x => x.priority_score >= 80))).catch(() => {}); }, [user]);

  const cid = (loc.pathname.match(/\/workspace\/([^/?]+)/) || [])[1] || (user?.role === "client" ? user.client_id : activeClientId);

  const ask = async (text) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput(""); setMsgs(m => [...m, { role: "user", text: q }]);
    if (!online) { setMsgs(m => [...m, { role: "assistant", error: true, text: "You appear to be offline. Reconnect and try again." }]); return; }
    setLoading(true);
    try {
      const { data } = await api.post("/buddy/chat", { message: q, session_id: session.current, path: loc.pathname, client_id: cid || null });
      setMsgs(m => [...m, { role: "assistant", text: data.answer, llm: data.llm_used, sources: data.sources }]);
      speak(data.answer);
    } catch (e) {
      setMsgs(m => [...m, { role: "assistant", error: true, text: e?.response?.data?.detail || "Sorry, I couldn't reach VITRONX right now. Please try again." }]);
    } finally { setLoading(false); }
  };

  const toggleMic = () => {
    if (!SR) { setMsgs(m => [...m, { role: "assistant", error: true, text: "Voice input isn't supported in this browser. Try Chrome or Edge, or type your question." }]); return; }
    if (listening) { recRef.current?.stop(); return; }
    stop();
    const rec = new SR(); rec.lang = "en-IN"; rec.interimResults = true; rec.maxAlternatives = 1; rec.continuous = false;
    let finalText = "";
    rec.onresult = (e) => { const t = Array.from(e.results).map(r => r[0].transcript).join(" "); setInput(t); if (e.results[e.results.length - 1].isFinal) finalText = t; };
    rec.onerror = (e) => { setListening(false); setMsgs(m => [...m, { role: "assistant", error: true, text: e.error === "not-allowed" ? "Microphone permission was denied. Allow it in browser settings or type instead." : `Voice input error: ${e.error}` }]); };
    rec.onend = () => { setListening(false); if (finalText) ask(finalText); };
    recRef.current = rec; setListening(true); rec.start();
  };

  const toggleMute = () => { const v = !muted; setMuted(v); localStorage.setItem("vx_buddy_muted", v ? "1" : "0"); if (v) stop(); };
  const mood = listening ? "listening" : loading ? "thinking" : speaking ? "speaking" : "idle";
  const status = !online ? "Offline" : listening ? "Listening…" : loading ? "Thinking…" : speaking ? "Speaking…" : "Ask about campaigns, leads, risk, models";

  if (!user) return null;
  return (
    <div className="fixed bottom-4 right-4 z-[60] flex flex-col items-end gap-2" data-testid="ai-buddy">
      {open && (
        <div className="vx-buddy-panel w-[min(370px,calc(100vw-2rem))] h-[min(520px,70vh)] flex flex-col rounded-2xl border border-[var(--vx-border-active)] bg-[var(--vx-popover)]/95 backdrop-blur-xl shadow-2xl" data-testid="buddy-panel">
          <div className="flex items-center gap-2 p-3 border-b border-[var(--vx-border)]">
            <DogAvatar size={32} mood={mood}/>
            <div className="flex-1 min-w-0"><div className="text-sm font-bold">VITRONX AI Buddy</div><div className="text-[10px] text-slate-400 truncate" data-testid="buddy-status">{status}</div></div>
            {speaking && <button onClick={stop} className="p-1.5 text-slate-300 hover:text-white" title="Stop speaking" data-testid="buddy-stop-speaking-btn"><Square size={14}/></button>}
            {TTS && <button onClick={toggleMute} className="p-1.5 text-slate-300 hover:text-white" title={muted ? "Unmute" : "Mute"} data-testid="buddy-mute-btn">{muted ? <VolumeX size={14}/> : <Volume2 size={14}/>}</button>}
            <button onClick={() => setOpen(false)} className="p-1.5 text-slate-300 hover:text-white" title="Minimize" data-testid="buddy-minimize-btn"><Minus size={14}/></button>
            <button onClick={() => { setOpen(false); setMsgs([]); stop(); }} className="p-1.5 text-slate-300 hover:text-white" title="Close" data-testid="buddy-close-btn"><X size={14}/></button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2" data-testid="buddy-messages">
            {msgs.length === 0 && (
              <div className="space-y-2">
                <div className="text-xs text-slate-400">Woof! I answer using live VITRONX data you're allowed to see{cid ? " for the selected client" : ""}.{!TTS && " Spoken replies aren't supported in this browser."}</div>
                {SUGGESTIONS.map(s => <button key={s} onClick={() => ask(s)} className="block w-full text-left text-xs p-2 rounded-lg bg-[var(--vx-card-hover)] hover:bg-[var(--vx-card)] text-slate-300" data-testid="buddy-suggestion">{s}</button>)}
              </div>)}
            {msgs.map((m, i) => <Message key={i} m={m} onReplay={speak}/>)}
            {loading && <div className="text-xs text-slate-400 flex items-center gap-2" data-testid="buddy-loading"><span className="vx-dots"><i/><i/><i/></span>Checking VITRONX data…</div>}
            <div ref={endRef}/>
          </div>
          <form onSubmit={(e) => { e.preventDefault(); ask(); }} className="p-2 border-t border-[var(--vx-border)] flex gap-1.5">
            <button type="button" onClick={toggleMic} className={`p-2 rounded-lg ${listening ? "bg-red-500/20 text-red-300 animate-pulse" : "text-slate-300 hover:text-white bg-[var(--vx-card-hover)]"}`} title={SR ? "Speak" : "Voice not supported"} data-testid="buddy-mic-btn">{SR ? <Mic size={16}/> : <MicOff size={16}/>}</button>
            <input value={input} onChange={e => setInput(e.target.value)} placeholder={listening ? "Listening…" : "Type your question…"} className="vx-input flex-1 text-sm" data-testid="buddy-input" maxLength={1000}/>
            <button type="submit" disabled={loading || !input.trim()} className="vx-btn-primary px-3 disabled:opacity-50" data-testid="buddy-send-btn"><Send size={14}/></button>
          </form>
        </div>
      )}
      <button onClick={() => { setOpen(o => !o); setNotice(false); }} className="relative rounded-full bg-[var(--vx-card)] border border-[var(--vx-border-active)] p-1 shadow-xl hover:scale-105 transition-transform" title="VITRONX AI Buddy" data-testid="buddy-toggle-btn">
        <DogAvatar size={52} mood={mood}/>
        {notice && !open && <span className="absolute top-0 right-0 w-3 h-3 rounded-full bg-red-500 border-2 border-[var(--vx-canvas)]" data-testid="buddy-notice-dot"/>}
      </button>
    </div>
  );
}

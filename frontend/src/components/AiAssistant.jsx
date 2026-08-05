import { useEffect, useRef, useState } from "react";
import { ENDPOINTS, getJSON } from "../api";

const SUGGESTIONS = [
  "How do I generate a report?",
  "Open the cyber twin",
  "Create a TBM design with sensors",
  "Analyse the data",
  "Live status"
];

const WELCOME = "Hello! I'm TunnelArchitect-AI. Ask me how to use the software, create a 3D design, analyse the data, or generate a report.";

export default function AiAssistant({ onAction, onToast }) {
  const [messages, setMessages] = useState([{ role: "ai", text: WELCOME }]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, typing]);

  async function send(raw) {
    const text = (raw || input).trim();
    if (!text || typing) return;
    const history = messages
      .slice(1)
      .map((m) => ({ role: m.role === "ai" ? "assistant" : "user", text: m.text }));
    setMessages((p) => [...p, { role: "user", text }]);
    setInput("");
    setTyping(true);
    try {
      const res = await getJSON(ENDPOINTS.assistantChat, {
        method: "POST",
        body: JSON.stringify({ message: text, history })
      });
      setMessages((p) => [...p, { role: "ai", text: res.reply }]);
      (res.actions || []).forEach((a) => {
        if (typeof onAction === "function") onAction(a);
      });
    } catch (e) {
      setMessages((p) => [...p, { role: "ai", text: "ERROR: assistant API offline - " + e.message }]);
      if (onToast) onToast("ASSISTANT API OFFLINE", "err");
    } finally {
      setTyping(false);
    }
  }

  return (
    <div className="ai-layout">
      <div className="ai-header">
        <span className="ai-orb" />
        <span>TUNNELARCHITECT-AI - <b className="ai-model">BIG PICKLE</b></span>
      </div>
      <div className="ai-list" ref={listRef}>
        {messages.map((m, i) => (
          <div key={i} className={`ai-msg ${m.role}`}>
            <div className="ai-bubble">{m.text}</div>
          </div>
        ))}
        {typing && (
          <div className="ai-msg ai">
            <div className="ai-bubble ai-typing">THINKING<span>.</span><span>.</span><span>.</span></div>
          </div>
        )}
      </div>
      <div className="ai-chips">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="ai-chip" onClick={() => send(s)}>{s}</button>
        ))}
      </div>
      <div className="ai-input-row">
        <input
          className="ai-input"
          value={input}
          placeholder="Ask me anything about the platform..."
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="btn chunky btn-apply" onClick={() => send()} disabled={typing}>SEND</button>
      </div>
    </div>
  );
}

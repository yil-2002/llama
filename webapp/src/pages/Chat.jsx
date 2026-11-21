import { useEffect, useRef, useState } from "react";
import { api, haptic, speak } from "../api.js";
import Owly from "../components/Owly.jsx";

export default function Chat({ me, go, refresh, mode }) {
  const [chat, setChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(true);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState(null);
  const recorder = useRef(null);
  const listEnd = useRef(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // StrictMode ikki marta chaqirmasligi uchun
    started.current = true;
    api
      .startChat(mode)
      .then((r) => {
        setChat(r);
        setMessages([{ role: "assistant", text: r.reply }]);
        speak(r.reply, r.audio_b64);
      })
      .catch(handleError)
      .finally(() => setBusy(false));
  }, [mode]);

  useEffect(() => {
    listEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  function handleError(e) {
    if (e.status === 402) return go("premium");
    setError(e.message);
  }

  async function sendText(e) {
    e?.preventDefault();
    const t = text.trim();
    if (!t || busy) return;
    setText("");
    setMessages((m) => [...m, { role: "user", text: t }]);
    setBusy(true);
    try {
      const r = await api.send(chat.id, t);
      setMessages((m) => [...m, { role: "assistant", text: r.reply }]);
      speak(r.reply, r.audio_b64);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy(false);
    }
  }

  async function toggleRecord() {
    haptic("medium");
    if (recording) {
      recorder.current?.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks = [];
      rec.ondataavailable = (e) => chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        setBusy(true);
        try {
          const r = await api.sendVoice(chat.id, blob);
          setMessages((m) => [...m, { role: "user", text: r.transcript }, { role: "assistant", text: r.reply }]);
          speak(r.reply, r.audio_b64);
        } catch (err) {
          handleError(err);
        } finally {
          setBusy(false);
        }
      };
      rec.start();
      recorder.current = rec;
      setRecording(true);
    } catch {
      setError("Mikrofonga ruxsat berilmadi. Matn yozib gaplashing.");
    }
  }

  async function finish() {
    if (!messages.some((m) => m.role === "user")) return go("home");
    setBusy(true);
    try {
      const fb = await api.finish(chat.id);
      refresh();
      go("result", { feedback: fb });
    } catch (err) {
      handleError(err);
      setBusy(false);
    }
  }

  const mood = recording ? "listen" : busy ? "think" : "idle";

  return (
    <div className="page chat">
      <div className="chat-head">
        <Owly mood={mood} size={64} />
        <div>
          <b>{chat?.topic ? `Mavzu: ${chat.topic}` : "Owly"}</b>
          <span className="muted small">{mode === "free" ? "Erkin suhbat" : mode.replace("ielts_p", "IELTS Part ")}</span>
        </div>
        <button className="ghost small" onClick={finish} disabled={busy}>
          Yakunlash
        </button>
      </div>

      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`bubble bubble--${m.role}`}>
            {m.text}
            {m.role === "assistant" && (
              <button className="replay" onClick={() => speak(m.text)} aria-label="Qayta eshitish">
                🔊
              </button>
            )}
          </div>
        ))}
        {busy && <div className="bubble bubble--assistant typing">• • •</div>}
        {error && <div className="error">{error}</div>}
        <div ref={listEnd} />
      </div>

      <form className="composer" onSubmit={sendText}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Inglizcha yozing..."
          disabled={!chat || recording}
        />
        {text.trim() ? (
          <button className="send" disabled={busy}>
            ➤
          </button>
        ) : (
          <button type="button" className={`mic ${recording ? "mic--on" : ""}`} onClick={toggleRecord} disabled={!chat || busy}>
            {recording ? "■" : "🎙"}
          </button>
        )}
      </form>
    </div>
  );
}

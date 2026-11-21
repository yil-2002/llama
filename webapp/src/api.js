const BASE = import.meta.env.VITE_API_URL || "";
export const tg = window.Telegram?.WebApp;

async function request(path, { method = "GET", body, form } = {}) {
  const headers = { "X-Telegram-Init-Data": tg?.initData || "" };
  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(BASE + path, { method, headers, body: payload });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail || "Xatolik yuz berdi");
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  me: () => request("/api/me"),
  updateMe: (body) => request("/api/me", { method: "PATCH", body }),
  startTrial: () => request("/api/trial", { method: "POST" }),
  startChat: (mode, topic) => request("/api/chats", { method: "POST", body: { mode, topic } }),
  send: (id, text) => request(`/api/chats/${id}/messages`, { method: "POST", body: { text } }),
  sendVoice: (id, blob) => {
    const form = new FormData();
    form.append("audio", blob, "voice.webm");
    return request(`/api/chats/${id}/voice`, { method: "POST", form });
  },
  finish: (id) => request(`/api/chats/${id}/finish`, { method: "POST" }),
  history: () => request("/api/history"),
  plans: () => request("/api/payments/plans"),
  checkout: (provider, plan) => request("/api/payments/checkout", { method: "POST", body: { provider, plan } }),
  dashboard: (days = 7) => request(`/api/admin/dashboard?days=${days}`),
};

export function haptic(type = "light") {
  tg?.HapticFeedback?.impactOccurred?.(type);
}

export function speak(text, audioB64) {
  if (audioB64) {
    const audio = new Audio(`data:audio/ogg;base64,${audioB64}`);
    audio.play().catch(() => browserSpeak(text));
    return;
  }
  browserSpeak(text);
}

function browserSpeak(text) {
  if (!window.speechSynthesis) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  u.rate = 0.95;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

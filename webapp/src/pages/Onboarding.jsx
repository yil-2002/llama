import { useState } from "react";
import { api, haptic } from "../api.js";
import Owly from "../components/Owly.jsx";

const LEVELS = [
  ["A1", "Boshlang'ich", "Bir nechta so'z va ibora bilaman"],
  ["A2", "Elementar", "Oddiy gaplar tuza olaman"],
  ["B1", "O'rta", "Kundalik mavzularda gaplasha olaman"],
  ["B2", "O'rtadan yuqori", "Erkin, lekin xatolar bilan"],
  ["C1", "Yuqori", "Deyarli erkin gaplashaman"],
];

export default function Onboarding({ onDone }) {
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState(null);
  const [saving, setSaving] = useState(false);

  async function pickLevel(level) {
    haptic();
    setSaving(true);
    try {
      onDone(await api.updateMe({ goal, level }));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <Owly mood={step === 0 ? "hello" : "think"} size={120} />
      {step === 0 ? (
        <>
          <h1>Salom! Men Owly 🦉</h1>
          <p className="muted">Maqsadingiz nima?</p>
          <div className="stack">
            <button className="option" onClick={() => (setGoal("ielts"), setStep(1), haptic())}>
              <b>🎯 IELTS Speaking</b>
              <span>Band ballni oshirish</span>
            </button>
            <button className="option" onClick={() => (setGoal("speaking"), setStep(1), haptic())}>
              <b>💬 Erkin gaplashish</b>
              <span>Ishonch bilan ingliz tilida so'zlash</span>
            </button>
          </div>
        </>
      ) : (
        <>
          <h1>Darajangiz qanday?</h1>
          <p className="muted">Keyin o'zgartirish mumkin. Owly sizga moslashadi.</p>
          <div className="stack">
            {LEVELS.map(([code, title, desc]) => (
              <button key={code} className="option" disabled={saving} onClick={() => pickLevel(code)}>
                <b>
                  {code} · {title}
                </b>
                <span>{desc}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

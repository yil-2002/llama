import { useEffect, useState } from "react";
import { api, haptic, tg } from "../api.js";
import Owly from "../components/Owly.jsx";

const FEATURES = [
  "Cheksiz AI suhbat (matn va ovoz)",
  "IELTS Speaking Part 1, 2, 3 mock",
  "Har suhbatdan keyin batafsil o'zbekcha feedback",
  "Progress va band ball tarixi",
];

export default function Premium({ me, go, refresh }) {
  const [plans, setPlans] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    api.plans().then(setPlans).catch(() => {});
  }, []);

  async function buy(plan) {
    haptic("medium");
    setBusy(true);
    try {
      const { url } = await api.checkout(plan.provider, plan.code);
      // Mini App ichida faqat Telegram Stars (Telegram qoidasi)
      tg.openInvoice(url, (status) => {
        if (status === "paid") {
          setMsg("🎉 Rahmat! Premium faollashdi.");
          setTimeout(refresh, 1500);
        } else if (status === "failed") setMsg("To'lov amalga oshmadi.");
        setBusy(false);
      });
    } catch (e) {
      setMsg(e.message);
      setBusy(false);
    }
  }

  async function trial() {
    setBusy(true);
    try {
      await api.startTrial();
      await refresh();
      go("home");
    } catch (e) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <Owly mood="praise" size={120} />
      <h1>Owly Premium</h1>
      {me.is_premium && (
        <p className="pill pill--gold">Faol: {new Date(me.premium_until).toLocaleDateString("uz-UZ")} gacha</p>
      )}
      <ul className="list checks">
        {FEATURES.map((f) => (
          <li key={f}>{f}</li>
        ))}
      </ul>

      {plans.map((p) => (
        <button key={p.provider + p.code} className="cta" disabled={busy} onClick={() => buy(p)}>
          ⭐ {p.price} Stars / {p.days} kun
        </button>
      ))}
      {!me.is_premium && me.trial_available && (
        <button className="ghost" disabled={busy} onClick={trial}>
          3 kun bepul sinab ko'rish
        </button>
      )}
      <p className="muted small">Obuna har 30 kunda avtomatik yangilanadi. Telegram sozlamalarida bekor qilish mumkin.</p>
      {msg && <p className="notice">{msg}</p>}
    </div>
  );
}

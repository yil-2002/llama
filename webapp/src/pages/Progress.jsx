import { useEffect, useState } from "react";
import { api } from "../api.js";
import Owly from "../components/Owly.jsx";

export default function Progress({ me }) {
  const [items, setItems] = useState(null);
  useEffect(() => {
    api.history().then(setItems).catch(() => setItems([]));
  }, []);

  const bands = (items || []).filter((i) => i.overall_band != null).reverse();
  return (
    <div className="page">
      <Owly mood="idle" size={90} />
      <h1>Progress</h1>
      <div className="row stats">
        <div>
          <b>{me.streak_days}</b>
          <span>kun ketma-ket</span>
        </div>
        <div>
          <b>{items?.length ?? "…"}</b>
          <span>baholangan suhbat</span>
        </div>
        <div>
          <b>{me.level}</b>
          <span>daraja</span>
        </div>
      </div>

      {bands.length > 1 && (
        <>
          <h2>Band ball dinamikasi</h2>
          <div className="spark">
            {bands.map((b) => (
              <i key={b.session_id} style={{ height: `${(b.overall_band / 9) * 100}%` }} title={`${b.date}: ${b.overall_band}`} />
            ))}
          </div>
        </>
      )}

      <h2>Oxirgi suhbatlar</h2>
      {items?.length === 0 && <p className="muted">Hali suhbat yo'q. Birinchisini boshlang!</p>}
      <div className="stack">
        {items?.map((i) => (
          <div key={i.session_id} className="history-row">
            <span>
              <b>{i.topic}</b>
              <small className="muted">
                {i.date} · {i.mode === "free" ? "Erkin" : i.mode.replace("ielts_p", "Part ")}
              </small>
            </span>
            <b className="band-chip">{i.overall_band ?? "—"}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

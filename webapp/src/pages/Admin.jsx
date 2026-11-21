import { useEffect, useState } from "react";
import { api } from "../api.js";

const RANGES = [1, 7, 30];

export default function Admin() {
  const [days, setDays] = useState(7);
  const [d, setD] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setD(null);
    api.dashboard(days).then(setD).catch((e) => setError(e.message));
  }, [days]);

  if (error) return <div className="page"><p className="error">{error}</p></div>;

  const maxHour = d ? Math.max(1, ...d.by_hour) : 1;
  const maxLevel = d ? Math.max(1, ...d.levels.map((l) => l.messages)) : 1;

  return (
    <div className="page admin">
      <h1>📊 Dashboard</h1>
      <div className="segmented">
        {RANGES.map((r) => (
          <button key={r} className={r === days ? "on" : ""} onClick={() => setDays(r)}>
            {r === 1 ? "Bugun" : `${r} kun`}
          </button>
        ))}
      </div>

      {!d ? (
        <p className="muted">Yuklanmoqda…</p>
      ) : (
        <>
          <div className="kpis">
            <Kpi label="Jami foydalanuvchi" value={d.totals.users} />
            <Kpi label="Faol" value={d.totals.active} />
            <Kpi label="Yangi" value={d.totals.new} />
            <Kpi label="Premium" value={d.totals.premium} />
            <Kpi label="Tushum, Stars" value={d.totals.stars_revenue} />
          </div>

          <h2>Soat bo'yicha faollik</h2>
          <p className="muted small">
            Toshkent vaqti, xabarlar soni
            {d.peak_hour != null && ` · eng faol: ${String(d.peak_hour).padStart(2, "0")}:00`}
          </p>
          <div className="hours">
            {d.by_hour.map((v, h) => (
              <div key={h} className="hour" title={`${h}:00 — ${v}`}>
                <i style={{ height: `${(v / maxHour) * 100}%` }} className={h === d.peak_hour ? "peak" : ""} />
                {h % 6 === 0 && <span>{h}</span>}
              </div>
            ))}
          </div>

          <h2>Daraja bo'yicha</h2>
          <div className="levels">
            {d.levels
              .filter((l) => l.users || l.messages)
              .map((l) => (
                <div key={l.level} className="level-row">
                  <b>{l.level === "unknown" ? "?" : l.level}</b>
                  <div className="bar">
                    <i style={{ width: `${(l.messages / maxLevel) * 100}%` }} />
                  </div>
                  <span className="small">
                    {l.users} foyd. · {l.messages} xabar
                  </span>
                </div>
              ))}
          </div>
        </>
      )}
    </div>
  );
}

function Kpi({ label, value }) {
  return (
    <div className="kpi">
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

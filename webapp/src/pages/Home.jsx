import { haptic } from "../api.js";
import Owly from "../components/Owly.jsx";

const IELTS = [
  ["ielts_p1", "Part 1", "Tanish mavzular"],
  ["ielts_p2", "Part 2", "Cue card, 2 daqiqa"],
  ["ielts_p3", "Part 3", "Muhokama"],
];

export default function Home({ me, go }) {
  const start = (mode) => {
    haptic("medium");
    if (mode !== "free" && !me.is_premium) return go("premium");
    go("chat", { mode });
  };

  return (
    <div className="page">
      <header className="topbar">
        <span className="pill">🔥 {me.streak_days} kun</span>
        <span className="pill">{me.level}</span>
        {me.is_premium ? (
          <span className="pill pill--gold">⭐ Premium</span>
        ) : (
          <button className="pill pill--link" onClick={() => go("premium")}>
            ⭐ Premium
          </button>
        )}
      </header>

      <Owly mood="hello" size={150} />
      <h1>Salom, {me.first_name || "do'stim"}!</h1>
      <p className="muted">
        {me.is_premium
          ? "Bugun nima haqida gaplashamiz?"
          : `Bugun ${me.remaining_free_messages} ta bepul xabar qoldi`}
      </p>

      <button className="cta" onClick={() => start("free")}>
        🎙 Gaplashish
      </button>

      <h2>IELTS Speaking mock</h2>
      <div className="grid3">
        {IELTS.map(([mode, title, desc]) => (
          <button key={mode} className="card" onClick={() => start(mode)}>
            <b>{title}</b>
            <span>{desc}</span>
            {!me.is_premium && <i className="lock">🔒</i>}
          </button>
        ))}
      </div>

      <div className="row">
        <button className="ghost" onClick={() => go("progress")}>
          📈 Progress
        </button>
        {me.is_admin && (
          <button className="ghost" onClick={() => go("admin")}>
            📊 Dashboard
          </button>
        )}
      </div>
    </div>
  );
}

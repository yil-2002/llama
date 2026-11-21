import Owly from "../components/Owly.jsx";

const CRITERIA = [
  ["fluency", "Ravonlik"],
  ["lexical", "Lug'at"],
  ["grammar", "Grammatika"],
  ["pronunciation", "Talaffuz"],
];

export default function Result({ feedback: fb, go }) {
  if (!fb) return null;
  const band = fb.overall_band ?? "—";
  return (
    <div className="page">
      <Owly mood={band >= 6 ? "praise" : "hello"} size={110} />
      <div className="band">
        <span>Umumiy band</span>
        <b>{band}</b>
      </div>

      <div className="scores">
        {CRITERIA.map(([k, title]) => (
          <div key={k} className="score">
            <span>{title}</span>
            <div className="bar">
              <i style={{ width: `${((fb.scores?.[k] ?? 0) / 9) * 100}%` }} />
            </div>
            <b>{fb.scores?.[k] ?? "—"}</b>
          </div>
        ))}
      </div>

      {fb.summary_uz && <p className="card-text">{fb.summary_uz}</p>}

      {fb.strengths_uz?.length > 0 && (
        <>
          <h2>💪 Kuchli tomonlar</h2>
          <ul className="list">{fb.strengths_uz.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </>
      )}

      {fb.mistakes?.length > 0 && (
        <>
          <h2>✍️ Xatolar ustida ishlash</h2>
          {fb.mistakes.map((m, i) => (
            <div key={i} className="mistake">
              <p className="wrong">{m.original}</p>
              <p className="right">{m.better}</p>
              <p className="muted small">{m.explanation_uz}</p>
            </div>
          ))}
        </>
      )}

      {fb.better_answer && (
        <>
          <h2>⭐ Namunaviy javob</h2>
          <p className="card-text">{fb.better_answer}</p>
        </>
      )}

      {fb.next_steps_uz?.length > 0 && (
        <>
          <h2>➡️ Keyingi qadam</h2>
          <ul className="list">{fb.next_steps_uz.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </>
      )}

      <button className="cta" onClick={() => go("home")}>
        Bosh sahifa
      </button>
    </div>
  );
}

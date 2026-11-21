import { useCallback, useEffect, useState } from "react";
import { api, tg } from "./api.js";
import Owly from "./components/Owly.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Home from "./pages/Home.jsx";
import Chat from "./pages/Chat.jsx";
import Result from "./pages/Result.jsx";
import Premium from "./pages/Premium.jsx";
import Progress from "./pages/Progress.jsx";
import Admin from "./pages/Admin.jsx";

export default function App() {
  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);
  const [screen, setScreen] = useState({ name: "home" });

  const refresh = useCallback(() => api.me().then(setMe).catch((e) => setError(e.message)), []);

  useEffect(() => {
    tg?.ready();
    tg?.expand();
    refresh();
  }, [refresh]);

  const go = useCallback((name, params = {}) => setScreen({ name, ...params }), []);

  // Telegram "orqaga" tugmasi
  useEffect(() => {
    const back = tg?.BackButton;
    if (!back) return;
    const handler = () => go("home");
    if (screen.name === "home") back.hide();
    else {
      back.show();
      back.onClick(handler);
    }
    return () => back.offClick(handler);
  }, [screen.name, go]);

  if (error)
    return (
      <div className="center">
        <Owly mood="sad" />
        <p>{error}</p>
        <p className="muted">Ilovani Telegram ichidan oching.</p>
      </div>
    );
  if (!me)
    return (
      <div className="center">
        <Owly mood="think" />
      </div>
    );
  if (!me.level || !me.goal) return <Onboarding onDone={setMe} />;

  const props = { me, go, refresh };
  switch (screen.name) {
    case "chat":
      return <Chat {...props} mode={screen.mode} />;
    case "result":
      return <Result {...props} feedback={screen.feedback} />;
    case "premium":
      return <Premium {...props} />;
    case "progress":
      return <Progress {...props} />;
    case "admin":
      return <Admin {...props} />;
    default:
      return <Home {...props} />;
  }
}

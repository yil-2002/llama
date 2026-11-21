// Owly — loyihaning o'z maskoti (SVG + CSS animatsiya).
// Holatlar: idle | hello | listen | think | praise | sad
// Keyinroq Lottie/TGS stikerlari bilan almashtirish mumkin — props bir xil qoladi.
export default function Owly({ mood = "idle", size = 140 }) {
  const eyeY = mood === "sad" ? 62 : 58;
  return (
    <div className={`owly owly--${mood}`} style={{ width: size, height: size }} aria-label="Owly">
      <svg viewBox="0 0 120 120" width={size} height={size}>
        <ellipse cx="60" cy="112" rx="30" ry="5" className="owly-shadow" />
        <g className="owly-body">
          {/* quloqlar */}
          <path d="M30 30 L38 12 L48 28 Z" className="owly-dark" />
          <path d="M90 30 L82 12 L72 28 Z" className="owly-dark" />
          {/* tana */}
          <ellipse cx="60" cy="66" rx="40" ry="42" className="owly-main" />
          <ellipse cx="60" cy="80" rx="24" ry="24" className="owly-belly" />
          {/* qanotlar */}
          <path d="M22 62 Q10 82 26 96 Q30 80 30 66 Z" className="owly-dark owly-wing-l" />
          <path d="M98 62 Q110 82 94 96 Q90 80 90 66 Z" className="owly-dark owly-wing-r" />
          {/* ko'zoynak */}
          <circle cx="44" cy={eyeY} r="15" className="owly-eye-bg" />
          <circle cx="76" cy={eyeY} r="15" className="owly-eye-bg" />
          <circle cx="44" cy={eyeY} r="15" className="owly-glasses" />
          <circle cx="76" cy={eyeY} r="15" className="owly-glasses" />
          <line x1="59" y1={eyeY} x2="61" y2={eyeY} className="owly-glasses" />
          <g className="owly-pupils">
            {mood === "praise" ? (
              <>
                <path d={`M37 ${eyeY + 2} Q44 ${eyeY - 6} 51 ${eyeY + 2}`} className="owly-smile-eye" />
                <path d={`M69 ${eyeY + 2} Q76 ${eyeY - 6} 83 ${eyeY + 2}`} className="owly-smile-eye" />
              </>
            ) : (
              <>
                <circle cx="44" cy={eyeY + (mood === "think" ? -4 : 0)} r="6" className="owly-pupil" />
                <circle cx="76" cy={eyeY + (mood === "think" ? -4 : 0)} r="6" className="owly-pupil" />
                <circle cx="46" cy={eyeY - 2} r="2" fill="#fff" />
                <circle cx="78" cy={eyeY - 2} r="2" fill="#fff" />
              </>
            )}
          </g>
          {/* tumshuq */}
          <path d="M55 72 L65 72 L60 80 Z" className="owly-beak" />
          {mood === "sad" && <path d="M50 92 Q60 86 70 92" className="owly-mouth" />}
        </g>
        {mood === "listen" && (
          <g className="owly-waves">
            <path d="M104 50 Q112 60 104 70" />
            <path d="M110 44 Q122 60 110 76" />
          </g>
        )}
        {mood === "think" && (
          <g className="owly-dots">
            <circle cx="96" cy="22" r="3" />
            <circle cx="104" cy="14" r="4" />
            <circle cx="113" cy="6" r="5" />
          </g>
        )}
      </svg>
    </div>
  );
}

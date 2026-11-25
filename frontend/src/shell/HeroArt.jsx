// The home page illustration: an OncoSphere window with a CT slice (a lesion measured in orange) next to a
// treatment plan, with three example cards floating around it. Drawn here (not an image file) so it follows
// the light/dark theme. Decorative only: none of it is real data.
import { Icon } from "../shared/Icon.jsx";

const FLOATING = [
  { cls: "f1", icon: "calendar", title: "Next visit", text: "Tuesday · 10:30 · Oncology clinic" },
  { cls: "f2", icon: "activity", title: "Chemotherapy", text: "Cycle 3 of 6", progress: 50 },
  { cls: "f3", icon: "checkCircle", title: "Scan reviewed", text: "CT chest · report signed" },
];

export function HeroArt() {
  return (
    <div className="lp-art" aria-hidden="true">
      <svg className="lp-art-svg" viewBox="0 0 560 420">
        {/* soft rings behind the window, echoing the logo's sphere */}
        <circle cx="300" cy="210" r="205" className="ha-ring1" />
        <circle cx="300" cy="210" r="150" className="ha-ring2" />

        {/* app window */}
        <rect x="24" y="44" width="512" height="320" rx="22" className="ha-window" />
        <rect x="24" y="44" width="512" height="46" rx="22" className="ha-bar" />
        <rect x="24" y="70" width="512" height="20" className="ha-bar" />
        <circle cx="52" cy="67" r="6" className="ha-dot1" />
        <circle cx="72" cy="67" r="6" className="ha-dot2" />
        <circle cx="92" cy="67" r="6" className="ha-dot3" />
        <rect x="200" y="60" width="160" height="14" rx="7" className="ha-line" />

        {/* CT viewer panel (always dark, like a real viewer) */}
        <rect x="44" y="108" width="232" height="236" rx="14" className="ha-viewer" />
        <g transform="translate(160 226)">
          <ellipse rx="92" ry="70" className="ha-body" />
          <ellipse rx="80" ry="58" className="ha-fat" />
          {/* lungs */}
          <path d="M-12 -44c-30 -6 -58 10 -60 40s14 52 40 50c18 -2 24 -20 22 -44z" className="ha-lung" />
          <path d="M12 -44c30 -6 58 10 60 40s-14 52 -40 50c-18 -2 -24 -20 -22 -44z" className="ha-lung" />
          {/* heart, spine, sternum */}
          <ellipse cx="10" cy="4" rx="22" ry="18" className="ha-tissue" />
          <circle cx="0" cy="46" r="11" className="ha-bone" />
          <rect x="-5" y="-58" width="10" height="10" rx="3" className="ha-bone" />
          {/* lesion, ringed and measured */}
          <circle cx="-42" cy="-8" r="9" className="ha-lesion" />
          <circle cx="-42" cy="-8" r="17" className="ha-lesion-ring" />
          <path d="M-62 -30 -22 14" className="ha-measure" />
        </g>
        <rect x="58" y="120" width="54" height="18" rx="9" className="ha-chip" />
        <text x="85" y="133" className="ha-chip-text" textAnchor="middle">AXIAL</text>
        <rect x="190" y="318" width="72" height="18" rx="9" className="ha-chip-accent" />
        <text x="226" y="331" className="ha-chip-text" textAnchor="middle">18.4 mm</text>

        {/* treatment plan panel */}
        <rect x="296" y="108" width="220" height="18" rx="9" className="ha-title" />
        {[0, 1, 2].map((i) => (
          <g key={i} transform={`translate(296 ${146 + i * 44})`}>
            <rect width="220" height="34" rx="10" className="ha-row" />
            <circle cx="18" cy="17" r="9" className={i < 2 ? "ha-done" : "ha-todo"} />
            {i < 2 && <path d="M13.5 17l3 3 5.5-6" className="ha-tick" />}
            <rect x="36" y="10" width={[110, 90, 120][i]} height="7" rx="3.5" className="ha-line" />
            <rect x="36" y="21" width={[70, 80, 56][i]} height="5" rx="2.5" className="ha-line-soft" />
          </g>
        ))}
        {/* tumour size trend: going down */}
        <rect x="296" y="282" width="220" height="62" rx="12" className="ha-row" />
        {[42, 36, 30, 22, 16].map((h, i) => (
          <rect key={i} x={316 + i * 22} y={334 - h} width="12" height={h} rx="4" className={i === 4 ? "ha-bar-accent" : "ha-bar-fill"} />
        ))}
        <path d="M434 300c16 4 28 14 40 26" className="ha-trend" />
        <path d="M466 326l8 0 0-8" className="ha-trend" />
      </svg>

      {FLOATING.map((c) => (
        <div key={c.cls} className={`lp-float ${c.cls}`}>
          <span className="lp-float-icon"><Icon name={c.icon} /></span>
          <span className="lp-float-text">
            <b>{c.title}</b>
            <small>{c.text}</small>
            {c.progress != null && <span className="lp-progress"><span style={{ width: `${c.progress}%` }} /></span>}
          </span>
        </div>
      ))}
    </div>
  );
}

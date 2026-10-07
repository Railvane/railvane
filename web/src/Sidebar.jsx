// Views arrive per phase; until then they are shown but disabled
const NAV = [
  { label: "Workspace", ready: true },
  { label: "Library", soon: "v0.1" },
  { label: "Timeline", soon: "v0.2" },
  { label: "Quality", soon: "v0.3" },
  { label: "Packs", soon: "v0.4" },
];

export default function Sidebar({ version }) {
  return (
    <aside className="sidebar">
      <div className="logo">
        <img src="/railvane-logo.svg" alt="" />
        <div>Railvane<small>the guardrails manager for AI coding agents</small></div>
      </div>
      <nav>
        {NAV.map(n => (
          <a key={n.label} className={n.ready ? "active" : "disabled"}>
            {n.label}
            {n.soon && <span className="soon">{n.soon}</span>}
          </a>
        ))}
      </nav>
      <div className="sidebar-foot">
        {version && <span>v{version}</span>}
        <span>No database — git is the store</span>
      </div>
    </aside>
  );
}

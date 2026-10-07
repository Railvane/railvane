const NAV = [
  { id: "library", label: "▦ Library" },
  { id: "import", label: "⇪ Import" },
  { id: "timeline", label: "⟳ Timeline" },
  { id: "quality", label: "✦ Quality" },
  { id: "packs", label: "📦 Packs" },
  { id: "workspace", label: "⚙ Workspace" },
];

export default function Sidebar({ view, onNavigate, counts, version, workspace, onRefresh, busy }) {
  const count = id => {
    if (id === "library") return counts.library;
    if (id === "import") return counts.import || null;
    if (id === "quality") return counts.quality || null;
    return null;
  };
  return (
    <aside className="sidebar">
      <div className="logo">
        <img src="/railvane-logo.svg" alt="" />
        <div>Railvane<small>the guardrails manager for AI coding agents</small></div>
      </div>
      <nav>
        {NAV.map(n => (
          <a key={n.id} className={view === n.id ? "active" : ""} onClick={() => onNavigate(n.id)}>
            {n.label}
            {count(n.id) != null && <span className={`count ${n.id === "quality" ? counts.qualityKind : n.id === "import" ? "info" : ""}`}>{count(n.id)}</span>}
          </a>
        ))}
      </nav>
      <div className="sidebar-foot">
        {workspace && <b className="ws-name">{workspace}</b>}
        <button className="btn ghost small-btn" disabled={busy} onClick={onRefresh}>{busy ? "Fetching…" : "⟳ Fetch & rescan"}</button>
        {version && <span>v{version}</span>}
        <span>No database — git is the store</span>
      </div>
    </aside>
  );
}

import { RepoLine } from "./components/RepoBadge.jsx";

const NAV = [
  { id: "library", label: "▦ Library" },
  { id: "classify", label: "◈ Classify" },
  { id: "timeline", label: "⟳ Timeline" },
  { id: "quality", label: "✦ Quality" },
  { id: "packs", label: "📦 Packs" },
  { id: "repos", label: "⎇ Repositories" },
  { id: "admin", label: "⚙ Admin" },
];

export default function Sidebar({ view, onNavigate, counts, version, library, onRefresh, busy }) {
  const count = id => {
    if (id === "library") return counts.library;
    if (id === "classify") return counts.classify || null;
    if (id === "quality") return counts.quality || null;
    return null;
  };
  return (
    <aside className="sidebar">
      <div className="logo">
        <img src="/railvane-logo.svg" alt="" />
        <div>Railvane<small>the guardrails manager for AI coding agents</small></div>
      </div>
      {library && (
        <div className="ws-box" onClick={() => onNavigate("repos")} title="Workspace repository — click for all repositories">
          <div className="ws-label">Workspace</div>
          <div className="ws-name">{library.workspace}</div>
          <RepoLine repo={library.workspace_repo} path={library.workspace_root} />
          {library.server
            ? <div className="ws-sync" title="Server mode: pulled every minute, every change is pushed">⇅ synced · auto-push</div>
            : <div className="mono ws-path">{library.workspace_repo?.display_root ?? library.workspace_root}</div>}
          {library.server?.sync_error && <div className="badge b-err" title={library.server.sync_error}>sync problem</div>}
        </div>
      )}
      <nav>
        {NAV.map(n => (
          <a key={n.id} className={view === n.id ? "active" : ""} onClick={() => onNavigate(n.id)}>
            {n.label}
            {count(n.id) != null && <span className={`count ${n.id === "quality" ? counts.qualityKind : n.id === "classify" ? "info" : ""}`}>{count(n.id)}</span>}
          </a>
        ))}
      </nav>
      <div className="sidebar-foot">
        <button className="btn ghost small-btn" disabled={busy} onClick={onRefresh}>{busy ? "Fetching…" : "⟳ Fetch & rescan"}</button>
        {version && <span>v{version}</span>}
        <span>No database — git is the store</span>
      </div>
    </aside>
  );
}

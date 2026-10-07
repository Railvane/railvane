import { Badge } from "../components/Badges.jsx";
import { RepoCard } from "../components/RepoBadge.jsx";

export default function Repositories({ library, workspace, schema, onNavigate }) {
  const { config, config_found, errors } = workspace;
  const fm = schema.frontmatter;
  return (
    <section>
      <h1>Repositories</h1>
      <p className="sub">Where your guardrails live. Railvane has no database: everything is read from and written to these git repositories.</p>

      <h3>Workspace repository</h3>
      <RepoCard title={`${library.workspace} — your guardrails workspace`} repo={library.workspace_repo} path={library.workspace_root} />
      <div className="explain">
        This repository holds <code>railvane.yaml</code> (settings, sources, packs), <code>.railvane/manifest.yaml</code> (confirmed
        metadata) and <code>.railvane/overrides/</code> (your changes to pack rules). Confirming metadata, installing or updating
        packs and saving overrides are commits <b>here</b>. It can also contain guardrails of its own, like a <code>guardrails/</code> folder.
      </div>
      {!config_found && <div className="notice">No <code>railvane.yaml</code> yet — using defaults.</div>}
      {errors.length > 0 && <div className="alert"><b>railvane.yaml has errors</b><ul>{errors.map(e => <li key={e}>{e}</li>)}</ul></div>}

      <h3>Sources — where guardrail files are read from</h3>
      {library.sources.map(s => (
        <RepoCard key={s.id} title={s.id} repo={s.repo} path={s.display_root ?? s.location}>
          <div className="repo-tags">
            <Badge kind="info">{s.kind === "git" ? "git clone" : "folder"}</Badge>
            {s.readonly ? <Badge kind="muted" title="Railvane never writes here">🔒 read-only</Badge>
              : <Badge kind="ok" title="Edits are committed in this repository">✎ editable</Badge>}
            {s.error ? <Badge kind="err" title={s.error}>error</Badge> : <span className="muted small">{s.files} files</span>}
          </div>
        </RepoCard>
      ))}
      <button className="btn" onClick={() => onNavigate("import")}>+ Add a source in Import</button>

      <h3>Packs installed in this workspace</h3>
      {config.packs.length === 0 ? <p className="muted small">None.</p> : config.packs.map(p => (
        <div key={p.source + (p.path ?? "")} className="row"><span className="pill">pack</span>
          <span className="mono small">{p.source}{p.path ? `#${p.path}` : ""}</span>
          <span className="muted small">v{p.version ?? "—"} · <span className="mono">{p.sha?.slice(0, 7)}</span></span></div>
      ))}

      <div className="grid">
        <div className="card">
          <h2>Which files count as guardrails</h2>
          <div className="tags">{config.include.map(p => <code key={p}>{p}</code>)}</div>
          <p className="muted small">A source can override this with its own <code>include</code>.</p>
        </div>
        <div className="card">
          <h2>Frontmatter schema v{fm.version}</h2>
          <div className="row"><span className="label">Required</span>{fm.required.map(f => <code key={f}>{f}</code>)}</div>
          <div className="row"><span className="label">Optional</span>{fm.optional.map(f => <code key={f}>{f}</code>)}</div>
          <div className="row"><span className="label">Defaults</span>
            <span className="muted">visibility {config.defaults.visibility}{config.defaults.owner && ` · owner ${config.defaults.owner}`}</span></div>
        </div>
      </div>
    </section>
  );
}

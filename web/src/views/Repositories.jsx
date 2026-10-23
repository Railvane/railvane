import { Badge } from "../components/Badges.jsx";
import { postJson } from "../api.js";
import AddSource from "../components/AddSource.jsx";
import CopiesPanel from "../components/CopiesPanel.jsx";
import { RepoCard } from "../components/RepoBadge.jsx";
import { useDialog } from "../components/Dialog.jsx";

export default function Repositories({ library, workspace, schema, onChanged }) {
  const { config, config_found, errors } = workspace;
  const fm = schema.frontmatter;
  const dialog = useDialog();
  const toggle = async s => {
    const ok = await dialog.confirm(s.readonly
      ? { title: `Make ${s.id} editable?`, message: "Railvane may then commit in this repository.", confirmLabel: "Make editable", danger: true }
      : { title: `Make ${s.id} read-only?`, message: "Railvane will no longer write to this repository.", confirmLabel: "Make read-only" });
    if (!ok) return;
    try { await postJson("/api/sources/readonly", { id: s.id, readonly: !s.readonly }); onChanged(); }
    catch (e) { await dialog.tell({ title: "Could not change the repository", message: e.message }); }
  };
  return (
    <section>
      <h1>Repositories</h1>
      <p className="sub">Where your guardrails live. Railvane has no database: everything is read from and written to these git repositories.</p>

      <h3>Workspace repository</h3>
      <RepoCard title={`${library.workspace} — your guardrails workspace`} repo={library.workspace_repo} path={library.workspace_root}>
        {library.server && <Badge kind="info" title="Pulled every minute and on Fetch; every change is pushed">⇅ server mode · auto-push</Badge>}
      </RepoCard>
      {library.server?.sync_error && <div className="alert">{library.server.sync_error}</div>}
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
            <button className={`btn small-btn ${s.readonly ? "" : "ok-btn"}`} onClick={() => toggle(s)}
              title={s.readonly ? "Railvane never writes here — click to make editable" : "Edits are committed here — click to make read-only"}>
              {s.readonly ? "🔒 read-only" : "✎ editable"}</button>
            {!s.available ? <Badge kind="muted" title={s.error}>not available here</Badge>
              : s.error ? <Badge kind="err" title={s.error}>error</Badge> : <span className="muted small">{s.files} files</span>}
          </div>
        </RepoCard>
      ))}
      <AddSource onAdded={onChanged} />
      <CopiesPanel onChanged={onChanged} />

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

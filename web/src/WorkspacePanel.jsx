export default function WorkspacePanel({ workspace, schema }) {
  const { config, root, config_found, errors } = workspace;
  const fm = schema.frontmatter;

  return (
    <>
      <h1>{config.name}</h1>
      <p className="muted mono">{root}</p>

      {!config_found && (
        <div className="notice">No <code>railvane.yaml</code> found — using defaults. Add one to configure sources.</div>
      )}
      {errors.length > 0 && (
        <div className="alert">
          <b>railvane.yaml has errors</b>
          <ul>{errors.map(e => <li key={e}>{e}</li>)}</ul>
        </div>
      )}

      <div className="grid">
        <section className="card">
          <h2>Sources</h2>
          {config.sources.map((s, i) => (
            <div key={i} className="row">
              <span className="pill">{s.git ? "git" : "folder"}</span>
              <span className="mono">{s.git || s.path}</span>
              {s.branch && <span className="muted">@{s.branch}</span>}
            </div>
          ))}
          <h3>Included files</h3>
          <div className="tags">{config.include.map(p => <code key={p}>{p}</code>)}</div>
        </section>

        <section className="card">
          <h2>Frontmatter schema v{fm.version}</h2>
          <div className="row"><span className="label">Required</span>{fm.required.map(f => <code key={f}>{f}</code>)}</div>
          <div className="row"><span className="label">Optional</span>{fm.optional.map(f => <code key={f}>{f}</code>)}</div>
          <div className="row"><span className="label">Types</span><span className="muted">{fm.types.join(" · ")}</span></div>
          <div className="row"><span className="label">Defaults</span>
            <span className="muted">visibility {config.defaults.visibility}{config.defaults.owner && ` · owner ${config.defaults.owner}`}</span>
          </div>
        </section>
      </div>

      <section className="card">
        <h2>Lifecycle areas</h2>
        <div className="phases">
          {Object.entries(schema.phases).map(([id, p]) => (
            <div key={id} className="phase">
              <b>{p.name}</b>
              {Object.entries(p.areas).map(([a, name]) => <div key={a} className="area"><code>{a}</code> {name}</div>)}
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

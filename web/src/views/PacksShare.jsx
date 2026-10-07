import { useEffect, useState } from "react";
import { getJson, postJson } from "../api.js";
import { Badge } from "../components/Badges.jsx";
import { fmtTokens } from "../meta.js";

export function PacksDiscover({ onChanged }) {
  const [packs, setPacks] = useState(null);
  const [source, setSource] = useState("");
  const [msg, setMsg] = useState(null);
  const load = () => getJson("/api/packs/discover").then(r => setPacks(r.packs)).catch(e => setMsg(e.message));
  useEffect(() => { load(); }, []);
  const install = async (src, path = null) => {
    setMsg(null);
    try {
      const r = await postJson("/api/packs/install", { source: src, path });
      setMsg(`Installed ${r.name} ${r.version ? "v" + r.version : ""}.`); load(); onChanged();
    } catch (e) { setMsg(e.message); }
  };
  return (
    <>
      <div className="add-source">
        <input value={source} onChange={e => setSource(e.target.value)} placeholder="Install from a git URL or folder (relative to the workspace)" />
        <button className="btn primary" disabled={!source.trim()} onClick={() => install(source.trim())}>Install…</button>
      </div>
      {msg && <div className="notice">{msg}</div>}
      {packs && !packs.length && <p className="muted">Your catalog is empty. Add pack sources to <code>catalog:</code> in railvane.yaml to list them here.</p>}
      <div className="pk-disc">
        {packs?.map(p => p.error ? (
          <div key={p.source} className="pk-card"><b>{p.source}</b><div className="pk-warn">⚠ {p.error}</div></div>
        ) : (
          <div key={p.source + (p.path ?? "")} className="pk-card">
            <div className="pk-top"><span className="pk-ico">📦</span>
              <div className="grow"><b>{p.name}</b><div className="muted small">{p.description}</div></div>
              {p.version && <span className="pk-ver">v{p.version}</span>}</div>
            <div className="pk-meta"><span>{p.rules} rules</span><span>~{fmtTokens(p.tokens)} tokens</span>{p.license && <span>{p.license}</span>}</div>
            {p.tokens > 1500 && <div className="pk-warn">⚠ Large pack — consider whether you need all of it</div>}
            <div className="pk-actions">
              {p.installed ? <Badge kind="ok">✓ installed</Badge> : <button className="btn primary" onClick={() => install(p.source, p.path)}>Install</button>}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function MinePack({ p, onChanged }) {
  const [version, setVersion] = useState(p.suggested ?? "");
  const [msg, setMsg] = useState(null);
  const blocking = p.share_issues.filter(i => i.severity === "error");
  const publish = async () => {
    setMsg(null);
    try {
      const r = await postJson("/api/packs/publish", { folder: p.folder, version });
      setMsg(`Published ${r.tag}${r.pushed ? " and pushed" : r.push_error ? ` (push failed: ${r.push_error})` : " (local tag; no remote)"}.`);
      onChanged();
    } catch (e) { setMsg(e.message); }
  };
  return (
    <div className="pk-mine-card">
      <div className="pk-top"><span className="pk-ico">📤</span>
        <div className="grow"><b>{p.name}</b><div className="muted small">{p.folder} · {p.version ? `v${p.version}` : "never released"} · {p.rules} rules · ~{fmtTokens(p.tokens)} tokens</div></div>
        {p.remote && <span className="muted small mono">{p.remote}</span>}</div>
      <div className="pk-cols">
        <div><h4>Share check</h4>
          {p.share_issues.length === 0 ? <div className="pk-row"><Badge kind="ok">✓ passed</Badge> No secrets or personal data</div>
            : p.share_issues.slice(0, 6).map((i, n) => <div key={n} className="pk-row"><Badge kind={i.severity === "error" ? "err" : "warn"}>{i.severity}</Badge> {i.path}:{i.line} {i.message}</div>)}</div>
        <div><h4>Unreleased changes</h4>
          {p.unreleased.length ? p.unreleased.map(c => <div key={c.sha} className="pk-row">• {c.subject}{c.why && <span className="muted"> — {c.why}</span>}</div>)
            : <div className="pk-empty">{p.version ? `Nothing new since v${p.version}` : "First release"}</div>}</div>
      </div>
      <div className="pk-release">
        <span className="grow">Next version {p.suggested ? <>suggested <b>v{p.suggested}</b> (removed rule → major, new rule → minor, changes → patch)</> : "— nothing to release"}. Release notes are built from the Why-lines.</span>
        <input className="ver" value={version} onChange={e => setVersion(e.target.value)} placeholder="1.0.0" />
        <button className="btn primary" disabled={!version || blocking.length > 0} title={blocking.length ? "Fix the share check first" : ""} onClick={publish}>Publish v{version}</button>
      </div>
      {msg && <div className="notice">{msg}</div>}
    </div>
  );
}

export function PacksMine({ onChanged }) {
  const [packs, setPacks] = useState(null);
  const load = () => getJson("/api/packs/mine").then(r => setPacks(r.packs));
  useEffect(() => { load(); }, []);
  if (!packs) return <p className="muted">Loading…</p>;
  if (!packs.length) return <p className="muted">You publish no packs yet. A pack is a folder with <code>railvane-pack.yaml</code> and markdown rules; list it under <code>publish:</code> in railvane.yaml.</p>;
  return packs.map(p => p.error
    ? <div key={p.folder} className="alert">{p.folder}: {p.error}</div>
    : <MinePack key={p.folder} p={p} onChanged={() => { load(); onChanged(); }} />);
}

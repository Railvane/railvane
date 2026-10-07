import { useEffect, useMemo, useState } from "react";
import { getJson, postJson } from "../api.js";
import { Badge } from "../components/Badges.jsx";
import { areaOptions, TYPES } from "../meta.js";

export default function Classify({ schema, onChanged, onOpen, onNavigate }) {
  const [data, setData] = useState(null);
  const [rows, setRows] = useState({});
  const [picked, setPicked] = useState(new Set());
  const [why, setWhy] = useState("");
  const [msg, setMsg] = useState(null);
  const areas = useMemo(() => areaOptions(schema), [schema]);

  const load = () => getJson("/api/classify").then(d => {
    setData(d);
    setRows(Object.fromEntries(d.rows.map(r => [r.id, { type: r.type, area: r.area ?? "", visibility: r.visibility, owner: r.owner }])));
    setPicked(new Set());
  });
  useEffect(() => { load(); }, []);

  if (!data) return <p className="muted">Scanning…</p>;
  const set = (id, key, value) => setRows(r => ({ ...r, [id]: { ...r[id], [key]: value } }));
  const toggle = id => setPicked(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const open = data.rows.filter(r => !r.confirmed);
  const ready = id => rows[id].type && rows[id].area && rows[id].visibility && rows[id].owner;
  const confirm = async () => {
    const items = [...picked].map(id => ({ id, ...rows[id] }));
    try {
      const r = await postJson("/api/classify/confirm", { items, why: why || null });
      setMsg(`Confirmed ${r.confirmed} file(s)${r.commit ? ` in commit ${r.commit.slice(0, 7)}` : ""}.`);
      setWhy(""); load(); onChanged();
    } catch (e) { setMsg(e.message); }
  };

  return (
    <section>
      <h1>Classify</h1>
      <p className="sub">Railvane recognises guardrail files in your sources and guesses their type, lifecycle area and visibility.
        Check the guesses and confirm them: they are stored in <code>.railvane/manifest.yaml</code> in your workspace — your source
        files are never rewritten. Quality checks, filters and sharing work on this metadata.</p>
      <p className="muted small">Missing a repository? <span className="link" onClick={() => onNavigate("repos")}>Add it under Repositories →</span></p>
      <div className="imp-sum">
        <b>{open.length}</b> to review · {data.rows.length - open.length} confirmed
        <button className="btn" onClick={() => setPicked(new Set(open.filter(r => r.confidence >= 0.5 && ready(r.id)).map(r => r.id)))}>Select confident ones</button>
        <button className="btn" onClick={() => setPicked(new Set())}>Clear</button>
        <input className="why-input" placeholder="Why? (optional)" value={why} onChange={e => setWhy(e.target.value)} />
        <button className="btn primary" disabled={!picked.size || [...picked].some(id => !ready(id))} onClick={confirm}>Confirm {picked.size || ""}</button>
      </div>
      {msg && <div className="notice">{msg}</div>}
      <table className="imp-table">
        <thead><tr><th /><th>File</th><th>Type</th><th>Lifecycle area</th><th>Visibility</th><th>Owner</th><th>Confidence</th><th /></tr></thead>
        <tbody>
          {data.rows.map(r => (
            <tr key={r.id} className={r.confirmed ? "done" : ""}>
              <td>{!r.confirmed && <input type="checkbox" checked={picked.has(r.id)} onChange={() => toggle(r.id)} />}</td>
              <td><div className="link" onClick={() => onOpen(r.id)}>{r.title}</div><div className="mono muted small">{r.id}</div></td>
              <td><select value={rows[r.id].type} disabled={r.confirmed} onChange={e => set(r.id, "type", e.target.value)}>
                {Object.entries(TYPES).map(([k, t]) => <option key={k} value={k}>{t.label}</option>)}</select></td>
              <td><select value={rows[r.id].area} disabled={r.confirmed} onChange={e => set(r.id, "area", e.target.value)}>
                <option value="">— choose —</option>
                {areas.map(a => <option key={a.id} value={a.id}>{a.phase} · {a.name}</option>)}</select>
                {!r.confirmed && r.alt_areas.length > 0 && <div className="muted small">or {r.alt_areas.join(", ")}</div>}</td>
              <td><select value={rows[r.id].visibility} disabled={r.confirmed} onChange={e => set(r.id, "visibility", e.target.value)}>
                <option value="private">🔒 private</option><option value="shared">👥 shared</option></select></td>
              <td><input className="owner" value={rows[r.id].owner} disabled={r.confirmed} onChange={e => set(r.id, "owner", e.target.value)} /></td>
              <td><div className="conf"><i style={{ width: `${r.confidence * 100}%`, background: r.confidence >= 0.75 ? "var(--green)" : r.confidence >= 0.5 ? "var(--yellow)" : "var(--red)" }} /></div>
                <span className="muted small"> {Math.round(r.confidence * 100)}%</span></td>
              <td>{r.confirmed ? <Badge kind="ok">✓ {r.meta_source}</Badge> : r.errors.length ? <Badge kind="err" title={r.errors.join("\n")}>frontmatter</Badge> : null}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

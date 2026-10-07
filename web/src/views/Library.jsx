import { useEffect, useMemo, useState } from "react";
import { getJson, qs } from "../api.js";
import { Badge, VisBadge } from "../components/Badges.jsx";
import { areaName, fmtTokens, timeAgo, TYPES, typeInfo } from "../meta.js";

const ORDER = Object.keys(TYPES);

function Chip({ on, onClick, children }) {
  return <button className={`chip ${on ? "on" : ""}`} onClick={onClick}>{children}</button>;
}

function Card({ e, schema, findings, onOpen }) {
  const f = findings?.[e.id];
  return (
    <div className="gcard" onClick={() => onOpen(e.id)}>
      <div className="stripe" style={{ background: typeInfo(e.type).color }} />
      <div className="t">{e.title}</div>
      <div className="p">{e.source}/{e.path}</div>
      {e.excerpt && <div className="d">{e.excerpt}</div>}
      <div className="meta">
        <VisBadge visibility={e.visibility} />
        <span className="tag">{areaName(schema, e.area)}</span>
        {e.tags.slice(0, 3).map(t => <span key={t} className="tag">#{t}</span>)}
        {!e.confirmed && <Badge kind="info" title="Metadata guessed, not confirmed yet">unconfirmed</Badge>}
        {e.pack && <Badge kind="info">📦 {e.pack.name}</Badge>}
        {e.subtype && <span className={`tag sub-${e.subtype}`}>{e.subtype}</span>}
        {e.copy_of && <Badge kind={e.copy_status === "drift" ? "warn" : "muted"} title={`Copy of ${e.copy_of}`}>⧉ {e.copy_status === "drift" ? "copy out of date" : "copy"}</Badge>}
        {e.copies?.length > 0 && <Badge kind="muted" title="Master with copies in other repositories">⧉ {e.copies.length} cop{e.copies.length > 1 ? "ies" : "y"}</Badge>}
        {e.promoted_to && <Badge kind="ok" title={`Promoted to ${e.promoted_to}`}>⇧ promoted</Badge>}
        {f?.error > 0 && <Badge kind="err">✕ {f.error}</Badge>}
        {f?.warning > 0 && <Badge kind="warn">⚠ {f.warning}</Badge>}
        <span className="when">{fmtTokens(e.tokens)} tok · {timeAgo(e.updated)}</span>
      </div>
    </div>
  );
}

export default function Library({ library, schema, findings, onOpen, onNavigate }) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState(null);
  const [filter, setFilter] = useState({ visibility: null, source: null, phase: null, subtype: null, unconfirmed: false });
  const entries = library.entries;

  useEffect(() => {
    if (!q.trim()) { setHits(null); return; }
    const t = setTimeout(() => getJson(`/api/search?${qs({ q })}`)
      .then(r => setHits(new Set(r.results.map(x => x.id)))).catch(() => setHits(new Set())), 200);
    return () => clearTimeout(t);
  }, [q]);

  const shown = useMemo(() => entries.filter(e =>
    (!hits || hits.has(e.id)) &&
    (!filter.visibility || e.visibility === filter.visibility) &&
    (!filter.source || e.source === filter.source) &&
    (!filter.phase || e.phase === filter.phase) &&
    (!filter.subtype || e.subtype === filter.subtype) &&
    (!filter.unconfirmed || !e.confirmed)), [entries, hits, filter]);

  const toggle = (key, value) => setFilter(f => ({ ...f, [key]: f[key] === value ? null : value }));
  const unconfirmed = entries.filter(e => !e.confirmed).length;
  const shared = entries.filter(e => e.visibility === "shared").length;

  return (
    <section>
      <div className="view-head">
        <div><h1>Library</h1><p className="sub">All guardrails across {library.sources.length} source(s), grouped by type.</p></div>
        <input className="search" placeholder="Search rules, tags, content…" value={q} onChange={e => setQ(e.target.value)} />
      </div>
      <div className="stats">
        <div className="stat"><b>{entries.length}</b><span>guardrail files</span></div>
        <div className="stat"><b>{library.sources.length}</b><span>sources</span></div>
        <div className="stat"><b>{entries.length - shared} <small>/ {shared}</small></b><span>private / shared</span></div>
        <div className="stat clickable" onClick={() => onNavigate("classify")}>
          <b className={unconfirmed ? "warn" : ""}>{unconfirmed}</b><span>unconfirmed → review in Classify</span>
        </div>
      </div>
      <div className="filters">
        <Chip on={filter.visibility === "private"} onClick={() => toggle("visibility", "private")}>🔒 private</Chip>
        <Chip on={filter.visibility === "shared"} onClick={() => toggle("visibility", "shared")}>👥 shared</Chip>
        <Chip on={filter.unconfirmed} onClick={() => setFilter(f => ({ ...f, unconfirmed: !f.unconfirmed }))}>unconfirmed</Chip>
        <span className="sep" />
        {["feedback", "project", "user", "reference"].map(s =>
          <Chip key={s} on={filter.subtype === s} onClick={() => toggle("subtype", s)}>memory: {s}</Chip>)}
        <span className="sep" />
        {library.sources.map(s => <Chip key={s.id} on={filter.source === s.id} onClick={() => toggle("source", s.id)}>{s.id}</Chip>)}
        <span className="sep" />
        {Object.entries(schema.phases).map(([id, p]) =>
          <Chip key={id} on={filter.phase === id} onClick={() => toggle("phase", id)}>{p.name}</Chip>)}
      </div>
      {shown.length === 0 && <p className="muted">No guardrails match.</p>}
      <div className="board">
        {ORDER.map(type => {
          const items = shown.filter(e => e.type === type);
          if (!items.length) return null;
          return (
            <div className="col" key={type}>
              <h3><span className="dot" style={{ background: typeInfo(type).color }} />{typeInfo(type).label} <span className="n">{items.length}</span></h3>
              {items.map(e => <Card key={e.id} e={e} schema={schema} findings={findings} onOpen={onOpen} />)}
            </div>
          );
        })}
      </div>
    </section>
  );
}

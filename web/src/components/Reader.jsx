import { useEffect, useState } from "react";
import { getJson, qs } from "../api.js";
import { Badge, VisBadge } from "./Badges.jsx";
import EditDialog from "./EditDialog.jsx";
import FileHistory from "./FileHistory.jsx";
import Markdown from "./Markdown.jsx";
import { areaName, fmtTokens, timeAgo, typeInfo } from "../meta.js";

function LinkList({ ids, entries, onOpen }) {
  return ids.map(id => (
    <div key={id} className="link" onClick={() => onOpen(id)}>{entries[id]?.title ?? id}</div>
  ));
}

export default function Reader({ id, schema, entries, findings, onOpen, onClose, onChanged }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("read");
  const [editing, setEditing] = useState(false);

  const load = () => getJson(`/api/file?${qs({ id })}`).then(setFile).catch(e => setError(e.message));
  useEffect(() => { setFile(null); setError(null); setTab("read"); load(); }, [id]);
  useEffect(() => {
    const onKey = e => e.key === "Escape" && !editing && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editing, onClose]);

  const openByName = name => {
    const key = name.toLowerCase().replace(/[\s_]+/g, "-");
    const hit = Object.values(entries).find(e =>
      e.path.toLowerCase().replace(/\.mdc?$/, "").split("/").pop().replace(/_/g, "-") === key ||
      e.title.toLowerCase().replace(/[\s_]+/g, "-") === key);
    if (hit) onOpen(hit.id);
  };

  const f = findings?.[id];
  return (
    <>
      <div className="overlay on" onClick={onClose} />
      <div className="drawer open">
        <div className="drawer-head">
          <span className="dot" style={{ background: typeInfo(file?.type).color, width: 10, height: 10 }} />
          <div className="grow">
            <div className="title">{file?.title ?? "…"}</div>
            <div className="mono muted small">{id}</div>
          </div>
          <div className="seg">
            <span className={tab === "read" ? "on" : ""} onClick={() => setTab("read")}>Read</span>
            <span className={tab === "history" ? "on" : ""} onClick={() => setTab("history")}>History</span>
          </div>
          <button className="btn" disabled={!file || file.readonly}
            title={file?.readonly ? "This source is read-only" : "Edit this file"} onClick={() => setEditing(true)}>✎ Edit</button>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>
        {error && <div className="alert m">{error}</div>}
        {file && (
          <div className="reader">
            <div className="doc">
              {tab === "read"
                ? <Markdown text={file.body} onWikilink={openByName} />
                : <FileHistory id={id} />}
            </div>
            <aside className="side">
              <h4>Metadata <span className="muted small">({file.meta_source}{file.confirmed ? "" : ", unconfirmed"})</span></h4>
              <div className="kv">
                <span>type</span><span>{typeInfo(file.type).label}</span>
                <span>area</span><span>{areaName(schema, file.area)}</span>
                <span>visibility</span><span><VisBadge visibility={file.visibility} /></span>
                <span>owner</span><span>{file.owner || "—"}</span>
                <span>status</span><span>{file.status}</span>
                {file.scope && <><span>scope</span><span>{file.scope}</span></>}
                <span>tags</span><span>{file.tags.map(t => "#" + t).join(" ") || "—"}</span>
                <span>size</span><span>{file.lines} lines · ~{fmtTokens(file.tokens)} tokens</span>
                <span>changed</span><span>{timeAgo(file.updated)}</span>
              </div>
              {file.pack && <><h4>Pack</h4><div className="issue">📦 {file.pack.name} v{file.pack.version}{file.overridden && <Badge kind="warn">local override</Badge>}</div></>}
              {(file.errors.length > 0 || f) && <h4>Quality</h4>}
              {file.errors.map(e => <div key={e} className="issue"><Badge kind="err">frontmatter</Badge> {e}</div>)}
              {f?.items?.map((x, i) => <div key={i} className="issue"><Badge kind={x.severity === "error" ? "err" : x.severity === "warning" ? "warn" : "info"}>{x.rule}</Badge> {x.message}</div>)}
              {file.resolved_links.length > 0 && <><h4>Links to</h4><LinkList ids={file.resolved_links} entries={entries} onOpen={onOpen} /></>}
              {file.backlinks.length > 0 && <><h4>Linked from</h4><LinkList ids={file.backlinks} entries={entries} onOpen={onOpen} /></>}
              {file.dead_links.length > 0 && <><h4>Dead links</h4>{file.dead_links.map(l => <div key={l} className="link dead">{l}</div>)}</>}
            </aside>
          </div>
        )}
      </div>
      {editing && file && (
        <EditDialog file={file} onClose={() => setEditing(false)}
          onSaved={() => { setEditing(false); load(); onChanged(); }} />
      )}
    </>
  );
}

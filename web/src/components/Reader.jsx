import { useEffect, useState } from "react";
import { getJson, qs } from "../api.js";
import { Badge, VisBadge } from "./Badges.jsx";
import EditDialog from "./EditDialog.jsx";
import FileHistory from "./FileHistory.jsx";
import Markdown from "./Markdown.jsx";
import PromoteDialog from "./PromoteDialog.jsx";
import SplitDialog from "./SplitDialog.jsx";
import { RepoLine } from "./RepoBadge.jsx";
import { areaName, fmtTokens, timeAgo, typeInfo } from "../meta.js";

function LinkList({ ids, entries, onOpen }) {
  return ids.map(id => (
    <div key={id} className="link" onClick={() => onOpen(id)}>{entries[id]?.title ?? id}</div>
  ));
}

export default function Reader({ id, schema, entries, findings, sources, onOpen, onClose, onChanged }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("read");
  const [editing, setEditing] = useState(false);
  const [dialog, setDialog] = useState(null);     // "split" | "promote"
  const [message, setMessage] = useState(null);

  const load = () => getJson(`/api/file?${qs({ id })}`).then(setFile).catch(e => setError(e.message));
  useEffect(() => { setFile(null); setError(null); setMessage(null); setTab("read"); load(); }, [id]);
  useEffect(() => {
    const onKey = e => e.key === "Escape" && !editing && !dialog && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editing, dialog, onClose]);
  const done = text => { setDialog(null); setMessage(text); load(); onChanged(); };

  const openByName = name => {
    const key = name.toLowerCase().replace(/[\s_]+/g, "-");
    const hit = Object.values(entries).find(e =>
      e.path.toLowerCase().replace(/\.mdc?$/, "").split("/").pop().replace(/_/g, "-") === key ||
      e.title.toLowerCase().replace(/[\s_]+/g, "-") === key);
    if (hit) onOpen(hit.id);
  };

  const f = findings?.[id];
  const src = sources.find(s => s.id === file?.source);
  const canSplit = file && ["project-rules", "index", "agent"].includes(file.type) && !file.copy_of && !file.pack;
  const canPromote = file && file.type === "memory" && !file.promoted_to;
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
          {canPromote && <button className="btn" title="Turn this memory into a real guardrail" onClick={() => setDialog("promote")}>⇧ Promote to rule</button>}
          {canSplit && <button className="btn" title="Split into separate files, shared rules and skills" onClick={() => setDialog("split")}>✂ Split</button>}
          <button className="btn" disabled={!file || file.readonly || Boolean(file.copy_of)}
            title={file?.copy_of ? "This is a copy — edit the master" : file?.readonly ? "This source is read-only" : "Edit this file"}
            onClick={() => setEditing(true)}>✎ Edit</button>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>
        {error && <div className="alert m">{error}</div>}
        {message && <div className="notice m">{message}</div>}
        {file?.copy_of && (
          <div className={`${file.copy_status === "drift" ? "alert" : "notice"} m`}>
            ⧉ Copy of <span className="link" onClick={() => onOpen(file.copy_of)}>{file.copy_of}</span>
            {file.copy_status === "drift" ? " — out of date: sync the copies under Repositories." : " — in sync. Edit the master, not this copy."}
          </div>)}
        {file?.promoted_to && (
          <div className="notice m">⇧ Promoted to <span className="link" onClick={() => onOpen(file.promoted_to)}>{file.promoted_to}</span> — this memory is kept for reference.</div>)}
        {file && (
          <div className="reader">
            <div className="doc">
              {tab === "read"
                ? <Markdown text={file.body} onWikilink={openByName} />
                : <FileHistory id={id} readonly={file.readonly || Boolean(file.pack)} onChanged={() => { load(); onChanged(); }} />}
            </div>
            <aside className="side">
              <h4>Metadata <span className="muted small">({file.meta_source}{file.confirmed ? "" : ", unconfirmed"})</span></h4>
              <div className="kv">
                <span>type</span><span>{typeInfo(file.type).label}{file.subtype ? ` · ${file.subtype}` : ""}</span>
                <span>area</span><span>{areaName(schema, file.area)}</span>
                <span>visibility</span><span><VisBadge visibility={file.visibility} /></span>
                <span>owner</span><span>{file.owner || "—"}</span>
                <span>status</span><span>{file.status}</span>
                {file.scope && <><span>scope</span><span>{file.scope}</span></>}
                <span>tags</span><span>{file.tags.map(t => "#" + t).join(" ") || "—"}</span>
                <span>size</span><span>{file.lines} lines · ~{fmtTokens(file.tokens)} tokens</span>
                <span>changed</span><span>{timeAgo(file.updated)}</span>
                {src && <><span>source</span><span>{src.id}{src.readonly ? " · 🔒 read-only" : ""}</span></>}
                {src && <><span>repository</span><span><RepoLine repo={src.repo} path={src.display_root} /></span></>}
              </div>
              {file.copies.length > 0 && <><h4>Copies</h4>{file.copies.map(c => (
                <div key={c.id} className="issue"><span className="link" onClick={() => onOpen(c.id)}>{c.id}</span>
                  <Badge kind={c.status === "in_sync" ? "ok" : "warn"}>{c.status.replace("_", " ")}</Badge></div>))}</>}
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
      {dialog === "split" && <SplitDialog id={id} schema={schema} onClose={() => setDialog(null)}
        onDone={r => done(`Split into ${r.files.length} files${r.workspace_commit ? " — shared rules registered in your workspace" : ""}.`)} />}
      {dialog === "promote" && file && <PromoteDialog file={file} schema={schema} onClose={() => setDialog(null)}
        onDone={r => done(`Promoted to ${r.path}.${r.note ? " " + r.note : ""}`)} />}
      {editing && file && (
        <EditDialog file={file} onClose={() => setEditing(false)}
          onSaved={() => { setEditing(false); load(); onChanged(); }} />
      )}
    </>
  );
}

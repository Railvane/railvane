import { useState } from "react";
import { putJson } from "../api.js";
import Markdown from "./Markdown.jsx";

export default function EditDialog({ file, onClose, onSaved }) {
  const [text, setText] = useState(file.text);
  const [why, setWhy] = useState("");
  const [subject, setSubject] = useState("");
  const [mode, setMode] = useState("commit");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const isPack = Boolean(file.pack);
  const isGit = file.source_kind === "git";

  const save = async () => {
    setBusy(true); setError(null);
    try {
      const r = await putJson("/api/file", { id: file.id, text, base_hash: file.hash, why, mode, subject: subject || null });
      if (r.mode === "pr") setResult(r); else onSaved();
    } catch (e) { setError(e.message); }
    setBusy(false);
  };

  if (result) {
    return (
      <div className="modal-bg on">
        <div className="modal small">
          <h2>Pull request ready</h2>
          <p>Your change is on branch <code>{result.branch}</code>.</p>
          {result.url && <p><a href={result.url} target="_blank" rel="noreferrer">Open on GitHub ↗</a></p>}
          <button className="btn primary" onClick={onSaved}>Done</button>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-bg on">
      <div className="modal">
        <div className="drawer-head">
          <div className="grow"><div className="title">Edit {file.title}</div>
            <div className="muted small">{isPack ? "Pack rule: your change is saved as a local override; the pack itself stays unchanged." : file.id}</div></div>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>
        <div className="edit-body">
          <textarea value={text} onChange={e => setText(e.target.value)} spellCheck="false" />
          <div className="edit-preview"><Markdown text={text.replace(/^---[\s\S]*?\n---\n/, "")} /></div>
        </div>
        <div className="edit-foot">
          <input placeholder={`Summary (default: Update ${file.title})`} value={subject} onChange={e => setSubject(e.target.value)} />
          <input className="why-input" placeholder="Why? (required — becomes part of the history)" value={why} onChange={e => setWhy(e.target.value)} />
          {!isPack && (
            <div className="seg">
              <span className={mode === "commit" ? "on" : ""} onClick={() => setMode("commit")}>Direct commit</span>
              <span className={mode === "pr" ? "on" : isGit ? "" : "disabled"} title={isGit ? "" : "Pull requests are available for git sources"}
                onClick={() => isGit && setMode("pr")}>Pull request</span>
            </div>
          )}
          <button className="btn primary" disabled={busy || !why.trim() || text === file.text} onClick={save}>
            {busy ? "Saving…" : isPack ? "Save override" : mode === "pr" ? "Open pull request" : "Commit"}
          </button>
        </div>
        {error && <div className="alert m">{error}</div>}
      </div>
    </div>
  );
}

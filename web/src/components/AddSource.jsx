import { useState } from "react";
import { postJson } from "../api.js";

export default function AddSource({ onAdded }) {
  const [kind, setKind] = useState("path");
  const [value, setValue] = useState("");
  const [readonly, setReadonly] = useState(true);
  const [msg, setMsg] = useState(null);
  const add = async () => {
    setMsg(null);
    try {
      const r = await postJson("/api/sources", { [kind]: value.trim(), readonly });
      setValue("");
      setMsg({ ok: true, text: `Source added${r.commit ? ` (commit ${r.commit.slice(0, 7)} in the workspace)` : ""}.` });
      onAdded();
    } catch (e) { setMsg({ ok: false, text: e.message }); }
  };
  return (
    <div className="card">
      <h2>Add a source</h2>
      <div className="add-source">
        <div className="seg">
          <span className={kind === "path" ? "on" : ""} onClick={() => setKind("path")}>📁 Folder</span>
          <span className={kind === "git" ? "on" : ""} onClick={() => setKind("git")}>🐙 Git URL</span>
        </div>
        <input value={value} onChange={e => setValue(e.target.value)}
          placeholder={kind === "path" ? "Folder, relative to the workspace (e.g. ../my-repo)" : "https://github.com/org/repo.git"} />
        <label className="check" title="Railvane never writes to a read-only source">
          <input type="checkbox" checked={readonly} onChange={e => setReadonly(e.target.checked)} /> read-only</label>
        <button className="btn primary" disabled={!value.trim()} onClick={add}>Add source</button>
      </div>
      <p className="muted small">
        A folder is read in place; a git URL is cloned into Railvane's cache. Running in Docker? The folder must be mounted
        into the container first (see <code>compose.yaml</code>). The source is added to <code>railvane.yaml</code> as a commit.
      </p>
      {msg && <div className={msg.ok ? "notice" : "alert"}>{msg.text}</div>}
    </div>
  );
}

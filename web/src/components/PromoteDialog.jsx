import { useMemo, useState } from "react";
import { postJson } from "../api.js";
import { areaOptions } from "../meta.js";
import Markdown from "./Markdown.jsx";

const slug = s => s.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "rule";

export default function PromoteDialog({ file, schema, onClose, onDone }) {
  const areas = useMemo(() => areaOptions(schema), [schema]);
  const [text, setText] = useState(`# ${file.title}\n\n${file.body.trim()}\n`);
  const [folder, setFolder] = useState("guardrails/shared");
  const [name, setName] = useState(`${slug(file.title.replace(/^feedback\s+/i, ""))}.md`);
  const [area, setArea] = useState(file.area ?? "");
  const [visibility, setVisibility] = useState("shared");
  const [why, setWhy] = useState("");
  const [error, setError] = useState(null);

  const promote = async () => {
    setError(null);
    try {
      onDone(await postJson("/api/promote", { id: file.id, path: `${folder}/${name}`, text, area, visibility, why: why || null }));
    } catch (e) { setError(e.message); }
  };

  return (
    <div className="modal-bg on">
      <div className="modal">
        <div className="drawer-head">
          <div className="grow"><div className="title">Promote to rule</div>
            <div className="muted small">Turn this memory into a real guardrail in your workspace — versioned, checked and shareable. The memory is marked as promoted.</div></div>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>
        <div className="edit-body">
          <textarea value={text} onChange={e => setText(e.target.value)} spellCheck="false" />
          <div className="edit-preview"><Markdown text={text} /></div>
        </div>
        <div className="edit-foot">
          <select value={folder} onChange={e => setFolder(e.target.value)}>
            <option value="guardrails/shared">guardrails/shared (reusable)</option>
            <option value="guardrails">guardrails</option>
          </select>
          <input className="fname" value={name} onChange={e => setName(e.target.value)} />
          <select value={area} onChange={e => setArea(e.target.value)}>
            <option value="">— area —</option>
            {areas.map(a => <option key={a.id} value={a.id}>{a.phase} · {a.name}</option>)}
          </select>
          <select value={visibility} onChange={e => setVisibility(e.target.value)}>
            <option value="shared">👥 shared</option><option value="private">🔒 private</option>
          </select>
        </div>
        <div className="edit-foot">
          <input className="why-input" placeholder="Why? (optional)" value={why} onChange={e => setWhy(e.target.value)} />
          <button className="btn primary" disabled={!area || !name.endsWith(".md")} onClick={promote}>Promote</button>
        </div>
        {error && <div className="alert m">{error}</div>}
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { getJson, postJson } from "../api.js";
import { Badge } from "./Badges.jsx";

const STATUS = { in_sync: ["ok", "in sync"], drift: ["warn", "out of date"], missing: ["err", "missing"] };

export default function CopiesPanel({ onChanged }) {
  const [copies, setCopies] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => getJson("/api/copies").then(r => setCopies(r.copies));
  useEffect(() => { load(); }, []);

  const sync = async source => {
    setBusy(true); setMsg(null);
    try {
      const r = await postJson("/api/copies/sync", { source });
      const done = Object.entries(r.synced).map(([s, x]) => `${s}${x.commit ? ` (${x.commit.slice(0, 7)})` : ""}`);
      setMsg({ ok: true, text: done.length ? `Synced: ${done.join(", ")}` : "Everything was already in sync." });
      load(); onChanged();
    } catch (e) { setMsg({ ok: false, text: e.message }); }
    setBusy(false);
  };

  if (!copies) return null;
  const outdated = copies.filter(c => c.status !== "in_sync");
  return (
    <div className="card">
      <div className="row">
        <h2 className="grow" style={{ margin: 0 }}>Copies of shared guardrails</h2>
        {copies.length > 0 && <button className="btn primary" disabled={busy || !outdated.length} onClick={() => sync(null)}>
          {busy ? "Syncing…" : outdated.length ? `Sync ${outdated.length} cop${outdated.length > 1 ? "ies" : "y"}` : "All in sync"}</button>}
      </div>
      <p className="muted small">The master lives in your workspace; repositories hold a copy that agents read. Edit the master, then sync — each repository gets one commit.</p>
      {copies.length === 0 && <p className="muted small">No copies yet. Split a file and mark parts as “Shared” to create them.</p>}
      {copies.map(c => {
        const [kind, label] = STATUS[c.status] ?? ["muted", c.status];
        return (
          <div key={c.source + c.path} className="row copy-row">
            <span className="mono small">{c.master}</span><span className="muted">→</span>
            <span className="mono small"><b>{c.source}</b>/{c.path}</span>
            <Badge kind={kind}>{label}</Badge>
            {c.readonly && <Badge kind="muted" title="Make the source editable to sync">🔒 read-only</Badge>}
          </div>
        );
      })}
      {msg && <div className={msg.ok ? "notice" : "alert"}>{msg.text}</div>}
    </div>
  );
}

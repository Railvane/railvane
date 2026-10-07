import { useEffect, useState } from "react";
import { getJson, qs } from "../api.js";
import DiffView from "../components/DiffView.jsx";
import { timeAgo } from "../meta.js";

function day(iso) {
  const d = new Date(iso);
  const today = new Date();
  const diff = Math.floor((today.setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 86400000);
  return diff === 0 ? "Today" : diff === 1 ? "Yesterday" : d.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
}

export default function Timeline({ entries, onOpen }) {
  const [commits, setCommits] = useState(null);
  const [error, setError] = useState(null);
  const [sel, setSel] = useState(null);
  const [diff, setDiff] = useState("");

  useEffect(() => {
    getJson("/api/timeline?limit=80").then(r => { setCommits(r.commits); if (r.commits[0]) select(r.commits[0]); })
      .catch(e => setError(e.message));
  }, []);

  const select = c => {
    setSel(c);
    const id = c.ids[0];
    if (!id) { setDiff(""); return; }
    getJson(`/api/diff?${qs({ id, sha: c.sha })}`).then(r => setDiff(r.diff)).catch(e => setDiff(`(${e.message})`));
  };

  if (error) return <div className="alert">{error}</div>;
  if (!commits) return <p className="muted">Loading timeline…</p>;
  let last = "";
  return (
    <section>
      <h1>Timeline</h1>
      <p className="sub">Every change to every guardrail, with the reason why. Learn from old agreements.</p>
      {!commits.length && <p className="muted">No history yet. Sources that are git repositories show their commits here.</p>}
      <div className="tl-grid">
        <div className="tl">
          {commits.map(c => {
            const d = day(c.date);
            const head = d !== last ? <div className="tl-day">{(last = d)}</div> : null;
            return (
              <div key={c.repo + c.sha}>
                {head}
                <div className={`tl-item ${sel?.sha === c.sha ? "on" : ""}`} onClick={() => select(c)}>
                  <b>{c.subject}</b>
                  <div className="muted small">
                    {c.ids.map(id => entries[id]?.title ?? id).join(", ") || c.settings.join(", ")} · {c.author} · {timeAgo(c.date)} · <span className="mono">{c.short}</span>
                  </div>
                  {c.why && <div className="why">💬 {c.why}</div>}
                </div>
              </div>
            );
          })}
        </div>
        {sel && (
          <div className="tl-detail">
            <div className="diff-head">
              <b>{sel.subject}</b>
              <span className="muted small mono">{sel.repo} · {sel.short}</span>
              {sel.ids[0] && <button className="btn" onClick={() => onOpen(sel.ids[0])}>Open file</button>}
            </div>
            {sel.ids.length > 1 && <div className="muted small">Also changed: {sel.ids.slice(1).map(id => entries[id]?.title ?? id).join(", ")}</div>}
            {sel.ids[0] ? <DiffView diff={diff} /> : <div className="muted small">Workspace settings changed: {sel.settings.join(", ")}</div>}
            <div className="learn">
              ✦ <b>Why</b><br />
              {sel.why ?? <span className="muted">No reason was recorded for this change. Railvane asks for one on every edit.</span>}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

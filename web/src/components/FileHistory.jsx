import { useEffect, useState } from "react";
import { getJson, postJson, qs } from "../api.js";
import DiffView from "./DiffView.jsx";
import { timeAgo } from "../meta.js";
import { useDialog } from "./Dialog.jsx";

export default function FileHistory({ id, readonly, onChanged }) {
  const dialog = useDialog();
  const [commits, setCommits] = useState(null);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(null);
  const [diff, setDiff] = useState("");

  const load = () => getJson(`/api/history?${qs({ id })}`)
    .then(r => { setCommits(r.commits); if (r.commits[0]) show(r.commits[0].sha); })
    .catch(e => setError(e.message));
  useEffect(() => { load(); }, [id]);

  const show = sha => {
    setOpen(sha);
    getJson(`/api/diff?${qs({ id, sha })}`).then(r => setDiff(r.diff)).catch(e => setDiff(`(${e.message})`));
  };

  const revert = async c => {
    const why = await dialog.prompt({
      title: "Revert this change?", message: `“${c.subject}” is undone in a new commit.`,
      label: "Why? (stored in the commit message)", placeholder: "e.g. this rule caused wrong deploys",
      required: true, confirmLabel: "Revert", danger: true,
    });
    if (!why) return;
    try { await postJson("/api/revert", { id, sha: c.sha, why }); onChanged?.(); load(); }
    catch (e) { await dialog.tell({ title: "Could not revert", message: e.message }); }
  };

  if (error) return <div className="notice">{error}</div>;
  if (!commits) return <p className="muted">Loading history…</p>;
  if (!commits.length) return <p className="muted">No commits for this file yet.</p>;
  return (
    <div className="file-history">
      {commits.map(c => (
        <div key={c.sha} className={`commit ${open === c.sha ? "on" : ""}`} onClick={() => show(c.sha)}>
          <div className="commit-top">
            <b>{c.subject}</b>
            <span className="muted small">{c.author} · {timeAgo(c.date)} · <span className="mono">{c.short}</span></span>
          </div>
          {c.why && <div className="why">💬 {c.why}</div>}
          {open === c.sha && (
            <>
              <DiffView diff={diff} />
              {!readonly && <button className="btn small-btn" onClick={e => { e.stopPropagation(); revert(c); }}>↶ Revert this change</button>}
            </>
          )}
        </div>
      ))}
    </div>
  );
}

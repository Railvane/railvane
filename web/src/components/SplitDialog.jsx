import { useEffect, useMemo, useState } from "react";
import { getJson, postJson, qs } from "../api.js";
import { areaOptions, fmtTokens } from "../meta.js";

const ACTIONS = {
  keep: { label: "Keep inline", hint: "stays in this file" },
  project: { label: "Project file", hint: ".claude/guardrails/ in this repository" },
  shared: { label: "Shared", hint: "master in your workspace, copy in this repository" },
  skill: { label: "Skill", hint: "loaded only when needed" },
};
const stem = f => f.replace(/\.md$/, "");

function previewMain(plan, choices) {
  // Mirrors the server: imports for files, a skills list at the end
  let out = plan.preamble.trimEnd() + "\n";
  const skills = [];
  let parent = null;
  for (const p of plan.parts) {
    const c = choices[p.key];
    if (p.parent && p.parent !== parent && c.action !== "skill") out += `\n## ${p.parent}\n`;
    parent = p.parent;
    if (c.action === "keep") out += "\n" + p.text.trim() + "\n";
    else if (c.action === "skill") skills.push(`- \`${stem(c.filename)}\` — ${p.heading}`);
    else out += `@.claude/guardrails/${c.action === "shared" ? "shared/" : ""}${c.filename}\n`;
  }
  if (skills.length) out += "\n## On request (skills)\n" + skills.join("\n") + "\n";
  return out;
}

export default function SplitDialog({ id, schema, onClose, onDone }) {
  const [plan, setPlan] = useState(null);
  const [choices, setChoices] = useState({});
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const areas = useMemo(() => areaOptions(schema), [schema]);

  useEffect(() => {
    getJson(`/api/split/plan?${qs({ id })}`).then(p => {
      setPlan(p);
      setChoices(Object.fromEntries(p.parts.map(x => [x.key, { ...x.suggestion, area: x.suggestion.area ?? "" }])));
    }).catch(e => setError(e.message));
  }, [id]);

  const set = (key, field, value) => setChoices(c => ({ ...c, [key]: { ...c[key], [field]: value } }));
  const apply = async () => {
    setBusy(true); setError(null);
    try { onDone(await postJson("/api/split/apply", { id, choices, why })); }
    catch (e) { setError(e.message); }
    setBusy(false);
  };

  const stats = plan && Object.values(choices).reduce((s, c, i) => {
    const t = plan.parts[i]?.tokens ?? 0;
    return c.action === "skill" ? { ...s, onDemand: s.onDemand + t } : s;
  }, { onDemand: 0 });

  return (
    <div className="modal-bg on">
      <div className="modal">
        <div className="drawer-head">
          <div className="grow"><div className="title">Split {id}</div>
            <div className="muted small">One part per section. Files get no frontmatter — metadata goes to the sidecar, so agents do not pay tokens for it.</div></div>
          <button className="btn ghost" onClick={onClose}>✕</button>
        </div>
        {error && <div className="alert m">{error}</div>}
        {plan?.readonly && <div className="alert m">This source is read-only. Make it editable under Repositories to split it.</div>}
        {plan && (
          <div className="split-body">
            <div className="split-parts">
              {plan.parts.map(p => {
                const c = choices[p.key];
                return (
                  <div key={p.key} className={`split-part a-${c.action}`}>
                    <div className="split-head">
                      <b>{p.parent ? `${p.parent} › ` : ""}{p.heading}</b>
                      <span className="muted small">{p.lines} lines · ~{fmtTokens(p.tokens)} tok</span>
                    </div>
                    <div className="split-controls">
                      <div className="seg">
                        {Object.entries(ACTIONS).map(([k, a]) =>
                          <span key={k} title={a.hint} className={c.action === k ? "on" : ""} onClick={() => set(p.key, "action", k)}>{a.label}</span>)}
                      </div>
                      {c.action !== "keep" && <input className="fname" value={c.filename} onChange={e => set(p.key, "filename", e.target.value)} />}
                      {c.action !== "keep" && (
                        <select value={c.area} onChange={e => set(p.key, "area", e.target.value)}>
                          <option value="">— area —</option>
                          {areas.map(a => <option key={a.id} value={a.id}>{a.phase} · {a.name}</option>)}
                        </select>)}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="split-preview">
              <div className="muted small">New file (~{fmtTokens(Math.max(0, plan.tokens - stats.onDemand))} tokens always loaded incl. imports, ~{fmtTokens(stats.onDemand)} on demand)</div>
              <pre>{previewMain(plan, choices)}</pre>
            </div>
          </div>
        )}
        <div className="edit-foot">
          <input className="why-input" placeholder="Why? (required)" value={why} onChange={e => setWhy(e.target.value)} />
          <button className="btn primary" disabled={!plan || plan.readonly || busy || !why.trim()} onClick={apply}>{busy ? "Splitting…" : "Split as commit"}</button>
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import { Badge } from "../components/Badges.jsx";

const META = {
  "frontmatter-invalid": { ico: "⌗", hint: "Fix the frontmatter or remove it and confirm metadata in Import." },
  "share-secret": { ico: "🔒", hint: "Remove the secret, or make the file private." },
  "share-personal": { ico: "🔒", hint: "Mask it, or make the file private." },
  "file-too-long": { ico: "≡", hint: "Split it into smaller files per topic." },
  "token-heavy": { ico: "◷", hint: "Agents follow fewer, sharper rules more reliably." },
  "dead-link": { ico: "↯", hint: "Fix the link name or create the missing note." },
  "duplicate-rule": { ico: "⧉", hint: "Keep the rule in one place and link to it." },
  stale: { ico: "⏱", hint: "Still relevant? Update it or mark it deprecated." },
  unconfirmed: { ico: "?", hint: "Confirm type, area, visibility and owner in Import." },
};
const KIND = { error: "err", warning: "warn", info: "info" };

export default function Quality({ quality, entries, onOpen, onNavigate }) {
  const [level, setLevel] = useState("warning");
  if (!quality) return <p className="muted">Checking…</p>;
  const order = { error: 3, warning: 2, info: 1 };
  const shown = quality.findings.filter(f => order[f.severity] >= order[level]);
  const groups = {};
  for (const f of shown) (groups[f.rule] ??= []).push(f);
  const c = quality.counts;

  return (
    <section>
      <div className="view-head">
        <div><h1>Quality</h1><p className="sub">Lint checks across all guardrails. The same checks run in CI with <code>railvane lint</code>.</p></div>
        <div className="seg">
          {["error", "warning", "info"].map(l => (
            <span key={l} className={level === l ? "on" : ""} onClick={() => setLevel(l)}>{l === "info" ? "Everything" : l === "warning" ? "Warnings +" : "Errors"}</span>
          ))}
        </div>
      </div>
      <div className="stats three">
        <div className="stat"><b className={c.error ? "err" : ""}>{c.error}</b><span>errors</span></div>
        <div className="stat"><b className={c.warning ? "warn" : ""}>{c.warning}</b><span>warnings</span></div>
        <div className="stat"><b>{c.info}</b><span>info</span></div>
      </div>
      {!shown.length && <div className="notice">✓ Nothing at this level. Nice and lean.</div>}
      {Object.entries(groups).map(([rule, items]) => (
        <div key={rule} className="q-group">
          <div className="q-head">
            <span className={`q-ico q-${items[0].severity}`}>{META[rule]?.ico ?? "•"}</span>
            <div className="grow"><b>{rule}</b> <span className="muted small">· {items.length}</span><div className="muted small">{META[rule]?.hint}</div></div>
            {rule === "unconfirmed" && <button className="btn" onClick={() => onNavigate("import")}>Open Import</button>}
          </div>
          {items.slice(0, 50).map((f, i) => (
            <div key={i} className="q-row" onClick={() => onOpen(f.id)}>
              <Badge kind={KIND[f.severity]}>{f.severity}</Badge>
              <span className="mono small">{entries[f.id]?.source ?? ""}/{entries[f.id]?.path ?? f.id}{f.line ? `:${f.line}` : ""}</span>
              <span className="grow">{f.message}</span>
            </div>
          ))}
          {items.length > 50 && <div className="muted small">…and {items.length - 50} more</div>}
        </div>
      ))}
    </section>
  );
}

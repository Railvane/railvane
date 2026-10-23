import { useEffect, useState } from "react";
import { postJson } from "../api.js";
import { Badge } from "../components/Badges.jsx";
import DiffView from "../components/DiffView.jsx";
import { fmtTokens } from "../meta.js";
import { useDialog } from "../components/Dialog.jsx";

const ICON = { changed: "✎", added: "+", removed: "−" };

function UpdatePanel({ pack, onChanged }) {
  const [keep, setKeep] = useState(new Set());
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => {
    // Rules you already override locally are kept by default
    setKeep(new Set(pack.changes?.filter(c => c.overridden && c.kind === "changed").map(c => c.path) ?? []));
    setError(null);
  }, [pack.name, pack.latest]);

  if (pack.error) return <div className="alert">{pack.error}</div>;
  if (!pack.update) return <div className="pk-empty">✓ {pack.name} is up to date (v{pack.version ?? "—"}).</div>;
  const toggle = p => setKeep(k => { const n = new Set(k); n.has(p) ? n.delete(p) : n.add(p); return n; });
  const apply = async () => {
    setBusy(true); setError(null);
    try { await postJson("/api/packs/update", { name: pack.name, keep: [...keep], why: why || null }); onChanged(); }
    catch (e) { setError(e.message); }
    setBusy(false);
  };
  const delta = (pack.tokens_after ?? pack.tokens) - pack.tokens;
  return (
    <>
      <div className="pk-diff-head">
        <div className="grow"><b>{pack.name}</b><div className="muted small">v{pack.version} → v{pack.latest}{pack.major && " · major update: read carefully"}</div></div>
      </div>
      {pack.changes.map(c => (
        <div key={c.path} className={`pk-change k-${c.kind}`}>
          <div className="pk-ch-top">
            <span className="pk-ch-ico">{ICON[c.kind]}</span><b>{c.path}</b><span className="muted small">{c.kind}</span>
            {c.kind === "changed" && (
              <label className="pk-accept"><input type="checkbox" checked={!keep.has(c.path)} onChange={() => toggle(c.path)} /> accept</label>
            )}
          </div>
          <DiffView diff={c.diff} />
          {c.why.map((w, i) => <div key={i} className="why">💬 Why: {w}</div>)}
          {c.overridden && <div className="pk-mine">⚠ You override this rule locally — your version stays unless you accept.</div>}
          {keep.has(c.path) && !c.overridden && <div className="pk-mine">Kept: your current text becomes a local override.</div>}
        </div>
      ))}
      <div className="pk-impact">Token impact: ~{fmtTokens(pack.tokens)} → ~{fmtTokens(pack.tokens_after)} ({delta >= 0 ? "+" : ""}{delta})</div>
      <div className="edit-foot">
        <input className="why-input" placeholder="Why update now? (optional)" value={why} onChange={e => setWhy(e.target.value)} />
        <button className="btn primary" disabled={busy} onClick={apply}>{busy ? "Updating…" : `Update to v${pack.latest}`}</button>
      </div>
      {error && <div className="alert m">{error}</div>}
    </>
  );
}

export default function PacksInstalled({ packs, onRefresh, onChanged }) {
  const [sel, setSel] = useState(packs.find(p => p.update)?.name ?? packs[0]?.name);
  const pack = packs.find(p => p.name === sel);
  const dialog = useDialog();
  const remove = async name => {
    const ok = await dialog.confirm({
      title: `Remove pack ${name}?`, message: "Its rules leave your library. Local overrides stay in .railvane/overrides.",
      confirmLabel: "Remove pack", danger: true,
    });
    if (!ok) return;
    try { await postJson("/api/packs/remove", { name }); onChanged(); }
    catch (e) { await dialog.tell({ title: "Could not remove the pack", message: e.message }); }
  };
  if (!packs.length) return <div className="notice">No packs installed yet. Find one under Discover, or install from a git URL.</div>;
  return (
    <div className="pk-grid2">
      <div>
        {packs.map(p => (
          <div key={p.name} className={`pk-card clickable ${p.name === sel ? "sel" : ""}`} onClick={() => setSel(p.name)}>
            <div className="pk-top"><span className="pk-ico">📦</span>
              <div className="grow"><b>{p.name}</b><div className="muted small">{p.description || p.source}{p.license && ` · ${p.license}`}</div></div>
              <span className="pk-ver">v{p.version ?? "—"}</span></div>
            <div className="pk-meta"><span>{p.rules ?? "?"} rules</span><span>~{fmtTokens(p.tokens ?? 0)} tokens</span>
              {p.overrides?.length > 0 && <Badge kind="warn">{p.overrides.length} local override{p.overrides.length > 1 ? "s" : ""}</Badge>}</div>
            {p.error ? <div className="pk-warn">⚠ {p.error}</div>
              : p.update ? <div className={`pk-next ${p.major ? "major" : ""}`}>⬆ v{p.latest} available · {p.changes.length} change(s){p.major ? " · major" : ""}</div>
                : <div className="pk-uptodate">✓ Up to date</div>}
            <button className="btn ghost small-btn" onClick={e => { e.stopPropagation(); remove(p.name); }}>Remove</button>
          </div>
        ))}
        <button className="btn" onClick={onRefresh}>⟳ Check upstream for updates</button>
      </div>
      <div className="pk-diff">{pack && <UpdatePanel pack={pack} onChanged={onChanged} />}</div>
    </div>
  );
}

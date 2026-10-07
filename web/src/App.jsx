import { useCallback, useEffect, useMemo, useState } from "react";
import { getJson, postJson } from "./api.js";
import Reader from "./components/Reader.jsx";
import Sidebar from "./Sidebar.jsx";
import Import from "./views/Import.jsx";
import Library from "./views/Library.jsx";
import Packs from "./views/Packs.jsx";
import Quality from "./views/Quality.jsx";
import Timeline from "./views/Timeline.jsx";
import Workspace from "./views/Workspace.jsx";

const VIEWS = ["library", "import", "timeline", "quality", "packs", "workspace"];
const fromHash = () => (VIEWS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "library");

export default function App() {
  const [view, setView] = useState(fromHash);
  const [base, setBase] = useState(null);       // health + schema + workspace
  const [library, setLibrary] = useState(null);
  const [quality, setQuality] = useState(null);
  // ?open=<guardrail id> opens the reader directly (shareable link)
  const [readerId, setReaderId] = useState(() => new URLSearchParams(location.search).get("open"));
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(() => Promise.all([getJson("/api/library"), getJson("/api/quality")])
    .then(([lib, q]) => { setLibrary(lib); setQuality(q); setError(null); })
    .catch(e => setError(e.message)), []);

  useEffect(() => {
    Promise.all([getJson("/api/health"), getJson("/api/schema"), getJson("/api/workspace")])
      .then(([health, schema, workspace]) => setBase({ health, schema, workspace }))
      .catch(e => setError(e.message));
    reload();
    const onHash = () => setView(fromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [reload]);

  const navigate = v => { location.hash = v; };
  const refresh = async () => {
    setBusy(true);
    try { await postJson("/api/refresh"); await reload(); } catch (e) { setError(e.message); }
    setBusy(false);
  };
  const entries = useMemo(() => Object.fromEntries((library?.entries ?? []).map(e => [e.id, e])), [library]);
  const findings = quality?.by_file;
  const counts = {
    library: library?.entries.length,
    import: library?.entries.filter(e => !e.confirmed && !e.pack).length,
    quality: quality ? quality.counts.error + quality.counts.warning : undefined,
    qualityKind: quality?.counts.error ? "err" : "warn",
  };

  const ready = base && library;
  return (
    <div className="app">
      <Sidebar view={view} onNavigate={navigate} counts={counts} version={base?.health.version}
        workspace={library?.workspace} onRefresh={refresh} busy={busy} />
      <main className="content">
        {error && <div className="alert">Something went wrong: {error}</div>}
        {!ready && !error && <p className="muted">Loading your guardrails…</p>}
        {ready && view === "library" && <Library library={library} schema={base.schema} findings={findings} onOpen={setReaderId} onNavigate={navigate} />}
        {ready && view === "import" && <Import schema={base.schema} onChanged={reload} onOpen={setReaderId} />}
        {ready && view === "timeline" && <Timeline entries={entries} onOpen={setReaderId} />}
        {ready && view === "quality" && <Quality quality={quality} entries={entries} onOpen={setReaderId} onNavigate={navigate} />}
        {ready && view === "packs" && <Packs onChanged={reload} />}
        {ready && view === "workspace" && <Workspace workspace={base.workspace} schema={base.schema} />}
      </main>
      {readerId && base && (
        <Reader id={readerId} schema={base.schema} entries={entries} findings={findings}
          onOpen={setReaderId} onClose={() => setReaderId(null)} onChanged={reload} />
      )}
    </div>
  );
}

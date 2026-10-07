import { useEffect, useState } from "react";
import { getJson } from "./api.js";
import Sidebar from "./Sidebar.jsx";
import WorkspacePanel from "./WorkspacePanel.jsx";

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([getJson("/api/health"), getJson("/api/workspace"), getJson("/api/schema")])
      .then(([health, workspace, schema]) => setData({ health, workspace, schema }))
      .catch(e => setError(e.message));
  }, []);

  return (
    <div className="app">
      <Sidebar version={data?.health.version} />
      <main className="content">
        {error && <div className="alert">Cannot reach the Railvane API: {error}</div>}
        {!data && !error && <p className="muted">Loading…</p>}
        {data && <WorkspacePanel workspace={data.workspace} schema={data.schema} />}
      </main>
    </div>
  );
}

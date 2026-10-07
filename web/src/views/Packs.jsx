import { useEffect, useState } from "react";
import { getJson } from "../api.js";
import PacksInstalled from "./PacksInstalled.jsx";
import { PacksDiscover, PacksMine } from "./PacksShare.jsx";

export default function Packs({ onChanged }) {
  const [tab, setTab] = useState("installed");
  const [installed, setInstalled] = useState(null);
  const [error, setError] = useState(null);

  const load = (fetch = false) => getJson(`/api/packs${fetch ? "?fetch=true" : ""}`)
    .then(r => setInstalled(r.packs)).catch(e => setError(e.message));
  useEffect(() => { load(); }, []);
  const changed = () => { load(); onChanged(); };
  const updates = installed?.filter(p => p.update).length ?? 0;

  return (
    <section>
      <h1>Packs</h1>
      <p className="sub">Share guardrails as versioned packs. Install packs from other teams; upstream changes arrive as a reviewable diff, and your local overrides stay yours.</p>
      <div className="pk-tabs">
        {[["installed", `Installed`, installed?.length], ["discover", "Discover"], ["mine", "My packs"]].map(([k, l, n]) => (
          <span key={k} className={`pk-tab ${tab === k ? "on" : ""}`} onClick={() => setTab(k)}>{l}{n != null && <span className="pk-n">{n}</span>}</span>
        ))}
        {updates > 0 && <span className="pk-upd">⬆ {updates} update{updates > 1 ? "s" : ""} available</span>}
      </div>
      {error && <div className="alert">{error}</div>}
      {tab === "installed" && installed && <PacksInstalled packs={installed} onRefresh={() => load(true)} onChanged={changed} />}
      {tab === "discover" && <PacksDiscover onChanged={changed} />}
      {tab === "mine" && <PacksMine onChanged={changed} />}
    </section>
  );
}

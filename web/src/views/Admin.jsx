import { AdminPanel } from "@webheaven/kit/admin";
import "@webheaven/kit/admin.css";

// The admin module from webheaven-kit: the same component a hub shows for a linked Railvane.
export default function Admin() {
  return (
    <>
      <h1>Admin</h1>
      <p className="sub">This Railvane instance: status, usage, the audit trail (git) and updates.</p>
      <AdminPanel base="/api/admin" defaultHub="https://webheaven.nl" />
    </>
  );
}

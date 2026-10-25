import { useState } from "react";
import { Link } from "react-router-dom";
import { getAuditLogs } from "../api.js";
import { useLoad } from "../useLoad.js";
import Empty from "../components/Empty.jsx";
import Loading from "../components/Loading.jsx";
import Pager from "../components/Pager.jsx";
import { fmtDate, labelOf } from "../format.js";

function Target({ type, id }) {
  if (type === "submission") return <Link to={`/submissions/${id}`}>submission #{id.slice(-6)}</Link>;
  if (type === "user") return <Link to={`/users/${id}`}>user #{id.slice(-6)}</Link>;
  return <span>{labelOf(type)} {labelOf(id)}</span>;
}

export default function AuditLog() {
  const [skip, setSkip] = useState(0);
  const { data, error, loading, reload } = useLoad(() => getAuditLogs({ skip, limit: 25 }), [skip]);
  return (
    <div>
      <h1>Audit log</h1>
      <p className="muted">Every administrator decision and rule change, newest first.</p>
      <div className="toolbar"><button className="btn secondary" onClick={reload}>Refresh</button></div>
      <div className="card">
        <Loading loading={loading} error={error} onRetry={reload} />
        {data && data.items.length === 0 && <Empty>No admin actions yet.</Empty>}
        {data && data.items.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Admin</th><th>Action</th><th>Target</th><th>Details</th></tr></thead>
              <tbody>
                {data.items.map((a) => (
                  <tr key={a.id}>
                    <td>{fmtDate(a.created_at)}</td><td>{a.admin_email}</td><td>{labelOf(a.action)}</td>
                    <td><Target type={a.target_type} id={a.target_id} /></td>
                    <td className="small mono">{Object.keys(a.details).length ? JSON.stringify(a.details) : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={data} onSkip={setSkip} />
      </div>
    </div>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";
import { getFraudFlags } from "../api.js";
import { useLoad } from "../useLoad.js";
import Empty from "../components/Empty.jsx";
import Loading from "../components/Loading.jsx";
import Pager from "../components/Pager.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { fmtDate, labelOf } from "../format.js";

export default function FraudLogs() {
  const [skip, setSkip] = useState(0);
  const { data, error, loading, reload } = useLoad(() => getFraudFlags({ skip, limit: 25 }), [skip]);
  return (
    <div>
      <h1>Fraud and duplicate flags</h1>
      <p className="muted">
        Each row is a submission that raised at least one review flag. A flag asks for a human check;
        it is not proof of fraud. Open the submission to compare it with the related ones.
      </p>
      <div className="toolbar"><button className="btn secondary" onClick={reload}>Refresh</button></div>
      <div className="card">
        <Loading loading={loading} error={error} onRetry={reload} />
        {data && data.items.length === 0 && <Empty>No flagged submissions.</Empty>}
        {data && data.items.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>User</th><th>Flags</th><th>Reasons</th><th>Related</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {data.items.map((f) => (
                  <tr key={f.id}>
                    <td>{fmtDate(f.created_at)}</td>
                    <td>{f.user_email || "-"}</td>
                    <td><span className="flag-list">{f.flags.map((x) => <span key={x} className="flag">{labelOf(x)}</span>)}</span></td>
                    <td className="small">{f.reasons.join(" ")}</td>
                    <td>{f.related_submission_ids.map((rid) => (
                      <Link key={rid} className="related" to={`/submissions/${rid}`}>#{rid.slice(-6)}</Link>))}</td>
                    <td><StatusBadge status={f.submission_status} /></td>
                    <td><Link className="btn small" to={`/submissions/${f.submission_id}`}>Review</Link></td>
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

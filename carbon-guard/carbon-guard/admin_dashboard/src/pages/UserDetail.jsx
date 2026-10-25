import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getUser, setUserActive } from "../api.js";
import { useLoad } from "../useLoad.js";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import Empty from "../components/Empty.jsx";
import Loading from "../components/Loading.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { activityLabel, fmtDate, labelOf, num, statusLabel } from "../format.js";

export default function UserDetail() {
  const { id } = useParams();
  const { data: u, error, loading, reload } = useLoad(() => getUser(id), [id]);
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function toggle() {
    setBusy(true);
    try {
      await setUserActive(id, !u.is_active);
      setMessage(u.is_active ? "Account deactivated." : "Account reactivated.");
      reload();
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
      setAsking(false);
    }
  }

  if (loading && !u) return <Loading loading />;
  if (error) return <Loading error={error} onRetry={reload} />;
  if (!u) return null;

  return (
    <div>
      <p><Link to="/users">&larr; Back to users</Link></p>
      <div className="title-row">
        <h1>{u.name}</h1>
        {u.is_active ? <span className="badge verified">Active</span> : <span className="badge rejected">Deactivated</span>}
      </div>

      <div className="cards">
        <div className="card stat"><span>Trust Score</span><b>{num(u.trust_score, 1)}</b></div>
        <div className="card stat"><span>Green Credits</span><b>{num(u.green_credits_total)}</b></div>
        <div className="card stat"><span>Submissions</span><b>{u.submission_counts.total}</b></div>
        <div className="card stat"><span>Verified</span><b>{u.submission_counts.verified}</b></div>
      </div>

      <div className="card actions">
        <span className="muted">{u.email} &middot; {u.role} &middot; joined {fmtDate(u.created_at)}</span>
        {u.role === "user" && (
          <button className={`btn push ${u.is_active ? "danger" : ""}`} onClick={() => setAsking(true)}>
            {u.is_active ? "Deactivate account" : "Reactivate account"}
          </button>
        )}
        {message && <span className="info">{message}</span>}
      </div>

      <div className="card">
        <h3>Submissions by status</h3>
        <p>{Object.entries(u.submission_counts).filter(([k]) => k !== "total")
          .map(([k, v]) => `${statusLabel(k)}: ${v}`).join(" · ")}</p>
        {u.recent_submissions.length === 0 ? <Empty>No submissions yet.</Empty> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Submitted</th><th>Activity</th><th>Status</th><th>Score</th><th>Credits</th><th></th></tr></thead>
              <tbody>
                {u.recent_submissions.map((s) => (
                  <tr key={s.id}>
                    <td>{fmtDate(s.created_at)}</td><td>{activityLabel(s.activity_type)}</td>
                    <td><StatusBadge status={s.status} /></td><td>{num(s.verification_score, 1)}</td>
                    <td>{num(s.green_credits_awarded)}</td>
                    <td><Link to={`/submissions/${s.id}`}>Open</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="grid2">
        <div className="card">
          <h3>Trust Score history</h3>
          {u.trust_events.length === 0 ? <Empty>No changes yet (starts at 50).</Empty> : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Date</th><th>Event</th><th>Change</th><th>After</th></tr></thead>
                <tbody>
                  {[...u.trust_events].reverse().map((e) => (
                    <tr key={e.id} title={e.reason}>
                      <td>{fmtDate(e.created_at)}</td><td>{labelOf(e.event_type)}</td>
                      <td className={e.score_delta < 0 ? "error" : "info"}>{e.score_delta > 0 ? "+" : ""}{num(e.score_delta, 1)}</td>
                      <td>{num(e.score_after, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div className="card">
          <h3>Green Credit history</h3>
          {u.credit_transactions.length === 0 ? <Empty>No credits awarded yet.</Empty> : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Date</th><th>Submission</th><th>Amount</th></tr></thead>
                <tbody>
                  {u.credit_transactions.map((t) => (
                    <tr key={t.id}>
                      <td>{fmtDate(t.created_at)}</td>
                      <td><Link to={`/submissions/${t.submission_id}`}>#{t.submission_id.slice(-6)}</Link></td>
                      <td>+{num(t.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog open={asking} busy={busy} danger={u.is_active}
                     title={u.is_active ? "Deactivate this account?" : "Reactivate this account?"}
                     message={u.is_active ? "The user will be logged out and cannot log in until reactivated. Their data is kept."
                                          : "The user will be able to log in again."}
                     confirmLabel={u.is_active ? "Deactivate" : "Reactivate"}
                     onConfirm={toggle} onCancel={() => setAsking(false)} />
    </div>
  );
}

import { Link } from "react-router-dom";
import { getStats, getReports } from "../api.js";
import { useLoad } from "../useLoad.js";
import Loading from "../components/Loading.jsx";
import Empty from "../components/Empty.jsx";
import { activityLabel, num, statusLabel } from "../format.js";

const STATUS_ORDER = ["pending", "manual_review", "verified", "rejected", "processing"];

function Stat({ label, value, to }) {
  const body = (<><span>{label}</span><b>{value}</b></>);
  return to ? <Link className="card stat link" to={to}>{body}</Link> : <div className="card stat">{body}</div>;
}

function Bars({ rows, max }) {
  return rows.map(({ key, label, value, cls }) => (
    <div className="bar-row" key={key}>
      <span className="bar-label">{label}</span>
      <div className="bar-track"><div className={`bar-fill ${cls || ""}`} style={{ width: `${max ? (value / max) * 100 : 0}%` }} /></div>
      <span className="bar-n">{value}</span>
    </div>
  ));
}

export default function Overview() {
  const stats = useLoad(getStats);
  const reports = useLoad(getReports);
  const s = stats.data;
  const r = reports.data;

  return (
    <div>
      <h1>Overview</h1>
      <Loading loading={stats.loading} error={stats.error} onRetry={stats.reload} />
      {s && (
        <>
          <div className="cards">
            <Stat label="Registered users" value={s.total_users} to="/users" />
            <Stat label="Total submissions" value={s.total_submissions} to="/submissions?status=all" />
            <Stat label="Awaiting review" value={s.awaiting_review} to="/submissions" />
            <Stat label="Verified" value={s.by_status.verified} to="/submissions?status=verified" />
            <Stat label="Rejected" value={s.by_status.rejected} to="/submissions?status=rejected" />
            <Stat label="Green Credits awarded" value={num(s.total_credits_issued)} />
            <Stat label="Estimated CO2 (kg/year)" value={num(s.total_co2_estimate)} />
            <Stat label="Flagged for review" value={s.fraud_flagged} to="/fraud" />
          </div>

          <div className="grid2">
            <div className="card">
              <h3>Submissions by status</h3>
              {s.total_submissions === 0 ? <Empty>No submissions yet.</Empty> : (
                <Bars max={s.total_submissions} rows={STATUS_ORDER.map((st) => (
                  { key: st, label: statusLabel(st), value: s.by_status[st] || 0, cls: st }))} />
              )}
            </div>
            <div className="card">
              <h3>Submissions by activity</h3>
              {s.total_submissions === 0 ? <Empty>No submissions yet.</Empty> : (
                <Bars max={s.total_submissions} rows={Object.entries(s.by_activity).map(([a, n]) => (
                  { key: a, label: activityLabel(a), value: n, cls: "activity" }))} />
              )}
            </div>
          </div>
        </>
      )}

      <div className="card">
        <h3>Environmental impact report</h3>
        <Loading loading={reports.loading} error={reports.error} onRetry={reports.reload} />
        {r && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Activity</th><th>Submitted</th><th>Verified</th><th>Rejected</th><th>Credits awarded</th><th>CO2 estimate (kg/year)</th></tr>
              </thead>
              <tbody>
                {r.by_activity.map((a) => (
                  <tr key={a.activity_type}>
                    <td>{activityLabel(a.activity_type)}</td><td>{a.submitted}</td><td>{a.verified}</td>
                    <td>{a.rejected}</td><td>{num(a.credits_issued)}</td><td>{num(a.co2_estimate_kg_per_year)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {r && r.by_month.length > 0 && (
          <>
            <h3 className="spaced">Last 12 months</h3>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Month</th><th>Submitted</th><th>Verified</th><th>Credits awarded</th></tr></thead>
                <tbody>
                  {r.by_month.map((m) => (
                    <tr key={m.month}><td>{m.month}</td><td>{m.submitted}</td><td>{m.verified}</td><td>{num(m.credits_issued)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {r && <p className="muted small">{r.note}</p>}
      </div>
    </div>
  );
}

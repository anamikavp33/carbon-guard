import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listSubmissions } from "../api.js";
import { useLoad } from "../useLoad.js";
import Loading from "../components/Loading.jsx";
import Empty from "../components/Empty.jsx";
import Pager from "../components/Pager.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { ACTIVITY_LABELS, STATUS_LABELS, activityLabel, fmtDate, labelOf, num } from "../format.js";

const PAGE_SIZE = 25;

export default function Submissions() {
  // Filters live in the URL (e.g. #/submissions?status=verified) so links and Back work.
  const [params, setParams] = useSearchParams();
  const status = params.get("status") || "review";
  const activity = params.get("activity") || "all";
  const search = params.get("search") || "";
  const skip = Number(params.get("skip") || 0);
  const [searchText, setSearchText] = useState(search);

  const set = (changes) => {
    const next = { status, activity, search, skip: 0, ...changes };
    const isDefault = (k, v) => v === "" || v === 0 || (k === "status" && v === "review") || (k === "activity" && v === "all");
    setParams(Object.fromEntries(Object.entries(next).filter(([k, v]) => !isDefault(k, v))));
  };

  // "review" = the review queue: pending first, then manual review (two requests, shown together).
  const load = async () => {
    if (status !== "review") {
      return listSubmissions({ status, activity_type: activity, search, skip, limit: PAGE_SIZE });
    }
    const base = { activity_type: activity, search, limit: 200 };
    const [p, m] = await Promise.all([
      listSubmissions({ ...base, status: "pending" }), listSubmissions({ ...base, status: "manual_review" })]);
    const items = [...p.items, ...m.items].sort((a, b) => a.created_at.localeCompare(b.created_at));
    return { items, total: items.length, skip: 0, limit: 400 };
  };
  const { data, error, loading, reload } = useLoad(load, [status, activity, search, skip]);

  return (
    <div>
      <h1>Submissions</h1>
      <div className="toolbar wrap">
        <div>
          <label htmlFor="status">Status</label>
          <select id="status" value={status} onChange={(e) => set({ status: e.target.value })}>
            <option value="review">Review queue (pending + manual review)</option>
            <option value="all">All</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="activity">Activity</label>
          <select id="activity" value={activity} onChange={(e) => set({ activity: e.target.value })}>
            <option value="all">All activities</option>
            {Object.entries(ACTIVITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <form className="search" onSubmit={(e) => { e.preventDefault(); set({ search: searchText.trim() }); }}>
          <label htmlFor="search">User email contains</label>
          <div className="row">
            <input id="search" value={searchText} onChange={(e) => setSearchText(e.target.value)} placeholder="e.g. asha" />
            <button className="btn secondary">Search</button>
          </div>
        </form>
        <button className="btn secondary push" onClick={reload}>Refresh</button>
      </div>

      <div className="card">
        <Loading loading={loading} error={error} onRetry={reload} />
        {data && data.items.length === 0 && (
          <Empty>{status === "review" ? "Nothing waiting for review. Well done!" : "No submissions match these filters."}</Empty>
        )}
        {data && data.items.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Submitted</th><th>User</th><th>Activity</th><th>Score</th><th>Flags</th><th>Status</th><th>Credits</th><th></th></tr>
              </thead>
              <tbody>
                {data.items.map((s) => (
                  <tr key={s.id}>
                    <td>{fmtDate(s.created_at)}</td>
                    <td>{s.user_email}</td>
                    <td>{activityLabel(s.activity_type)}</td>
                    <td>{num(s.verification_score, 1)}</td>
                    <td>{s.flags.length ? <span className="flag-list">{s.flags.map((f) => <span key={f} className="flag">{labelOf(f)}</span>)}</span> : "-"}</td>
                    <td><StatusBadge status={s.status} /></td>
                    <td>{num(s.green_credits_awarded)}</td>
                    <td><Link className="btn small" to={`/submissions/${s.id}`}>Review</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {status !== "review" && <Pager page={data} onSkip={(n) => set({ skip: n })} />}
      </div>
    </div>
  );
}

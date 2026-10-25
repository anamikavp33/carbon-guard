import { useState } from "react";
import { Link } from "react-router-dom";
import { listUsers } from "../api.js";
import { useLoad } from "../useLoad.js";
import Empty from "../components/Empty.jsx";
import Loading from "../components/Loading.jsx";
import Pager from "../components/Pager.jsx";
import { fmtDate, num } from "../format.js";

const PAGE_SIZE = 25;

export default function Users() {
  const [search, setSearch] = useState("");
  const [text, setText] = useState("");
  const [skip, setSkip] = useState(0);
  const { data, error, loading, reload } = useLoad(() => listUsers({ search, skip, limit: PAGE_SIZE }), [search, skip]);

  return (
    <div>
      <h1>Users</h1>
      <div className="toolbar wrap">
        <form className="search" onSubmit={(e) => { e.preventDefault(); setSkip(0); setSearch(text.trim()); }}>
          <label htmlFor="user-search">Name or email contains</label>
          <div className="row">
            <input id="user-search" value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. asha" />
            <button className="btn secondary">Search</button>
          </div>
        </form>
        <button className="btn secondary push" onClick={reload}>Refresh</button>
      </div>
      <div className="card">
        <Loading loading={loading} error={error} onRetry={reload} />
        {data && data.items.length === 0 && <Empty>{search ? `No users match "${search}".` : "No users yet."}</Empty>}
        {data && data.items.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Trust Score</th><th>Green Credits</th><th>Joined</th><th></th></tr>
              </thead>
              <tbody>
                {data.items.map((u) => (
                  <tr key={u.id}>
                    <td>{u.name}</td><td>{u.email}</td><td>{u.role}</td>
                    <td>{u.is_active ? <span className="badge verified">Active</span> : <span className="badge rejected">Deactivated</span>}</td>
                    <td>{num(u.trust_score, 1)}</td><td>{num(u.green_credits_total)}</td><td>{fmtDate(u.created_at)}</td>
                    <td><Link className="btn secondary small" to={`/users/${u.id}`}>Open</Link></td>
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

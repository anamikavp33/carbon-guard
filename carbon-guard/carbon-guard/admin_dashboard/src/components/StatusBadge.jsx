import { statusLabel } from "../format.js";

export default function StatusBadge({ status }) {
  if (!status) return <span className="muted">-</span>;
  return <span className={`badge ${status}`}>{statusLabel(status)}</span>;
}

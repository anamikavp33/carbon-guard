// The backend sends UTC times ending in "Z". Older values without a zone are treated as UTC too.
export function fmtDate(s) {
  if (!s) return "-";
  const iso = /Z$|[+-]\d\d:\d\d$/.test(s) ? s : s + "Z";
  const d = new Date(iso);
  return isNaN(d) ? "-" : d.toLocaleString();
}

export const labelOf = (s) => (s || "").replace(/_/g, " ");

export const ACTIVITY_LABELS = {
  tree_plantation: "Tree plantation",
  solar_panel: "Solar panel",
  water_harvesting: "Water harvesting",
};

export const STATUS_LABELS = {
  processing: "Processing",
  pending: "Pending approval",
  manual_review: "Manual review",
  verified: "Verified",
  rejected: "Rejected",
};

export const SCALE_UNITS = {
  tree_plantation: "trees",
  solar_panel: "kW",
  water_harvesting: "m³",
};

export const activityLabel = (a) => ACTIVITY_LABELS[a] || labelOf(a);
export const statusLabel = (s) => STATUS_LABELS[s] || labelOf(s);

// 12.0 -> "12", 12.345 -> "12.35", null -> "-"
export function num(v, digits = 2) {
  if (v === null || v === undefined || v === "") return "-";
  return Number(v).toLocaleString(undefined, { maximumFractionDigits: digits });
}

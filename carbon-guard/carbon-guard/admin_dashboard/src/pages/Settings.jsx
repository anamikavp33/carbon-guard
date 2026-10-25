import { useEffect, useState } from "react";
import { getConfig, updateConfig } from "../api.js";
import { useLoad } from "../useLoad.js";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import Loading from "../components/Loading.jsx";
import { activityLabel, labelOf } from "../format.js";

// Simple (single number) settings, with a short explanation each.
const FIELDS = [
  ["recommend_threshold", "Score needed for 'pending' (recommended for approval)", "0-100"],
  ["ai_min_confidence", "Minimum AI confidence for a match", "0-1"],
  ["gps_max_accuracy_m", "Worst acceptable GPS accuracy (metres)", "> 0"],
  ["duplicate_location_radius_m", "Nearby-location radius (metres)", "> 0"],
  ["similar_image_max_distance", "Similar-image hash distance (0 = identical only)", "0-64"],
  ["max_submissions_per_10min", "Submissions per 10 minutes before a flag", ">= 1"],
  ["satellite_min_ndvi", "Minimum NDVI for satellite points (tree plantation)", "-1 to 1"],
];
const GROUPS = [
  ["weights", "Score weights (points; should total 100)"],
  ["trust_rules", "Trust Score change per admin decision"],
  ["impact_factors", "CO2 estimate per unit (kg/year) - placeholder values"],
  ["max_scale", "Maximum quantity before an 'implausible' flag"],
];

export default function Settings() {
  const { data, error, loading, reload } = useLoad(getConfig);
  const [form, setForm] = useState(null);
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (data) setForm(JSON.parse(JSON.stringify(data)));
  }, [data]);

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setGroup = (g, k, v) => setForm((f) => ({ ...f, [g]: { ...f[g], [k]: v } }));

  // Only send what changed, as numbers.
  function changes() {
    const out = {};
    for (const [k] of FIELDS) if (String(form[k]) !== String(data[k])) out[k] = Number(form[k]);
    for (const [g] of GROUPS) {
      const diff = Object.keys(form[g]).some((k) => String(form[g][k]) !== String(data[g][k]));
      if (diff) out[g] = Object.fromEntries(Object.entries(form[g]).map(([k, v]) => [k, Number(v)]));
    }
    return out;
  }

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      const c = changes();
      if (Object.keys(c).length === 0) throw new Error("Nothing has changed.");
      if (Object.values(c).some((v) => typeof v === "number" && Number.isNaN(v))) throw new Error("Please enter numbers only.");
      await updateConfig(c);
      setMessage("Settings saved. They apply to new submissions and decisions.");
      reload();
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
      setAsking(false);
    }
  }

  return (
    <div>
      <h1>Verification settings</h1>
      <p className="muted">
        Prototype rules defined by this project, not validated science. Changes apply to submissions checked
        and decisions made after saving, and are recorded in the audit log.
      </p>
      <Loading loading={loading} error={error} onRetry={reload} />
      {message && <p className="info" role="status">{message}</p>}
      {form && (
        <>
          <div className="card settings">
            {FIELDS.map(([k, label, range]) => (
              <div key={k} className="setting">
                <label htmlFor={k}>{label} <span className="muted small">({range})</span></label>
                <input id={k} type="number" step="any" value={form[k]} onChange={(e) => setField(k, e.target.value)} />
              </div>
            ))}
          </div>
          <div className="grid2">
            {GROUPS.map(([g, title]) => (
              <div className="card" key={g}>
                <h3>{title}</h3>
                {Object.entries(form[g]).map(([k, v]) => (
                  <div key={k} className="setting">
                    <label htmlFor={`${g}-${k}`}>{g === "impact_factors" || g === "max_scale" ? activityLabel(k) : labelOf(k)}</label>
                    <input id={`${g}-${k}`} type="number" step="any" value={v} onChange={(e) => setGroup(g, k, e.target.value)} />
                  </div>
                ))}
              </div>
            ))}
          </div>
          <div className="actions">
            <button className="btn" onClick={() => setAsking(true)}>Save settings</button>
            <button className="btn secondary" onClick={() => setForm(JSON.parse(JSON.stringify(data)))}>Undo changes</button>
          </div>
        </>
      )}
      <ConfirmDialog open={asking} busy={busy} title="Save verification settings?"
                     message="New submissions will be scored with these values." confirmLabel="Save"
                     onConfirm={save} onCancel={() => setAsking(false)} />
    </div>
  );
}

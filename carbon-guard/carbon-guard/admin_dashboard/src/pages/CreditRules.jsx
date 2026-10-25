import { useEffect, useState } from "react";
import { getCreditRules, updateCreditRule } from "../api.js";
import { useLoad } from "../useLoad.js";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import Loading from "../components/Loading.jsx";
import { SCALE_UNITS, activityLabel, fmtDate, num } from "../format.js";

export default function CreditRules() {
  const { data, error, loading, reload } = useLoad(getCreditRules);
  const [rules, setRules] = useState([]);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(null);     // the rule waiting for confirmation
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (data) setRules(data);
  }, [data]);

  const change = (type, field, value) =>
    setRules((all) => all.map((r) => (r.activity_type === type ? { ...r, [field]: value } : r)));

  async function save() {
    const rule = saving;
    setBusy(true);
    setMessage("");
    try {
      const base = parseFloat(rule.base_credit_value);
      const mult = parseFloat(rule.impact_multiplier);
      if (Number.isNaN(base) || Number.isNaN(mult)) throw new Error("Please enter numbers for both values.");
      await updateCreditRule(rule.activity_type, { base_credit_value: base, impact_multiplier: mult, is_active: rule.is_active });
      setMessage(`Saved the rule for ${activityLabel(rule.activity_type)}.`);
      reload();
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
      setSaving(null);
    }
  }

  return (
    <div>
      <h1>Green Credit rules</h1>
      <p className="muted">
        Credits for an approved submission = base value &times; multiplier &times; quantity. These are this project's
        own reward points, not legally recognised carbon credits. Changes apply to future approvals only.
      </p>
      <Loading loading={loading} error={error} onRetry={reload} />
      {message && <p className="info" role="status">{message}</p>}
      <div className="cards rules">
        {rules.map((rule) => (
          <div className="card rule" key={rule.activity_type}>
            <h3>{activityLabel(rule.activity_type)}</h3>
            <label htmlFor={`base-${rule.activity_type}`}>Base credits per {SCALE_UNITS[rule.activity_type]}</label>
            <input id={`base-${rule.activity_type}`} type="number" min="0" step="any" value={rule.base_credit_value}
                   onChange={(e) => change(rule.activity_type, "base_credit_value", e.target.value)} />
            <label htmlFor={`mult-${rule.activity_type}`}>Impact multiplier</label>
            <input id={`mult-${rule.activity_type}`} type="number" min="0" step="any" value={rule.impact_multiplier}
                   onChange={(e) => change(rule.activity_type, "impact_multiplier", e.target.value)} />
            <label className="check">
              <input type="checkbox" checked={rule.is_active}
                     onChange={(e) => change(rule.activity_type, "is_active", e.target.checked)} />
              Rule active (inactive = approvals give 0 credits)
            </label>
            <p className="muted small">
              Example: 10 {SCALE_UNITS[rule.activity_type]} &rarr; {num((parseFloat(rule.base_credit_value) || 0) * (parseFloat(rule.impact_multiplier) || 0) * 10)} credits.
              {rule.updated_by && <> Last changed by {rule.updated_by}, {fmtDate(rule.updated_at)}.</>}
            </p>
            <button className="btn" onClick={() => setSaving(rule)}>Save</button>
          </div>
        ))}
      </div>
      <ConfirmDialog open={!!saving} busy={busy} title="Save this credit rule?"
                     message="Future approvals will use the new values. Earlier awards are not changed. The change is recorded in the audit log."
                     confirmLabel="Save rule" onConfirm={save} onCancel={() => setSaving(null)} />
    </div>
  );
}

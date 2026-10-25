import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { approve, fileUrl, getSubmission, reject, sendToManualReview } from "../api.js";
import { useLoad } from "../useLoad.js";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import Loading from "../components/Loading.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { SCALE_UNITS, activityLabel, fmtDate, labelOf, num } from "../format.js";

function Row({ k, v }) {
  const empty = v === null || v === undefined || v === "";
  return <div className="kv"><span>{k}</span><b>{empty ? "-" : v}</b></div>;
}

const yesNo = (v) => (v === true ? "Yes" : v === false ? "No" : "Unknown");

function Img({ src, alt }) {
  const [failed, setFailed] = useState(false);
  if (!src) return <p className="muted">No image.</p>;
  if (failed) return <p className="muted">The image could not be loaded.</p>;
  return <a href={src} target="_blank" rel="noreferrer"><img className="photo" src={src} alt={alt} onError={() => setFailed(true)} /></a>;
}

const ACTIONS = {
  approve: { fn: approve, title: "Approve this submission?", label: "Approve", danger: false,
    message: "The user receives Green Credits and +5 Trust Score. This cannot be undone." },
  reject: { fn: reject, title: "Reject this submission?", label: "Reject", danger: true,
    message: "The user loses Trust Score (more if the submission was flagged). You can reopen it later." },
  review: { fn: sendToManualReview, title: "Send to manual review?", label: "Send to manual review", danger: false,
    message: "Moves the submission to the manual review queue. A rejected submission is reopened and its penalty refunded." },
};

export default function SubmissionDetail() {
  const { id } = useParams();
  const { data: s, error, loading, reload } = useLoad(() => getSubmission(id), [id]);
  const [dialog, setDialog] = useState(null);     // "approve" | "reject" | "review" | null
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [done, setDone] = useState("");

  // While the backend is still checking the submission, refresh every 3 seconds.
  useEffect(() => {
    if (!s || s.status !== "processing") return undefined;
    const t = setTimeout(reload, 3000);
    return () => clearTimeout(t);
  }, [s, reload]);

  async function confirm(notes) {
    const action = ACTIONS[dialog];
    setBusy(true);
    setActionError("");
    try {
      const updated = await action.fn(id, notes);
      setDone(`Done: the submission is now "${labelOf(updated.status)}".`);
      setDialog(null);
      reload();
    } catch (e) {
      setActionError(e.message);
      setDialog(null);
    } finally {
      setBusy(false);
    }
  }

  if (loading && !s) return <Loading loading />;
  if (error) return <Loading error={error} onRetry={reload} />;
  if (!s) return null;

  const { lat, lng, accuracy_m: acc } = s.gps;
  const d = 0.005;
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${lng - d}%2C${lat - d}%2C${lng + d}%2C${lat + d}&layer=mapnik&marker=${lat}%2C${lng}`;
  const ai = s.ai_verification;
  const loc = s.location_verification;
  const sat = s.satellite_verification;
  const fraud = s.fraud_check;
  const canDecide = s.status === "pending" || s.status === "manual_review";

  return (
    <div>
      <p><Link to="/submissions">&larr; Back to submissions</Link></p>
      <div className="title-row">
        <h1>{activityLabel(s.activity_type)} <StatusBadge status={s.status} /></h1>
        <span className="muted small">#{s.id}</span>
      </div>

      <div className="card actions sticky-actions">
        {canDecide && (
          <>
            <button className="btn" onClick={() => setDialog("approve")}>Approve</button>
            <button className="btn danger" onClick={() => setDialog("reject")}>Reject</button>
            {s.status === "pending" && (
              <button className="btn secondary" onClick={() => setDialog("review")}>Send to manual review</button>
            )}
          </>
        )}
        {s.status === "rejected" && (
          <button className="btn secondary" onClick={() => setDialog("review")}>Reopen for manual review</button>
        )}
        {s.status === "verified" && <span className="muted">Verified by {s.reviewed_by}. No further action.</span>}
        {s.status === "processing" && <span className="muted">Automatic checks are still running. This page refreshes itself.</span>}
        {done && <span className="info">{done}</span>}
        {actionError && <span className="error">{actionError}</span>}
      </div>

      {s.processing_error && <div className="alert error">{s.processing_error}</div>}
      {fraud && fraud.flags.length > 0 && (
        <div className="alert warn">
          <b>Flagged for review.</b> These signals ask for a human check; they are not proof of fraud.
          <ul>{fraud.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
          {s.related_submission_ids.length > 0 && (
            <p className="small">Compare with: {s.related_submission_ids.map((rid) => (
              <Link key={rid} to={`/submissions/${rid}`} className="related">#{rid.slice(-6)}</Link>))}</p>
          )}
        </div>
      )}

      <div className="grid2">
        <div className="card">
          <h3>Submitted photo</h3>
          <Img src={fileUrl(s.image_url)} alt="Photo submitted by the user" />
        </div>
        <div className="card">
          <h3>Location</h3>
          <Row k="Latitude, longitude" v={`${lat}, ${lng}`} />
          <Row k="GPS accuracy" v={acc != null ? `${num(acc, 0)} m` : "not reported"} />
          <Row k="Address (OpenStreetMap)" v={loc?.address || (loc ? labelOf(loc.geocoding_status) : null)} />
          <iframe className="map" title="Submission location map" src={mapUrl} loading="lazy" />
        </div>
      </div>

      <div className="grid2">
        <div className="card">
          <h3>Submission</h3>
          <Row k="User" v={<Link to={`/users/${s.user_id}`}>{s.user_name || s.user_email}</Link>} />
          <Row k="Email" v={s.user_email} />
          <Row k="User Trust Score" v={num(s.user_trust_score, 1)} />
          <Row k="Activity" v={activityLabel(s.activity_type)} />
          <Row k="Quantity" v={`${num(s.scale_value)} ${SCALE_UNITS[s.activity_type] || ""}`} />
          <Row k="Description" v={s.description} />
          <Row k="Submitted" v={fmtDate(s.created_at)} />
          <Row k="Reviewed by" v={s.reviewed_by} />
          <Row k="Review notes" v={s.review_notes} />
        </div>
        <div className="card">
          <h3>Verification score: {num(s.verification_score, 1)} / 100</h3>
          {Object.entries(s.score_components || {}).map(([k, v]) => <Row key={k} k={labelOf(k)} v={`${num(v, 1)} points`} />)}
          <Row k="Green Credits awarded" v={num(s.green_credits_awarded)} />
          <Row k="CO2 estimate" v={s.environmental_impact?.co2_estimate != null ? `${num(s.environmental_impact.co2_estimate)} kg/year` : null} />
          <h3 className="spaced">Why</h3>
          <ul className="reasons">{(s.decision_reasons || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
        </div>
      </div>

      <div className="grid3">
        <div className="card">
          <h3>AI image check</h3>
          {!ai ? <p className="muted">Not run yet.</p> : (
            <>
              <Row k="Status" v={labelOf(ai.status)} />
              <Row k="Model" v={ai.model} />
              <Row k="Predicted" v={ai.predicted_class ? labelOf(ai.predicted_class) : null} />
              <Row k="Confidence" v={ai.confidence != null ? `${num(ai.confidence * 100, 1)}%` : null} />
              <Row k="Matches claim" v={yesNo(ai.matched)} />
              {ai.warnings.map((w, i) => <p key={i} className="note">{w}</p>)}
              <p className="muted small">AI output is one signal. It cannot prove that the activity happened.</p>
            </>
          )}
        </div>
        <div className="card">
          <h3>Satellite evidence</h3>
          {!sat ? <p className="muted">Not run yet.</p> : (
            <>
              <Row k="Status" v={labelOf(sat.status)} />
              <Row k="Source" v={sat.source} />
              <Row k="Image date" v={sat.acquisition_date} />
              <Row k="Cloud cover" v={sat.cloud_cover != null ? `${num(sat.cloud_cover, 1)}%` : null} />
              <Row k="Mean NDVI" v={sat.ndvi_mean != null ? num(sat.ndvi_mean, 3) : null} />
              <Row k="Supports claim" v={yesNo(sat.supports_claim)} />
              {sat.image_url && <Img src={fileUrl(sat.image_url)} alt="Satellite image of the area" />}
              {sat.notes.map((n, i) => <p key={i} className="note">{n}</p>)}
            </>
          )}
        </div>
        <div className="card">
          <h3>GPS and duplicate checks</h3>
          {!loc || !fraud ? <p className="muted">Not run yet.</p> : (
            <>
              <Row k="GPS valid" v={yesNo(loc.gps_valid)} />
              <Row k="Accuracy acceptable" v={yesNo(loc.accuracy_ok)} />
              <Row k="Duplicate / similar image" v={yesNo(fraud.is_duplicate_image)} />
              <Row k="Nearby earlier submissions" v={yesNo(fraud.is_duplicate_location)} />
              <Row k="Suspicious pattern" v={yesNo(fraud.suspicious_pattern)} />
              {loc.notes.map((n, i) => <p key={i} className="note">{n}</p>)}
              <p className="muted small">Valid coordinates are not proof of location; GPS can be faked.</p>
            </>
          )}
        </div>
      </div>

      {dialog && (
        <ConfirmDialog open title={ACTIONS[dialog].title} message={ACTIONS[dialog].message}
                       confirmLabel={ACTIONS[dialog].label} danger={ACTIONS[dialog].danger} withNotes busy={busy}
                       onConfirm={confirm} onCancel={() => setDialog(null)} />
      )}
    </div>
  );
}

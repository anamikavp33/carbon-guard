import { useEffect, useRef, useState } from "react";

// A modal asking "are you sure?" before an important action, with an optional note field.
// Usage: <ConfirmDialog open title="Approve?" message="..." confirmLabel="Approve"
//          withNotes onConfirm={(notes) => ...} onCancel={() => ...} />
export default function ConfirmDialog({
  open, title, message, confirmLabel = "Confirm", danger = false, withNotes = false, busy = false,
  onConfirm, onCancel,
}) {
  const [notes, setNotes] = useState("");
  const cancelRef = useRef(null);

  useEffect(() => {
    if (open) {
      setNotes("");
      cancelRef.current && cancelRef.current.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && !busy && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={() => !busy && onCancel()}>
      <div className="modal card" role="dialog" aria-modal="true" aria-labelledby="confirm-title"
           onClick={(e) => e.stopPropagation()}>
        <h3 id="confirm-title">{title}</h3>
        <p>{message}</p>
        {withNotes && (
          <>
            <label htmlFor="confirm-notes">Note for the user (optional)</label>
            <textarea id="confirm-notes" rows={3} maxLength={1000} value={notes}
                      onChange={(e) => setNotes(e.target.value)} />
          </>
        )}
        <div className="actions end">
          <button ref={cancelRef} className="btn secondary" disabled={busy} onClick={onCancel}>Cancel</button>
          <button className={`btn ${danger ? "danger" : ""}`} disabled={busy} onClick={() => onConfirm(notes.trim())}>
            {busy ? "Working..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

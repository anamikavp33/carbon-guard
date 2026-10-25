export default function Loading({ loading, error, onRetry }) {
  if (loading) return <p className="muted" role="status">Loading...</p>;
  if (error)
    return (
      <div className="alert error" role="alert">
        <span>{error}</span>
        {onRetry && <button className="btn secondary small" onClick={onRetry}>Try again</button>}
      </div>
    );
  return null;
}

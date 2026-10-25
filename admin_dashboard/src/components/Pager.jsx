// Previous / next buttons for a page of results: { items, total, skip, limit }.
export default function Pager({ page, onSkip }) {
  if (!page || page.total <= page.limit) return null;
  const from = page.total === 0 ? 0 : page.skip + 1;
  const to = Math.min(page.skip + page.limit, page.total);
  return (
    <div className="pager">
      <button className="btn secondary small" disabled={page.skip === 0}
              onClick={() => onSkip(Math.max(0, page.skip - page.limit))}>Previous</button>
      <span className="muted small">{from}-{to} of {page.total}</span>
      <button className="btn secondary small" disabled={to >= page.total}
              onClick={() => onSkip(page.skip + page.limit)}>Next</button>
    </div>
  );
}

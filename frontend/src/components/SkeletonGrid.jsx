export default function SkeletonGrid() {
  return (
    <section className="results">
      <div className="skeleton-grid">
        {Array.from({ length: 12 }).map((_, i) => (
          <div className="track-card track-card--skeleton" key={i}>
            <div className="track-thumb" />
            <div className="track-info">
              <div className="skeleton-line skeleton-line--title" />
              <div className="skeleton-line skeleton-line--artist" />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

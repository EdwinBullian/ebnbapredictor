export default function SkeletonLoader() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="bg-tv-green-bg/30 border border-tv-green/10 rounded-lg h-16" />
      <div className="bg-tv-bg-secondary border border-tv-border rounded-lg">
        <div className="h-10 border-b border-tv-border bg-tv-bg-tertiary/30 rounded-t-lg" />
        {[...Array(8)].map((_, i) => (
          <div key={i} className="h-12 border-b border-tv-border/30 mx-4">
            <div className="h-3 bg-tv-bg-tertiary rounded w-3/4 mt-4" />
          </div>
        ))}
      </div>
    </div>
  );
}

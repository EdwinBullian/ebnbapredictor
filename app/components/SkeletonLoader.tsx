export default function SkeletonLoader() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="bg-bg-surface border border-t-green/10 h-16" />
      <div className="bg-bg-surface border border-border-default">
        <div className="h-10 border-b border-border-bright bg-bg-header" />
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className="h-11 border-b border-border-default px-4 flex items-center"
          >
            <div className="h-3 bg-bg-elevated w-3/4" />
          </div>
        ))}
      </div>
    </div>
  );
}

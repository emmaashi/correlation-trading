function SkeletonBlock({ className }: { className: string }) {
  return <div className={`skeleton-shimmer rounded ${className}`} />;
}

export default function PairExplorerSkeleton() {
  return (
    <main
      role="status"
      aria-label="Loading Pair Explorer"
      aria-busy="true"
      className="mx-6 min-h-screen bg-black text-neutral-50 sm:mx-0"
    >
      <span className="sr-only">Loading Pair Explorer</span>
      <div className="mx-auto min-h-[calc(100vh-68px)] max-w-6xl px-4 pb-8 sm:px-6">
        <div className="space-y-6 pt-6 sm:pt-8">
          <header className="flex flex-col items-center">
            <SkeletonBlock className="h-10 w-56 sm:w-72" />
            <SkeletonBlock className="mt-4 h-4 w-full max-w-xl" />
            <SkeletonBlock className="mt-2 h-4 w-64 max-w-[75%]" />
          </header>

          <div className="mx-auto flex w-full max-w-2xl gap-2">
            <SkeletonBlock className="h-9 min-w-0 flex-1" />
            <SkeletonBlock className="h-9 w-24" />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 15 }, (_, index) => (
              <div
                key={index}
                className="h-[86px] rounded-lg border border-white/[0.08] bg-white/[0.02] p-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <SkeletonBlock className="h-4 w-4/5" />
                    <div className="mt-3 flex gap-1.5">
                      <SkeletonBlock className="h-5 w-12" />
                      <SkeletonBlock className="h-5 w-12" />
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <SkeletonBlock className="h-5 w-16 rounded-full" />
                    <SkeletonBlock className="h-3 w-14" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}

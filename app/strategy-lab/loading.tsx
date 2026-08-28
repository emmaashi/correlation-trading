import StrategyLabSkeleton from "@/components/strategy/StrategyLabSkeleton";

export default function LoadingStrategyLab() {
  return (
    <main className="min-h-screen bg-black text-neutral-50">
      <div className="mx-auto min-h-[calc(100vh-68px)] max-w-7xl px-4 pb-8 sm:px-6">
        <StrategyLabSkeleton />
      </div>
    </main>
  );
}

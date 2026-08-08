import ResearchNav from "@/components/strategy/ResearchNav";
import StrategyLab from "@/components/strategy/StrategyLab";

export default function StrategyLabPage() {
  return (
    <main className="min-h-screen bg-black text-neutral-50">
      <div className="mx-auto min-h-screen max-w-7xl px-4 py-8 sm:px-6">
        <ResearchNav />
        <StrategyLab />
      </div>
    </main>
  );
}

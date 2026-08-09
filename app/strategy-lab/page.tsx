import StrategyLab from "@/components/strategy/StrategyLab";

type SearchParams = Record<string, string | string[] | undefined>;

function queryValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default function StrategyLabPage({ searchParams }: { searchParams: SearchParams }) {
  const tickers = (queryValue(searchParams.universe) ?? "")
    .split(",")
    .map((ticker) => ticker.trim().toUpperCase())
    .filter(Boolean);

  return (
    <main className="min-h-screen bg-black text-neutral-50">
      <div className="mx-auto min-h-[calc(100vh-68px)] max-w-7xl px-4 pb-8 sm:px-6">
        <StrategyLab
          initialState={{
            groupId: queryValue(searchParams.group),
            tickers,
            start: queryValue(searchParams.start),
            end: queryValue(searchParams.end),
          }}
        />
      </div>
    </main>
  );
}

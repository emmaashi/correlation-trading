import StrategyLab from "@/components/strategy/StrategyLab";

type SearchParams = Record<string, string | string[] | undefined>;

function queryValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function StrategyLabPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const resolvedSearchParams = await searchParams;
  const tickers = (queryValue(resolvedSearchParams.universe) ?? "")
    .split(",")
    .map((ticker) => ticker.trim().toUpperCase())
    .filter(Boolean);

  return (
    <main className="min-h-screen bg-black text-neutral-50">
      <div className="mx-auto min-h-[calc(100vh-68px)] max-w-7xl px-4 pb-8 sm:px-6">
        <StrategyLab
          initialState={{
            groupId: queryValue(resolvedSearchParams.group),
            tickers,
            start: queryValue(resolvedSearchParams.start),
            end: queryValue(resolvedSearchParams.end),
          }}
        />
      </div>
    </main>
  );
}

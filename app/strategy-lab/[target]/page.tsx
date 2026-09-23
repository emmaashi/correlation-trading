import StrategyCandidateDetail from "@/components/strategy/StrategyCandidateDetail";
import { todayISO, yearsAgoISO } from "@/lib/dateUtils";

type SearchParams = Record<string, string | string[] | undefined>;

function queryValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function tickerList(value: string | undefined) {
  return Array.from(
    new Set(
      (value ?? "")
        .split(",")
        .map((ticker) => ticker.trim().toUpperCase())
        .filter(Boolean)
    )
  );
}

export default async function StrategyCandidatePage({
  params,
  searchParams,
}: {
  params: Promise<{ target: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const [resolvedParams, resolvedSearchParams] = await Promise.all([
    params,
    searchParams,
  ]);
  const target = decodeURIComponent(resolvedParams.target).toUpperCase();
  const peers = tickerList(queryValue(resolvedSearchParams.peers));
  const universe = tickerList(queryValue(resolvedSearchParams.universe));
  const start = queryValue(resolvedSearchParams.start) ?? yearsAgoISO(5);
  const end = queryValue(resolvedSearchParams.end) ?? todayISO();

  const backQuery = new URLSearchParams({ start, end });
  const group = queryValue(resolvedSearchParams.group);
  if (group) backQuery.set("group", group);
  if (universe.length) backQuery.set("universe", universe.join(","));

  return (
    <main className="min-h-screen bg-black text-neutral-50">
      <div className="mx-auto min-h-[calc(100vh-68px)] max-w-7xl px-4 pb-8 sm:px-6">
        <StrategyCandidateDetail
          target={target}
          peers={peers}
          start={start}
          end={end}
          backHref={`/strategy-lab?${backQuery.toString()}`}
        />
      </div>
    </main>
  );
}

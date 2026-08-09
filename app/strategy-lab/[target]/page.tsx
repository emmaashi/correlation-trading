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

export default function StrategyCandidatePage({
  params,
  searchParams,
}: {
  params: { target: string };
  searchParams: SearchParams;
}) {
  const target = decodeURIComponent(params.target).toUpperCase();
  const peers = tickerList(queryValue(searchParams.peers));
  const universe = tickerList(queryValue(searchParams.universe));
  const start = queryValue(searchParams.start) ?? yearsAgoISO(5);
  const end = queryValue(searchParams.end) ?? todayISO();

  const backQuery = new URLSearchParams({ start, end });
  const group = queryValue(searchParams.group);
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

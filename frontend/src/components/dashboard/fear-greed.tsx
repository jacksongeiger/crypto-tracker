import { fetchFearGreed } from "@/lib/data-sources/fearGreed";
import type { FearGreedPoint } from "@/lib/data-sources/fearGreed";
import { ErrorCard } from "./error-card";

function classifyColor(v: number): string {
  if (v < 25) return "#DF5F67"; // danger
  if (v < 45) return "#F0B90B"; // warning
  if (v < 55) return "#8A8F98"; // neutral
  if (v < 75) return "#3F8AE0"; // mid blue
  return "#0052FF"; // brand
}

function Gauge({ value }: { value: number }) {
  // Half-donut: 180deg arc, value-fraction stroke
  const radius = 64;
  const stroke = 14;
  const cx = 90;
  const cy = 80;
  const startAngle = Math.PI; // 180
  const endAngle = 2 * Math.PI; // 360 (i.e. 0 = right)
  function polar(angle: number) {
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    };
  }
  // arc helpers
  function arcPath(startA: number, endA: number) {
    const s = polar(startA);
    const e = polar(endA);
    const large = endA - startA > Math.PI ? 1 : 0;
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${large} 1 ${e.x} ${e.y}`;
  }
  const total = endAngle - startAngle;
  const fillAngle = startAngle + total * (value / 100);
  const color = classifyColor(value);
  return (
    <svg
      width={180}
      height={104}
      viewBox="0 0 180 104"
      role="img"
      aria-label={`Fear & Greed gauge at ${value}`}
    >
      <path
        d={arcPath(startAngle, endAngle)}
        stroke="#EAECF0"
        strokeWidth={stroke}
        fill="none"
        strokeLinecap="round"
      />
      <path
        d={arcPath(startAngle, fillAngle)}
        stroke={color}
        strokeWidth={stroke}
        fill="none"
        strokeLinecap="round"
      />
      <text
        x={cx}
        y={cy + 4}
        textAnchor="middle"
        fontFamily="var(--font-mono)"
        fontWeight={600}
        fontSize={26}
        fill="#0A0B0D"
      >
        {value}
      </text>
    </svg>
  );
}

function MiniChart({ points }: { points: FearGreedPoint[] }) {
  const width = 280;
  const height = 60;
  if (points.length < 2) return null;
  const values = points.map((p) => p.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 100);
  const range = max - min || 1;
  const step = width / (points.length - 1);
  const path = values
    .map((v, i) => {
      const x = i * step;
      const y = height - ((v - min) / range) * height;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
  // Area fill from path to baseline
  const lastX = (values.length - 1) * step;
  const fillPath = `${path} L ${lastX.toFixed(2)} ${height} L 0 ${height} Z`;
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="30-day Fear & Greed history"
      className="block w-full"
      preserveAspectRatio="none"
    >
      <path d={fillPath} fill="rgba(0,82,255,0.08)" />
      <path
        d={path}
        fill="none"
        stroke="var(--brand-500)"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export async function FearGreedCard() {
  let data;
  try {
    data = await fetchFearGreed();
  } catch {
    return <ErrorCard title="Fear & Greed" />;
  }
  const { current, history } = data;
  return (
    <section className="rounded-md border border-line bg-surface p-6 sm:p-7">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-caption uppercase text-ink-subtle">
            Fear &amp; Greed Index
          </div>
          <div className="mt-1 text-h3 font-semibold text-ink">
            {current.classification}
          </div>
        </div>
        <span className="font-mono text-caption uppercase text-ink-subtle">
          alternative.me
        </span>
      </div>
      <div className="mt-4 flex flex-col items-center gap-2 sm:flex-row sm:items-center sm:gap-6">
        <Gauge value={current.value} />
        <p className="max-w-sm text-bodySm text-ink-muted">
          An aggregate of volatility, momentum, social sentiment, and BTC
          dominance signals. 0 is extreme fear, 100 is extreme greed.
        </p>
      </div>
      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
          <span>30-day trend</span>
          <span className="tabular-nums">
            min {Math.min(...history.map((p) => p.value))} · max{" "}
            {Math.max(...history.map((p) => p.value))}
          </span>
        </div>
        <MiniChart points={history} />
      </div>
    </section>
  );
}

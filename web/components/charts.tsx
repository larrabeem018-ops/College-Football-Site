"use client";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const tip = { contentStyle: { background: "#121820", border: "1px solid #243040", borderRadius: 10, color: "#E8EDF2", fontSize: 13 }, itemStyle: { color: "#E8EDF2" }, labelStyle: { color: "#AEB8C4", fontWeight: 700 }, cursor: { fill: "#ffffff0d" } };
const axis = { stroke: "#243040", tick: { fill: "#8D99A8", fontSize: 12 }, tickLine: false };
const C = { green: "#2FD27A", blue: "#5AA9F0", red: "#F2766B", amber: "#F5B83D", muted: "#5B6878" };

export function ProductionChart({ data }: { data: { pos: string; returning: number; lost: number; incoming: number }[] }) {
  const rows = data.map((d) => ({ pos: d.pos, Returning: Math.round(d.returning), Incoming: Math.round(d.incoming), Lost: -Math.round(d.lost) }));
  return (
    <ResponsiveContainer width="100%" height={360}>
      <BarChart data={rows} stackOffset="sign" margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="pos" {...axis} />
        <YAxis {...axis} width={56} />
        <Tooltip {...tip} formatter={(v: number, n: string) => [Math.abs(v).toLocaleString(), n]} />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <ReferenceLine y={0} stroke="#3A4756" />
        <Bar dataKey="Returning" stackId="a" fill={C.green} radius={[0, 0, 0, 0]} />
        <Bar dataKey="Incoming" stackId="a" fill={C.blue} radius={[4, 4, 0, 0]} />
        <Bar dataKey="Lost" stackId="a" fill={C.red} radius={[0, 0, 4, 4]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function SimpleBars({ data, height = 260, color = C.green, signed = false, valueLabel = "Value" }: { data: { label: string; value: number }[]; height?: number; color?: string; signed?: boolean; valueLabel?: string }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="label" {...axis} interval={0} angle={data.length > 10 ? -40 : 0} textAnchor={data.length > 10 ? "end" : "middle"} height={data.length > 10 ? 70 : 30} />
        <YAxis {...axis} width={48} />
        <Tooltip {...tip} formatter={(v: number) => [v.toLocaleString(undefined, { maximumFractionDigits: 1 }), valueLabel]} />
        {signed && <ReferenceLine y={0} stroke="#3A4756" />}
        <Bar dataKey="value" radius={[4, 4, 4, 4]}>
          {data.map((d, i) => <Cell key={i} fill={signed ? (d.value >= 0 ? C.green : C.red) : color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function HBars({ data, height, onPick, format = (v: number) => v.toFixed(1), selected }: { data: { label: string; value: number; key: string }[]; height?: number; onPick?: (key: string) => void; format?: (v: number) => string; selected?: string[] }) {
  return (
    <ResponsiveContainer width="100%" height={height ?? Math.max(260, data.length * 32 + 40)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 4 }}>
        <XAxis type="number" {...axis} hide />
        <YAxis type="category" dataKey="label" {...axis} width={210} tick={{ fill: "#E8EDF2", fontSize: 13 }} />
        <Tooltip {...tip} formatter={(v: number) => [format(v), "Value"]} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} cursor={onPick ? "pointer" : undefined} onClick={(d: any) => onPick?.(d.key)}
          label={{ position: "right", fill: "#AEB8C4", fontSize: 12, formatter: (v: number) => format(v) }}>
          {data.map((d) => <Cell key={d.key} fill={selected?.includes(d.key) ? C.amber : C.green} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function UnitsLine({ series }: { series: { name: string; color: string; dash?: string; points: { week: number; units: number }[] }[] }) {
  const weeks = [...new Set(series.flatMap((s) => s.points.map((p) => p.week)))].sort((a, b) => a - b);
  const rows = weeks.map((w) => {
    const r: Record<string, number | null> = { week: w };
    for (const s of series) r[s.name] = s.points.find((p) => p.week === w)?.units ?? null;
    return r;
  });
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={rows} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="week" {...axis} tickFormatter={(w) => `Wk ${w}`} />
        <YAxis {...axis} width={48} />
        <Tooltip {...tip} labelFormatter={(w) => `Week ${w}`} formatter={(v: number, n: string) => [`${v > 0 ? "+" : ""}${v.toFixed(1)} units`, n]} />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <ReferenceLine y={0} stroke="#3A4756" />
        {series.map((s) => <Line key={s.name} type="monotone" dataKey={s.name} stroke={s.color} strokeWidth={s.dash ? 2 : 3} strokeDasharray={s.dash} dot={{ r: 3 }} connectNulls />)}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function QbrLine({ data, color = C.green }: { data: { label: string; qbr: number | null }[]; color?: string }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="label" {...axis} interval={0} tick={{ fill: "#8D99A8", fontSize: 11 }} />
        <YAxis {...axis} width={36} domain={[0, 100]} />
        <Tooltip {...tip} formatter={(v: number) => [v?.toFixed(1), "QBR"]} />
        <Line type="monotone" dataKey="qbr" stroke={color} strokeWidth={3} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function QbRadar({ a, b }: { a: { name: string; values: Record<string, number | null> }; b: { name: string; values: Record<string, number | null> } }) {
  const labels: Record<string, string> = { att: "Attempts", qbr: "QBR", yds: "Pass yards", td: "TD", int: "INT (fewer = better)" };
  const rows = Object.keys(labels).map((k) => ({ metric: labels[k], [a.name]: a.values[k] ?? 0, [b.name]: b.values[k] ?? 0 }));
  return (
    <ResponsiveContainer width="100%" height={380}>
      <RadarChart data={rows} outerRadius="72%">
        <PolarGrid stroke="#243040" />
        <PolarAngleAxis dataKey="metric" tick={{ fill: "#E8EDF2", fontSize: 13 }} />
        <PolarRadiusAxis domain={[0, 100]} tick={{ fill: "#5B6878", fontSize: 10 }} axisLine={false} />
        <Radar name={b.name} dataKey={b.name} stroke={C.blue} fill={C.blue} fillOpacity={0.2} strokeWidth={2.5} />
        <Radar name={a.name} dataKey={a.name} stroke={C.green} fill={C.green} fillOpacity={0.25} strokeWidth={2.5} />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <Tooltip {...tip} formatter={(v: number) => [Math.round(v), "Score (0–100)"]} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

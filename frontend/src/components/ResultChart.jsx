import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

export default function ResultChart({ outputType, chart }) {
  if (!chart) return null;

  const data = chart.x.map((label, idx) => ({
    label,
    value: chart.series[idx]
  }));

  const title = chart.title ?? "";
  const seriesLabel = chart.series_label ?? "Value";
  const isRevenueSeries =
    seriesLabel.toLowerCase().includes("revenue") ||
    title.toLowerCase().includes("revenue");

  const useLine = outputType === "line_chart";

  return (
    <div style={{ marginTop: 14 }}>
      <div className="sectionTitle">{title || "Chart"}</div>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          {useLine ? (
            <LineChart data={data}>
              <CartesianGrid stroke="rgba(0,0,0,0.08)" />
              <XAxis dataKey="label" tick={{ fill: "rgba(17,24,39,0.65)" }} />
              <YAxis
                tick={{ fill: "rgba(17,24,39,0.65)" }}
                tickFormatter={(v) => formatTick(v, isRevenueSeries)}
              />
              <Tooltip
                contentStyle={{ background: "#ffffff", borderColor: "rgba(0,0,0,0.12)" }}
                labelStyle={{ color: "rgba(17,24,39,0.9)" }}
                formatter={(value) => formatTooltipValue(value, isRevenueSeries)}
              />
              <Line type="monotone" dataKey="value" strokeWidth={2} name={seriesLabel} stroke="#F41573" dot={{ r: 3, fill: "#F41573" }} />
            </LineChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid stroke="rgba(0,0,0,0.08)" />
              <XAxis dataKey="label" tick={{ fill: "rgba(17,24,39,0.65)" }} />
              <YAxis
                tick={{ fill: "rgba(17,24,39,0.65)" }}
                tickFormatter={(v) => formatTick(v, isRevenueSeries)}
              />
              <Tooltip
                contentStyle={{ background: "#ffffff", borderColor: "rgba(0,0,0,0.12)" }}
                labelStyle={{ color: "rgba(17,24,39,0.9)" }}
                formatter={(value) => formatTooltipValue(value, isRevenueSeries)}
              />
              <Bar dataKey="value" fill="#F41573" radius={[6, 6, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function formatTick(v, isRevenueSeries) {
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  if (!isRevenueSeries) return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  });
}

function formatTooltipValue(v, isRevenueSeries) {
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  if (!isRevenueSeries) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  });
}


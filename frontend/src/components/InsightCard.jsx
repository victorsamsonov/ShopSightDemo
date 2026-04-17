import React from "react";

export default function InsightCard({ kpi, insight }) {
  return (
    <div>
      <div className="insightTitle">Insight</div>
      <div className="subtle" style={{ marginBottom: 12, lineHeight: 1.5 }}>
        {insight}
      </div>

      {kpi ? (
        <div className="kpiGrid">
          <div className="kpiCard">
            <div className="kpiLabel">{kpi.label}</div>
            <div className="kpiValue">
              {String(kpi.unit || "").toUpperCase() === "USD" || String(kpi.unit || "") === "$"
                ? formatCurrency(kpi.value)
                : kpi.unit
                  ? `${formatNumber(kpi.value)} ${kpi.unit}`
                  : formatNumber(kpi.value)}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function formatNumber(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatCurrency(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  });
}


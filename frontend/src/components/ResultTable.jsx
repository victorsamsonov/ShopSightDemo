import React from "react";

export default function ResultTable({ table }) {
  if (!table || !table.columns || !table.rows) return null;

  return (
    <div style={{ marginTop: 14 }}>
      <div className="sectionTitle">Ranked result</div>
      <div className="tableWrap" style={{ maxHeight: 320 }}>
        <table>
          <thead>
            <tr>
              {table.columns.map((c, idx) => (
                <th key={idx}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((r, ridx) => (
              <tr key={ridx}>
                {r.map((cell, cidx) => (
                  <td key={cidx}>{formatCell(cell, table.columns[cidx])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatCell(v, columnName = "") {
  const col = String(columnName || "").toLowerCase();
  const isCurrency = col.includes("revenue") || col.includes("price") || col.includes("amount");

  if (typeof v === "number") {
    if (isCurrency) {
      return formatCurrency(v);
    }
    return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(v);
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


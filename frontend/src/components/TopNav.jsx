import React from "react";

const items = ["Connectors", "Tables", "Graphs", "Predictive Queries", "Batch Predictions", "Admin"];

export default function TopNav() {
  return (
    <div className="topNav">
      <div className="navInner">
        <div className="navBrand">
          <div className="navLogo" />
          <div className="navBrandText">kumo</div>
        </div>

        <div className="navLinks" aria-label="Navigation">
          {items.map((t) => (
            <div key={t} className="navLink">
              {t}
            </div>
          ))}
        </div>

        <div className="navUser" aria-label="User">
          <div className="navAvatar" />
        </div>
      </div>
    </div>
  );
}


import React from "react";
import { useNavigate } from "react-router-dom";

export default function IntroPage() {
  const navigate = useNavigate();

  return (
    <div className="introWrap">
      <div className="container">
        <div className="heroCard introHero">
          <div className="introTitle">ShopSight</div>
          <div className="insightTitle" style={{ textAlign: "center" }}></div>
          <div className="subtle introSubtitle" style={{ textAlign: "center", maxWidth: 1020, margin: "0 auto", fontSize: "22px" }}>
          Turn natural language into transaction insights
          </div>

          <div className="introActions">
            <button className="btn btnLarge" onClick={() => navigate("/chat")}>
              Get started
            </button>
            <div className="subtle" style={{ alignSelf: "center" }}>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


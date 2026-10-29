import React from "react";

const CLASS_FOR = {
  Beginner: "badge-beginner",
  Exploring: "badge-exploring",
  Practitioner: "badge-practitioner",
  Leader: "badge-leader",
};

// Maturity level badge; anything unknown (e.g. "Not assessed") renders neutral.
export default function Badge({ level }) {
  return <span className={`badge ${CLASS_FOR[level] || "badge-neutral"}`}>{level}</span>;
}

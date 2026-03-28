import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import type { Score } from "../../types";

interface Props { score: Score; }

export default function ScoreBreakdown({ score }: Props) {
  const data = [
    { category: "Financial", score: score.financial_score },
    { category: "Legal", score: score.legal_score },
    { category: "Landlord", score: score.landlord_score },
    { category: "Market", score: score.market_score },
    { category: "Condition", score: score.condition_score },
  ];

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {data.map((d) => (
          <div key={d.category} style={{ flex: 1, minWidth: 80, background: "var(--surface2)", borderRadius: "var(--radius)", padding: "10px 12px", textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>{d.category}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: d.score >= 60 ? "var(--red)" : d.score >= 40 ? "var(--orange)" : "var(--text)" }}>
              {Math.round(d.score)}
            </div>
          </div>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <RadarChart data={data}>
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis dataKey="category" tick={{ fill: "var(--muted)", fontSize: 11 }} />
          <Radar name="Score" dataKey="score" stroke="#5c6ef8" fill="#5c6ef8" fillOpacity={0.25} />
          <Tooltip
            contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 }}
            formatter={(v: number) => [Math.round(v), "Score"]}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

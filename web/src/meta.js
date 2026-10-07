// Labels, colours and small formatting helpers shared by the views

export const TYPES = {
  "project-rules": { label: "Project rules", color: "var(--accent)" },
  memory: { label: "Memory", color: "var(--blue)" },
  skill: { label: "Skills", color: "var(--green)" },
  agent: { label: "Agent prompts", color: "var(--purple)" },
  index: { label: "Index", color: "var(--muted)" },
};

export const typeInfo = t => TYPES[t] ?? { label: t, color: "var(--muted)" };

export function areaName(schema, area) {
  if (!area) return "No area";
  for (const p of Object.values(schema?.phases ?? {})) {
    if (p.areas[area]) return p.areas[area];
  }
  return area;
}

export function areaOptions(schema) {
  return Object.values(schema?.phases ?? {}).flatMap(p =>
    Object.entries(p.areas).map(([id, name]) => ({ id, name, phase: p.name })));
}

export function timeAgo(iso) {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  const steps = [[60, "s"], [3600, "min", 60], [86400, "h", 3600], [86400 * 30, "d", 86400],
    [86400 * 365, "mo", 86400 * 30], [Infinity, "y", 86400 * 365]];
  for (const [limit, unit, div = 1] of steps) {
    if (s < limit) return `${Math.max(1, Math.floor(s / div))}${unit} ago`;
  }
  return "";
}

export const fmtTokens = n => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`);

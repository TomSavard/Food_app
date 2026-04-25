/**
 * Tiny quantity parser + aggregator for shopping-list contributions.
 *
 * Goal: when every contribution can be parsed AND lives in the same unit
 * family (g/kg/mg, ml/cl/l, plain count, plain unitless), produce a single
 * pretty total. Otherwise fall back to a count of contributions.
 */

type Unit =
  | "g" | "kg" | "mg"
  | "ml" | "cl" | "l"
  | "pcs" | "_unitless";

type Family = "weight" | "volume" | "pcs" | "_unitless";

const UNIT_TO_BASE: Record<Unit, { family: Family; toBase: number }> = {
  g: { family: "weight", toBase: 1 },
  kg: { family: "weight", toBase: 1000 },
  mg: { family: "weight", toBase: 0.001 },
  ml: { family: "volume", toBase: 1 },
  cl: { family: "volume", toBase: 10 },
  l: { family: "volume", toBase: 1000 },
  pcs: { family: "pcs", toBase: 1 },
  _unitless: { family: "_unitless", toBase: 1 },
};

const UNIT_ALIASES: Record<string, Unit> = {
  g: "g", gr: "g", gramme: "g", grammes: "g",
  kg: "kg", kgs: "kg", kilo: "kg", kilos: "kg",
  mg: "mg",
  ml: "ml",
  cl: "cl",
  l: "l", lt: "l", litre: "l", litres: "l",
  pcs: "pcs", pc: "pcs", piece: "pcs", pieces: "pcs", "pièce": "pcs", "pièces": "pcs",
};

export interface ParsedQuantity {
  value: number;
  unit: Unit;
}

export function parseQuantity(text: string): ParsedQuantity | null {
  if (text == null) return null;
  const trimmed = String(text).trim();
  if (!trimmed) return null;

  // Match: optional digits/decimals (with comma OR dot, optional separators)
  // followed by optional unit token. Examples we accept:
  //   "500g", "500 g", "1,5 kg", "2 pcs", "3", "0.5 l".
  const m = trimmed.match(/^([\d]+(?:[.,]\d+)?)\s*([a-zA-ZÀ-ÿ]+)?$/);
  if (!m) return null;

  const value = parseFloat(m[1].replace(",", "."));
  if (Number.isNaN(value)) return null;

  const rawUnit = (m[2] || "").toLowerCase();
  if (!rawUnit) return { value, unit: "_unitless" };
  const unit = UNIT_ALIASES[rawUnit];
  if (!unit) return null;
  return { value, unit };
}

interface AggregateResult {
  display: string;
  mode: "sum" | "count";
}

export function aggregate(contributions: { quantity_text: string }[]): AggregateResult {
  if (contributions.length === 0) return { display: "", mode: "count" };

  const parsed: ParsedQuantity[] = [];
  for (const c of contributions) {
    const p = parseQuantity(c.quantity_text);
    if (!p) return { display: `× ${contributions.length}`, mode: "count" };
    parsed.push(p);
  }

  // All same family?
  const families = new Set(parsed.map((p) => UNIT_TO_BASE[p.unit].family));
  if (families.size !== 1) {
    return { display: `× ${contributions.length}`, mode: "count" };
  }

  const family = parsed[0] ? UNIT_TO_BASE[parsed[0].unit].family : "_unitless";

  // Sum in the family's base unit.
  const baseTotal = parsed.reduce(
    (sum, p) => sum + p.value * UNIT_TO_BASE[p.unit].toBase,
    0
  );

  return { display: prettyTotal(baseTotal, family), mode: "sum" };
}

function prettyTotal(baseTotal: number, family: Family): string {
  const round = (n: number, d = 2): string => {
    const v = Math.round(n * 10 ** d) / 10 ** d;
    return v === Math.floor(v) ? String(v) : String(v).replace(/\.?0+$/, "");
  };

  if (family === "weight") {
    if (baseTotal >= 1000) return `${round(baseTotal / 1000)} kg`;
    if (baseTotal < 1) return `${round(baseTotal * 1000)} mg`;
    return `${round(baseTotal)} g`;
  }
  if (family === "volume") {
    if (baseTotal >= 1000) return `${round(baseTotal / 1000)} L`;
    if (baseTotal >= 100) return `${round(baseTotal / 10)} cl`;
    return `${round(baseTotal)} ml`;
  }
  if (family === "pcs") return `${round(baseTotal)} pcs`;
  return round(baseTotal);
}

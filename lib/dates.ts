// Tiny date helpers for the meal-plan calendar (Monday-anchored weeks).

export function isoDate(d: Date): string {
  // YYYY-MM-DD in local time (avoids UTC-shift surprises near midnight).
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function mondayOf(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  const dow = x.getDay(); // 0=Sun ... 6=Sat
  const offsetToMonday = dow === 0 ? -6 : 1 - dow;
  x.setDate(x.getDate() + offsetToMonday);
  return x;
}

export function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}

const FR_DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];
export function dayLabelFR(d: Date): string {
  return FR_DAYS[(d.getDay() + 6) % 7]; // shift so Monday=0
}

const FR_MONTHS = [
  "Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
  "Juil", "Août", "Sep", "Oct", "Nov", "Déc",
];
export function shortDateFR(d: Date): string {
  return `${d.getDate()} ${FR_MONTHS[d.getMonth()]}`;
}

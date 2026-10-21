import type { Lang, WorkItem } from "./lib";

const locale = (lang: Lang) => (lang === "th" ? "th-TH-u-ca-gregory" : "en-US");

// "2024-03" or "2024-03-15" -> "Mar 2024" / "มี.ค. 2024"
export function formatMonth(iso: string, lang: Lang): string {
  const d = new Date(iso.length === 7 ? `${iso}-01` : iso);
  return Number.isNaN(d.getTime()) ? iso : new Intl.DateTimeFormat(locale(lang), { month: "short", year: "numeric" }).format(d);
}

export function formatDate(iso: string, lang: Lang): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : new Intl.DateTimeFormat(locale(lang), { day: "numeric", month: "short", year: "numeric" }).format(d);
}

export function workRange(w: Pick<WorkItem, "span" | "started_on" | "ended_on">, lang: Lang, present: string): string {
  const from = formatMonth(w.started_on, lang);
  if (w.span === "moment") return from;
  return `${from} – ${w.ended_on && w.span !== "ongoing" ? formatMonth(w.ended_on, lang) : present}`;
}

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

// "3 hours ago" / "เมื่อ 3 ชั่วโมงที่แล้ว". Depends on the clock, so call it after mount, never while rendering on the server.
export function timeAgo(iso: string, lang: Lang, now: number): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
  for (const [unit, size] of [["year", 31536000], ["month", 2592000], ["day", 86400], ["hour", 3600], ["minute", 60]] as const) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit);
  }
  return rtf.format(0, "second");
}

export function workRange(w: Pick<WorkItem, "started_on" | "ended_on"> & { span: string }, lang: Lang, present: string): string {
  const from = formatMonth(w.started_on, lang);
  if (w.span === "moment") return from;
  return `${from} – ${w.ended_on && w.span !== "ongoing" ? formatMonth(w.ended_on, lang) : present}`;
}

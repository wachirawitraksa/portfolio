export type Lang = "th" | "en";

export type Category = { id: number; name_th: string; name_en: string };

// No cache: a change in the admin shows on the next page load. Revisit when traffic matters.
// Server-side only: Next talks to Python over HTTP and never to the database.
export async function getCategories(): Promise<Category[]> {
  const base = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${base}/api/categories`, { cache: "no-store" });
    return res.ok ? res.json() : [];
  } catch {
    return [];
  }
}

// Show the visitor's language; fall back to the other one while a translation is missing.
export function pick(lang: Lang, th: string, en: string): string {
  return (lang === "th" ? th || en : en || th) || "";
}

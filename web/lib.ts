// Typed access to the Python API. The types come from api-types.ts, which is generated from the API's
// OpenAPI document (`npm run api:types`, also run before every build), so a field renamed on the Python
// side becomes a TypeScript error here instead of a blank spot on the page.
import type { components, paths } from "./api-types";

export type Lang = "th" | "en";

type Schemas = components["schemas"];
export type Category = Schemas["CategoryOut"];
export type Kind = Schemas["KindOut"];
export type TagCount = Schemas["TagCount"];
export type ProjectCard = Schemas["ProjectCard"];
export type ProjectDetail = Schemas["ProjectDetail"];
export type ProjectList = Schemas["ProjectList"];
export type WorkItem = Schemas["WorkItem"];
export type EducationItem = Schemas["EducationItem"];
export type ArticleCard = Schemas["ArticleCard"];
export type ArticleDetail = Schemas["ArticleDetail"];
export type ArticleList = Schemas["ArticleList"];
export type Profile = Schemas["ProfileOut"];
export type SiteSettings = Schemas["SettingsOut"];
export type AskAnswer = Schemas["AskOut"];

export type ProjectQuery = NonNullable<paths["/api/projects"]["get"]["parameters"]["query"]>;

// No cache: a change in the admin shows on the next page load. Revisit when traffic matters.
// Server-side only: Next talks to Python over HTTP and never to the database.
async function get<T>(path: string, fallback: T): Promise<T> {
  const base = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${base}${path}`, { cache: "no-store" });
    return res.ok ? ((await res.json()) as T) : fallback;
  } catch {
    return fallback;
  }
}

export const getCategories = () => get<Category[]>("/api/categories", []);
export const getKinds = () => get<Kind[]>("/api/kinds", []);
export const getTags = () => get<TagCount[]>("/api/tags", []);
export const getProfile = () => get<Profile | null>("/api/profile", null);
export const getSettings = () => get<SiteSettings | null>("/api/settings", null);
export const getExperience = () => get<WorkItem[]>("/api/experience", []);
export const getEducation = () => get<EducationItem[]>("/api/education", []);
export const getFeatured = (limit?: number) =>
  get<ProjectCard[]>(`/api/projects/featured${limit ? `?limit=${limit}` : ""}`, []);
export const getProject = (id: number) => get<ProjectDetail | null>(`/api/projects/${id}`, null);
// null when no project is chosen in the admin (or it is not published): leave the section out.
export const getHowIWork = () => get<ProjectDetail | null>("/api/how-i-work", null);
export const getArticle = (id: number) => get<ArticleDetail | null>(`/api/articles/${id}`, null);

export function getProjects(query: ProjectQuery = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    for (const item of Array.isArray(value) ? value : [value]) {
      if (item !== undefined && item !== null && item !== "") params.append(key, String(item));
    }
  }
  return get<ProjectList>(`/api/projects?${params}`, { total: 0, items: [] });
}

export function getArticles(query: { limit?: number; offset?: number } = {}) {
  const params = new URLSearchParams();
  if (query.limit) params.set("limit", String(query.limit));
  if (query.offset) params.set("offset", String(query.offset));
  return get<ArticleList>(`/api/articles?${params}`, { total: 0, items: [] });
}

// For the browser: the question box. Relative URL, so it goes through the same proxy as the page.
// Over the daily limit the API answers 429 with a normal body (mode "rate_limited"), so both cases parse alike.
export async function askQuestion(question: string): Promise<AskAnswer> {
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok && res.status !== 429) throw new Error(`ask failed: ${res.status}`);
  return (await res.json()) as AskAnswer;
}

// Show the visitor's language; fall back to the other one while a translation is missing.
export function pick(lang: Lang, th: string, en: string): string {
  return (lang === "th" ? th || en : en || th) || "";
}

// For the browser: the project list behind the category filter and "show more". Relative URL, same proxy as the page.
export async function fetchProjects(query: ProjectQuery): Promise<ProjectList> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") params.append(key, String(value));
  }
  const res = await fetch(`/api/projects?${params}`);
  if (!res.ok) throw new Error(`projects failed: ${res.status}`);
  return (await res.json()) as ProjectList;
}

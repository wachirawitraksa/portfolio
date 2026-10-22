import type { MetadataRoute } from "next";
import { getArticles, getProjects, siteUrl } from "../lib";

const LANGS = ["th", "en"] as const;

// Every public page, in both languages, read from the API. Articles that live on another platform have no page here.
async function everyProject(): Promise<number[]> {
  const ids: number[] = [];
  for (let offset = 0; offset < 600; offset += 60) {
    const page = await getProjects({ limit: 60, offset });
    ids.push(...page.items.map((p) => p.id));
    if (offset + 60 >= page.total) break;
  }
  return ids;
}

async function everyArticle(): Promise<number[]> {
  const ids: number[] = [];
  for (let offset = 0; offset < 600; offset += 60) {
    const page = await getArticles({ limit: 60, offset });
    ids.push(...page.items.filter((a) => !a.external_url).map((a) => a.id));
    if (offset + 60 >= page.total) break;
  }
  return ids;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = siteUrl();
  const [projects, articles] = await Promise.all([everyProject(), everyArticle()]);
  const paths = ["", ...projects.map((id) => `/projects/${id}`), ...articles.map((id) => `/articles/${id}`)];
  return LANGS.flatMap((lang) =>
    paths.map((path) => ({
      url: `${base}/${lang}${path}`,
      alternates: { languages: { th: `${base}/th${path}`, en: `${base}/en${path}` } },
    })),
  );
}

// What the IDE shell needs to know about the site, built on the server from the real API.
// A section appears in the explorer / outline / menus only when it has content, and the page sections use the same rule.
import { getKindSections, type KindSection } from "./kind-sections";
import { getDict } from "./i18n";
import { getArticles, getEducation, getExperience, getHowIWork, getProfile, getTags, getUpdates, pick, type Lang, type UpdateItem } from "./lib";

export type SectionId = "home" | "about" | "experience" | "education" | KindSection["id"] | "how" | "articles" | "skills" | "contact";

export type UpdateRow = { type: UpdateItem["type"]; id: number; label: string; at: string };

export type ShellData = {
  name: string;
  slug: string;
  email: string;
  github: string | null;
  cvTh: string | null;
  cvEn: string | null;
  sections: SectionId[];
  kinds: { id: SectionId; file: string; title: string; count: number }[];
  jobs: string[];
  updates: UpdateRow[];
};

export async function getShellData(lang: Lang): Promise<ShellData> {
  const [profile, experience, education, kinds, how, articles, tags, updates] = await Promise.all([
    getProfile(),
    getExperience(),
    getEducation(),
    getKindSections(lang),
    getHowIWork(),
    getArticles({ limit: 1 }),
    getTags(),
    getUpdates(8),
  ]);
  const t = getDict(lang);

  const name = profile ? pick(lang, profile.name_th, profile.name_en) : "";
  // Folder name in the title bar, e.g. "Jane Doe" -> "jane-portfolio".
  const first = (profile?.name_en || "").trim().split(/\s+/)[0]?.toLowerCase().replace(/[^a-z0-9]/g, "") ?? "";
  const github = profile?.links.find((l) => /github\.com/i.test(l.url) || /github/i.test(l.label))?.url ?? null;

  const sections: SectionId[] = ["home"];
  if (profile && pick(lang, profile.intro_th, profile.intro_en)) sections.push("about");
  if (experience.length) sections.push("experience");
  if (education.length) sections.push("education");
  sections.push(...kinds.map((k) => k.id));
  if (how) sections.push("how");
  if (articles.total) sections.push("articles");
  if (tags.length) sections.push("skills");
  sections.push("contact");

  return {
    name,
    slug: first ? `${first}-portfolio` : "portfolio",
    email: profile?.email ?? "",
    github,
    cvTh: profile?.cv_th_url ?? null,
    cvEn: profile?.cv_en_url ?? null,
    sections,
    kinds: kinds.map((k) => ({ id: k.id, file: k.file, title: k.title, count: k.list.total })),
    jobs: experience.map((j) => pick(lang, j.position_th, j.position_en)).filter(Boolean),
    updates: updates.map((u) => ({
      type: u.type,
      id: u.id,
      at: u.at,
      label: u.type === "profile" ? t.updatedProfile : `${t.updated} ${pick(lang, u.title_th, u.title_en)}`.trim(),
    })),
  };
}

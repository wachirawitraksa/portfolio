// What the IDE shell needs to know about the site, built on the server from the real API.
// A section appears in the explorer / outline / menus only when it has content, and the page sections use the same rule.
import { getArticles, getExperience, getProfile, getProjects, getTags, pick, type Lang } from "./lib";

export type SectionId = "home" | "about" | "experience" | "projects" | "articles" | "skills" | "contact";

export type ShellData = {
  name: string;
  slug: string;
  email: string;
  github: string | null;
  cvTh: string | null;
  cvEn: string | null;
  sections: SectionId[];
  projectCount: number;
  jobs: string[];
};

export async function getShellData(lang: Lang): Promise<ShellData> {
  const [profile, experience, projects, articles, tags] = await Promise.all([
    getProfile(),
    getExperience(),
    getProjects({ limit: 1 }),
    getArticles({ limit: 1 }),
    getTags(),
  ]);

  const name = profile ? pick(lang, profile.name_th, profile.name_en) : "";
  // Folder name in the title bar, e.g. "Jane Doe" -> "jane-portfolio".
  const first = (profile?.name_en || "").trim().split(/\s+/)[0]?.toLowerCase().replace(/[^a-z0-9]/g, "") ?? "";
  const github = profile?.links.find((l) => /github\.com/i.test(l.url) || /github/i.test(l.label))?.url ?? null;

  const sections: SectionId[] = ["home"];
  if (profile && pick(lang, profile.intro_th, profile.intro_en)) sections.push("about");
  if (experience.length) sections.push("experience");
  if (projects.total) sections.push("projects");
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
    projectCount: projects.total,
    jobs: experience.map((j) => pick(lang, j.position_th, j.position_en)).filter(Boolean),
  };
}

// One page section per kind (project, certificate, award, ...), built from the kinds that exist in the admin.
// Add, rename, reorder or hide a kind there and the site follows; nothing about kinds is fixed in this code.
import { cache } from "react";
import { getCategories, getKinds, getProjects, getSettings, pick, type Category, type Lang, type ProjectList } from "./lib";

export type KindSection = {
  id: `kind-${number}` | "kind-other";
  kindId: number | null; // null = entries without a visible kind
  file: string; // explorer name, e.g. "certificate/"
  title: string;
  list: ProjectList;
  categories: Category[]; // only categories that have entries of this kind
  pageSize: number;
};

const slug = (text: string) => text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

export const getKindSections = cache(async (lang: Lang): Promise<KindSection[]> => {
  const [kinds, categories, settings, all] = await Promise.all([getKinds(), getCategories(), getSettings(), getProjects({ limit: 1 })]);
  const pageSize = settings?.projects_page_size ?? 12;

  const sections = await Promise.all(
    kinds.map(async (k): Promise<KindSection | null> => {
      const list = await getProjects({ kind: k.id, limit: pageSize });
      if (!list.total) return null;
      // A filter only helps when it splits the list, so count each category's entries of this kind.
      const counts = list.total > 1 ? await Promise.all(categories.map((c) => getProjects({ kind: k.id, category: c.id, limit: 1 }))) : [];
      const used = categories.filter((_, i) => counts[i]?.total);
      return {
        id: `kind-${k.id}`,
        kindId: k.id,
        file: `${slug(k.name_en) || `kind-${k.id}`}/`,
        title: pick(lang, k.name_th, k.name_en),
        list,
        categories: used.length > 1 ? used : [],
        pageSize,
      };
    }),
  );
  const found = sections.filter((s): s is KindSection => s !== null);

  // Entries with no kind (or a hidden one) would otherwise vanish, so they go in a last "Other" section.
  const counted = found.reduce((n, s) => n + s.list.total, 0);
  if (all.total > counted) {
    const rest = (await getProjects({ limit: 60 })).items.filter((p) => !p.kind);
    if (rest.length) {
      found.push({ id: "kind-other", kindId: null, file: "other/", title: lang === "th" ? "อื่น ๆ" : "Other", list: { total: rest.length, items: rest }, categories: [], pageSize });
    }
  }
  return found;
});

import type { Dict } from "../../i18n";
import { pick, type Lang, type TagCount } from "../../lib";
import { SectionHead, sectionClass } from "./SectionHead";

// Built from the tags that real, public projects use. The number is how many projects use it, not a skill score.
// Tags the owner filed under a group in the admin are shown under that heading; the rest go in one general list.
export function Skills({ lang, t, tags }: { lang: Lang; t: Dict; tags: TagCount[] }) {
  const byUse = (a: TagCount, b: TagCount) => b.count - a.count || a.name.localeCompare(b.name);
  const groups = new Map<string, TagCount[]>();
  for (const tag of [...tags].sort(byUse)) {
    const key = pick(lang, tag.group_th, tag.group_en);
    groups.set(key, [...(groups.get(key) ?? []), tag]);
  }
  // Named groups first, in the order of their most used tag; the general group last.
  const general = groups.get("") ?? [];
  const named = [...groups.entries()].filter(([name]) => name);
  const blocks: [string, TagCount[]][] = [...named, ...(general.length ? ([["", general]] as [string, TagCount[]][]) : [])];
  const grouped = named.length > 0;

  return (
    <section id="skills" className={`${sectionClass} gap-4`}>
      <SectionHead file="skills.json" title={t.skills} />
      <div className={grouped ? "reveal grid grid-cols-1 gap-4 sm:grid-cols-[repeat(auto-fit,minmax(min(100%,260px),1fr))]" : "reveal"}>
        {blocks.map(([name, list]) => (
          <div key={name || "general"} className={grouped ? "flex flex-col gap-3 rounded-[14px] bg-card p-5" : undefined}>
            {grouped && <div className="font-mono text-[13px] text-kw">{name || t.otherSkills}</div>}
            <ul className="m-0 flex list-none flex-wrap gap-2 p-0 font-mono text-[13px]">
              {list.map((tag) => (
                <li key={tag.id} className="rounded-full bg-chip px-3.5 py-1.5">
                  {tag.name} <span className="text-muted">{tag.count}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

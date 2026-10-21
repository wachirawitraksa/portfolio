import type { Dict } from "../../i18n";
import type { TagCount } from "../../lib";
import { SectionHead, sectionClass } from "./SectionHead";

// Built from the tags that real, public projects use. The number is how many projects use it, not a skill score.
export function Skills({ t, tags }: { t: Dict; tags: TagCount[] }) {
  const sorted = [...tags].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  return (
    <section id="skills" className={`${sectionClass} gap-4`}>
      <SectionHead file="skills.json" title={t.skills} />
      <ul className="reveal m-0 flex list-none flex-wrap gap-2 p-0 font-mono text-[13px]">
        {sorted.map((tag) => (
          <li key={tag.id} className="rounded-full bg-chip px-3.5 py-1.5">
            {tag.name} <span className="text-muted">{tag.count}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

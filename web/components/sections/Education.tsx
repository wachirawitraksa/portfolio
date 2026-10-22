import { workRange } from "../../format";
import type { Dict } from "../../i18n";
import { pick, type EducationItem, type Lang } from "../../lib";
import { SectionHead, sectionClass } from "./SectionHead";

export function Education({ lang, t, items }: { lang: Lang; t: Dict; items: EducationItem[] }) {
  return (
    <section id="education" className={`${sectionClass} gap-8`}>
      <SectionHead file="education.md" title={t.education} />
      <ol className="m-0 flex list-none flex-col gap-5 p-0">
        {items.map((e) => {
          const range = workRange(e, lang, t.present);
          const study = [pick(lang, e.degree_th, e.degree_en), pick(lang, e.field_th, e.field_en)].filter(Boolean).join(" · ");
          const details = pick(lang, e.details_th.join("\n"), e.details_en.join("\n")).split("\n").filter(Boolean);
          return (
            <li key={e.id} className="reveal flex min-w-0 flex-col gap-1 rounded-[14px] border-l-[3px] border-l-brand bg-card px-[22px] py-[18px]">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span className="text-lg font-semibold text-strong">{pick(lang, e.institution_th, e.institution_en)}</span>
                <span className="font-mono text-xs text-brand">{range}</span>
              </div>
              {(study || e.grade) && (
                <div className="text-[15px] text-muted">
                  {study}
                  {study && e.grade ? " · " : ""}
                  {e.grade}
                </div>
              )}
              <div className="font-mono text-xs text-muted">{pick(lang, e.level_th, e.level_en)}</div>
              {details.length > 0 && (
                <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 text-[15px] leading-relaxed">
                  {details.map((d, i) => <li key={i}>{d}</li>)}
                </ul>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

import { workRange } from "../../format";
import type { Dict } from "../../i18n";
import { pick, type Lang, type WorkItem } from "../../lib";
import { SectionHead, sectionClass } from "./SectionHead";

export function Career({ lang, t, jobs }: { lang: Lang; t: Dict; jobs: WorkItem[] }) {
  return (
    <section id="experience" className={`${sectionClass} gap-10`}>
      <SectionHead file="career.tsx" title={t.career} />
      <div className="relative">
        {/* The line fills as you scroll; it is hidden on phones, where each job is a bordered card instead. */}
        <div aria-hidden="true" className="absolute top-2.5 bottom-2.5 left-[159px] hidden w-0.5 bg-line sm:block" />
        <div aria-hidden="true" className="tl-fill absolute top-2.5 bottom-2.5 left-[159px] hidden w-0.5 bg-brand sm:block" />
        <ol className="m-0 flex list-none flex-col gap-7 p-0">
          {jobs.map((j) => {
            const now = j.span === "ongoing";
            const range = workRange(j, lang, t.present);
            const bullets = pick(lang, j.bullets_th.join("\n"), j.bullets_en.join("\n")).split("\n").filter(Boolean);
            const kind = pick(lang, j.employment_type_th, j.employment_type_en);
            return (
              <li key={j.id} className="reveal grid grid-cols-[minmax(0,1fr)] sm:grid-cols-[140px_40px_minmax(0,1fr)] sm:items-start">
                <div className="hidden pt-5 text-right font-mono text-[13px] text-brand sm:block">{range}</div>
                <div className="hidden justify-center pt-[22px] sm:flex">
                  <span className={`box-border size-3.5 rounded-full border-2 bg-bg ${now ? "glow-green border-[#22c55e]" : "glow border-brand"}`} />
                </div>
                <div className={`flex min-w-0 flex-col gap-1 rounded-[14px] border-l-[3px] bg-card px-[22px] py-[18px] sm:border-l-0 ${now ? "border-l-[#22c55e]" : "border-l-brand"}`}>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="text-lg font-semibold text-strong">{pick(lang, j.position_th, j.position_en)}</span>
                    {now && <span className="rounded-full bg-[#22c55e]/15 px-2 py-[3px] font-mono text-[11px] text-[#22c55e]">● {t.present}</span>}
                  </div>
                  <div className="text-[15px] text-muted">
                    {j.employer} <span className="font-mono text-xs">· {range}{kind ? ` · ${kind}` : ""}</span>
                  </div>
                  {bullets.length > 0 && (
                    <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 text-[15px] leading-relaxed">
                      {bullets.map((b, i) => <li key={i}>{b}</li>)}
                    </ul>
                  )}
                  {j.tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-xs">
                      {j.tags.map((tag) => <span key={tag.id} className="rounded-full bg-chip px-2.5 py-1">{tag.name}</span>)}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

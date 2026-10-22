import Link from "next/link";
import type { Dict } from "../../i18n";
import { pick, type Lang, type ProjectDetail } from "../../lib";
import { SectionHead, sectionClass } from "./SectionHead";

// The one project the owner picked in the admin, told as steps. Only the parts that have text are shown.
export function HowIWork({ lang, t, project }: { lang: Lang; t: Dict; project: ProjectDetail }) {
  const steps = [
    { label: t.fProblem, text: pick(lang, project.problem_th, project.problem_en) },
    { label: t.fRole, text: pick(lang, project.role_th, project.role_en) },
    { label: t.fWork, text: pick(lang, project.work_th, project.work_en) },
    { label: t.fResult, text: pick(lang, project.result_th, project.result_en) },
    { label: t.fLearned, text: pick(lang, project.learned_th, project.learned_en) },
    { label: t.fNext, text: pick(lang, project.next_steps_th, project.next_steps_en) },
  ].filter((s) => s.text);
  const title = pick(lang, project.title_th, project.title_en);

  return (
    <section id="how" className={sectionClass}>
      <SectionHead file="how-i-work.md" title={t.howIWork} />
      <p className="reveal m-0 font-mono text-[13px] text-muted">
        {t.howIntro}: <span className="text-strong">{title}</span>
      </p>
      <ol className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2">
        {steps.map((s, i) => (
          <li key={s.label} className="reveal flex min-w-0 flex-col gap-2 rounded-[14px] bg-card px-5 py-[18px]">
            <div className="font-mono text-xs text-kw">{String(i + 1).padStart(2, "0")} · {s.label}</div>
            <p className="m-0 text-[15px] leading-[1.75] whitespace-pre-line [overflow-wrap:anywhere]">{s.text}</p>
          </li>
        ))}
      </ol>
      <Link href={`/${lang}/projects/${project.id}`} className="self-start rounded-md border border-brand px-[18px] py-3 font-mono text-[13px] text-brand no-underline hover:text-brand">
        {t.readProject} →
      </Link>
    </section>
  );
}

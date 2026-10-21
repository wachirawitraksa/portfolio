import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PageOutline } from "../../../../components/PageOutline";
import { formatDate } from "../../../../format";
import { getDict, isLang } from "../../../../i18n";
import { getKindSections } from "../../../../kind-sections";
import { getProfile, getProject, pick, type Lang } from "../../../../lib";

type Params = { params: Promise<{ lang: string; id: string }> };

async function load(params: Params["params"]) {
  const { lang, id } = await params;
  if (!isLang(lang) || !/^\d+$/.test(id)) notFound();
  const project = await getProject(Number(id));
  if (!project) notFound();
  return { lang: lang as Lang, project };
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { lang, project } = await load(params);
  const profile = await getProfile();
  const title = pick(lang, project.title_th, project.title_en);
  const who = profile ? pick(lang, profile.name_th, profile.name_en) : "";
  return { title: who ? `${title} — ${who}` : title, description: pick(lang, project.problem_th, project.problem_en).slice(0, 160) || undefined };
}

export default async function ProjectPage({ params }: Params) {
  const { lang, project } = await load(params);
  const t = getDict(lang);

  // Only the fields that have text are shown; the order follows the mockup.
  const fields = [
    { id: "f-problem", label: t.fProblem, text: pick(lang, project.problem_th, project.problem_en) },
    { id: "f-role", label: t.fRole, text: pick(lang, project.role_th, project.role_en) },
    { id: "f-work", label: t.fWork, text: pick(lang, project.work_th, project.work_en) },
    { id: "f-result", label: t.fResult, text: pick(lang, project.result_th, project.result_en) },
    { id: "f-learned", label: t.fLearned, text: pick(lang, project.learned_th, project.learned_en) },
    { id: "f-next", label: t.fNext, text: pick(lang, project.next_steps_th, project.next_steps_en) },
  ].filter((f) => f.text);

  const kinds = await getKindSections(lang);
  const home = kinds.find((k) => k.kindId === project.kind?.id) ?? kinds.find((k) => k.id === "kind-other");
  const back = home ? `/${lang}#${home.id}` : `/${lang}`;

  const kindName = project.kind ? pick(lang, project.kind.name_th, project.kind.name_en) : "";
  const cats = project.categories.map((c) => pick(lang, c.name_th, c.name_en)).filter(Boolean);
  const when = project.issued_on ? formatDate(project.issued_on, lang) : project.year ? String(project.year) : "";
  const meta = [project.issuer, when].filter(Boolean);
  const links = [
    { href: project.repo_url, label: "repo" },
    { href: project.demo_url, label: "demo" },
    { href: project.verify_url, label: t.verify },
  ].filter((l) => l.href);
  const file = `project-${String(project.id).padStart(2, "0")}.md`;

  return (
    <article className="mx-auto flex max-w-[820px] flex-col gap-7 px-5 pt-12 pb-36 sm:px-10 min-[1101px]:px-14">
      <PageOutline items={fields.map((f) => ({ id: f.id, label: f.label }))} />
      <Link href={back} className="self-start rounded-md border border-line px-3.5 py-2.5 font-mono text-xs text-fg no-underline hover:bg-hover hover:text-fg">
        ← cd ../{home?.file.replace(/\/$/, "") ?? ""}
      </Link>

      <header className="flex flex-col gap-3">
        <div className="font-mono text-[13px] text-cmt">// {file}</div>
        <h1 className="text-[clamp(30px,5vw,40px)] leading-tight font-bold text-strong [overflow-wrap:anywhere]">{pick(lang, project.title_th, project.title_en)}</h1>
        <div className="flex flex-wrap gap-2 font-mono text-xs text-muted">
          {kindName && <span className="rounded-full bg-chip px-2.5 py-1 text-strong">{kindName}</span>}
          {cats.map((c) => <span key={c} className="px-2.5 py-1">{c}</span>)}
          {meta.map((m) => <span key={m} className="px-2.5 py-1">{m}</span>)}
        </div>
      </header>

      {project.images.length > 0 && (
        <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto rounded-xl" tabIndex={0} aria-label="images">
          {project.images.map((img) => {
            const caption = pick(lang, img.caption_th, img.caption_en);
            return (
              <figure key={img.id} className="m-0 flex w-full shrink-0 snap-center flex-col gap-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={img.url} alt={caption} loading="lazy" className="aspect-[16/8] w-full rounded-xl bg-card object-cover" />
                {caption && <figcaption className="font-mono text-xs text-muted">{caption}</figcaption>}
              </figure>
            );
          })}
        </div>
      )}

      <div className="flex flex-col gap-7 text-[17px] leading-[1.8]">
        {fields.map((f) => (
          <section key={f.id} id={f.id} className="flex scroll-mt-6 flex-col gap-1.5">
            <h2 className="m-0 text-xl font-semibold text-strong">{f.label}</h2>
            <p className="m-0 whitespace-pre-line [overflow-wrap:anywhere]">{f.text}</p>
          </section>
        ))}
      </div>

      {project.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 font-mono text-xs">
          {project.tags.map((tag) => <span key={tag.id} className="rounded-full bg-chip px-3 py-1.5">{tag.name}</span>)}
        </div>
      )}

      {links.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {links.map((l) => (
            <a key={l.label} href={l.href} target="_blank" rel="noopener" className="rounded-md border border-brand px-[18px] py-3 font-mono text-[13px] text-brand no-underline transition-shadow hover:text-brand hover:shadow-[0_0_0_1px_var(--brand),0_0_18px_rgb(55_148_255/0.3)]">
              {l.label} ↗
            </a>
          ))}
        </div>
      )}
    </article>
  );
}

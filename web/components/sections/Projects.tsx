"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import type { Dict } from "../../i18n";
import { fetchProjects, imageSrcSet, imageUrl, pick, type Category, type Lang, type ProjectCard, type ProjectList } from "../../lib";
import { SectionHead, sectionClass } from "./SectionHead";

type Props = { id: string; file: string; title: string; kindId: number | null; lang: Lang; t: Dict; categories: Category[]; initial: ProjectList; pageSize: number };

export function Projects({ id: sectionId, file, title, kindId, lang, t, categories, initial, pageSize }: Props) {
  const [cat, setCat] = useState<number | null>(null);
  const [items, setItems] = useState<ProjectCard[]>(initial.items);
  const [total, setTotal] = useState(initial.total);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const latest = useRef(0); // ignore a slow answer that arrives after a newer click

  async function load(category: number | null, offset: number) {
    const id = ++latest.current;
    setBusy(true);
    setFailed(false);
    try {
      const res = await fetchProjects({ kind: kindId ?? undefined, category: category ?? undefined, limit: pageSize, offset });
      if (id !== latest.current) return;
      setItems((prev) => (offset ? [...prev, ...res.items] : res.items));
      setTotal(res.total);
    } catch {
      if (id === latest.current) setFailed(true);
    } finally {
      if (id === latest.current) setBusy(false);
    }
  }

  const choose = (next: number | null) => {
    if (next === cat) return;
    setCat(next);
    void load(next, 0);
  };

  const chip = "min-h-[38px] cursor-pointer rounded-full border px-4 py-1.5 font-mono text-[13px]";
  return (
    <section id={sectionId} className={sectionClass}>
      <SectionHead file={file} title={title} />
      {categories.length > 0 && (
        <div role="group" aria-label={t.filter} className="flex flex-wrap gap-2">
          {[{ id: null, label: t.all }, ...categories.map((c) => ({ id: c.id, label: pick(lang, c.name_th, c.name_en) }))].map((c) => (
            <button
              key={c.id ?? "all"}
              type="button"
              aria-pressed={cat === c.id}
              onClick={() => choose(c.id)}
              className={`${chip} ${cat === c.id ? "border-brand bg-brand text-white" : "border-line hover:bg-hover"}`}
            >
              {c.label}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2" aria-busy={busy}>
        {items.map((p) => <Card key={p.id} p={p} lang={lang} />)}
      </div>
      {!items.length && !busy && <p className="font-mono text-sm text-muted">{t.empty}</p>}
      {failed && <p role="alert" className="font-mono text-sm text-[#f14c4c]">{t.loadFailed}</p>}
      {items.length < total && (
        <button
          type="button"
          disabled={busy}
          onClick={() => void load(cat, items.length)}
          className="cursor-pointer self-center rounded-md border border-line px-5 py-3 font-mono text-[13px] hover:bg-hover disabled:opacity-50"
        >
          {failed ? t.retry : t.more}
        </button>
      )}
    </section>
  );
}

function Card({ p, lang }: { p: ProjectCard; lang: Lang }) {
  const cats = p.categories.map((c) => pick(lang, c.name_th, c.name_en)).filter(Boolean);
  const meta = [p.kind ? pick(lang, p.kind.name_th, p.kind.name_en) : "", ...cats].filter(Boolean).join(" · ");
  const summary = pick(lang, p.problem_th, p.problem_en);
  const when = p.year ? String(p.year) : p.issued_on ? p.issued_on.slice(0, 4) : "";
  const footer = [p.issuer, when].filter(Boolean).join(" · ");
  return (
    <Link
      href={`/${lang}/projects/${p.id}`}
      className="reveal group flex flex-col overflow-hidden rounded-2xl border border-transparent bg-card text-fg no-underline transition-[transform,border-color] duration-200 hover:-translate-y-1 hover:border-brand hover:text-fg"
    >
      <div className="flex aspect-video w-full items-center justify-center bg-chip font-mono text-xs text-muted">
        {p.cover_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl(p.cover_url, 640)}
            srcSet={imageSrcSet(p.cover_url, [320, 480, 640, 960, 1280])}
            sizes="(min-width: 640px) 460px, calc(100vw - 40px)"
            alt=""
            loading="lazy"
            decoding="async"
            className="size-full object-cover"
          />
        ) : (
          <span aria-hidden="true" className="text-2xl opacity-40">{"{ }"}</span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1.5 px-5 pt-[18px] pb-[22px]">
        <div className="font-mono text-xs text-muted">{meta}</div>
        <div className="text-[19px] font-semibold text-strong">{pick(lang, p.title_th, p.title_en)}</div>
        {summary && <div className="line-clamp-3 text-[15px] leading-relaxed text-muted">{summary}</div>}
        {p.tags.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1.5 font-mono text-[11px]">
            {p.tags.slice(0, 5).map((tag) => <span key={tag.id} className="rounded-full bg-chip px-2 py-[3px]">{tag.name}</span>)}
          </div>
        )}
        {footer && <div className="mt-auto pt-2 font-mono text-xs text-muted">{footer}</div>}
      </div>
    </Link>
  );
}

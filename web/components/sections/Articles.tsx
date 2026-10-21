import Link from "next/link";
import { formatDate } from "../../format";
import type { Dict } from "../../i18n";
import { pick, type ArticleCard, type Lang } from "../../lib";
import { SectionHead, sectionClass } from "./SectionHead";

export function Articles({ lang, t, items }: { lang: Lang; t: Dict; items: ArticleCard[] }) {
  const row = "flex flex-col gap-1 border-b border-line px-2 py-[18px] text-strong no-underline hover:bg-hover hover:text-strong";
  return (
    <section id="articles" className={`${sectionClass} gap-4`}>
      <SectionHead file="articles/" title={t.articles} />
      <div className="flex flex-col">
        {items.map((a) => {
          const external = Boolean(a.external_url);
          const body = (
            <>
              <span className="flex items-baseline justify-between gap-4">
                <span className="text-[17px]">{pick(lang, a.title_th, a.title_en)}{external && " ↗"}</span>
                <span className="font-mono text-xs whitespace-nowrap text-muted">
                  {[a.platform, a.published_on && formatDate(a.published_on, lang)].filter(Boolean).join(" · ")}
                </span>
              </span>
              {pick(lang, a.summary_th, a.summary_en) && <span className="text-[15px] text-muted">{pick(lang, a.summary_th, a.summary_en)}</span>}
            </>
          );
          return external ? (
            <a key={a.id} href={a.external_url} target="_blank" rel="noopener" className={`reveal ${row}`}>{body}</a>
          ) : (
            <Link key={a.id} href={`/${lang}/articles/${a.id}`} className={`reveal ${row}`}>{body}</Link>
          );
        })}
      </div>
    </section>
  );
}

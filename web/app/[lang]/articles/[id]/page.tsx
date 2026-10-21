import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { Markdown } from "../../../../components/Markdown";
import { formatDate } from "../../../../format";
import { isLang } from "../../../../i18n";
import { getArticle, getProfile, pick, type Lang } from "../../../../lib";

type Params = { params: Promise<{ lang: string; id: string }> };

async function load(params: Params["params"]) {
  const { lang, id } = await params;
  if (!isLang(lang) || !/^\d+$/.test(id)) notFound();
  const article = await getArticle(Number(id));
  if (!article) notFound();
  const body = pick(lang as Lang, article.body_th, article.body_en);
  // An article that lives on another platform has no text here: send the reader there.
  if (!body && article.external_url) redirect(article.external_url);
  if (!body) notFound();
  return { lang: lang as Lang, article, body };
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { lang, article } = await load(params);
  const profile = await getProfile();
  const title = pick(lang, article.title_th, article.title_en);
  const who = profile ? pick(lang, profile.name_th, profile.name_en) : "";
  return { title: who ? `${title} — ${who}` : title, description: pick(lang, article.summary_th, article.summary_en) || undefined };
}

export default async function ArticlePage({ params }: Params) {
  const { lang, article, body } = await load(params);
  const file = `article-${String(article.id).padStart(2, "0")}.md`;
  const meta = [article.platform, article.published_on && formatDate(article.published_on, lang)].filter(Boolean).join(" · ");

  return (
    <article className="mx-auto flex max-w-[760px] flex-col gap-6 px-5 pt-12 pb-36 sm:px-10 min-[1101px]:px-14">
      <Link href={`/${lang}#articles`} className="self-start rounded-md border border-line px-3.5 py-2.5 font-mono text-xs text-fg no-underline hover:bg-hover hover:text-fg">
        ← cd ../articles
      </Link>
      <header className="flex flex-col gap-3">
        <div className="font-mono text-[13px] text-cmt">// {file}</div>
        <h1 className="text-[clamp(30px,5vw,40px)] leading-tight font-bold text-strong [overflow-wrap:anywhere]">{pick(lang, article.title_th, article.title_en)}</h1>
        {meta && <div className="font-mono text-xs text-muted">{meta}</div>}
        {article.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 font-mono text-xs">
            {article.tags.map((tag) => <span key={tag.id} className="rounded-full bg-chip px-3 py-1.5">{tag.name}</span>)}
          </div>
        )}
      </header>
      <Markdown>{body}</Markdown>
    </article>
  );
}

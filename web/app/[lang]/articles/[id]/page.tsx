import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { Markdown } from "../../../../components/Markdown";
import { formatDate } from "../../../../format";
import { getDict, isLang } from "../../../../i18n";
import { getArticle, getArticlePreview, getProfile, pick, type Lang } from "../../../../lib";

type Params = { params: Promise<{ lang: string; id: string }>; searchParams: Promise<{ preview?: string }> };

// With ?preview=<token> (the owner's "preview on the site" link) a draft is shown, marked as not public.
async function load({ params, searchParams }: Params) {
  const { lang, id } = await params;
  const { preview } = await searchParams;
  if (!isLang(lang) || !/^\d+$/.test(id)) notFound();
  const article = preview ? await getArticlePreview(Number(id), preview) : await getArticle(Number(id));
  if (!article) notFound();
  const body = pick(lang as Lang, article.body_th, article.body_en);
  // An article that lives on another platform has no text here: send the reader there.
  if (!body && article.external_url && !preview) redirect(article.external_url);
  if (!body && !preview) notFound();
  return { lang: lang as Lang, article, body, preview };
}

export async function generateMetadata(props: Params): Promise<Metadata> {
  const { lang, article, preview } = await load(props);
  const profile = await getProfile();
  const title = pick(lang, article.title_th, article.title_en);
  const who = profile ? pick(lang, profile.name_th, profile.name_en) : "";
  const full = who ? `${title} — ${who}` : title;
  const description = pick(lang, article.summary_th, article.summary_en) || undefined;
  if (preview) return { title: full, robots: { index: false, follow: false } };
  return {
    title: full,
    description,
    alternates: { canonical: `/${lang}/articles/${article.id}`, languages: { th: `/th/articles/${article.id}`, en: `/en/articles/${article.id}` } },
    openGraph: { title: full, description, type: "article", publishedTime: article.published_on ?? undefined },
  };
}

export default async function ArticlePage(props: Params) {
  const { lang, article, body, preview } = await load(props);
  const t = getDict(lang);
  const file = `article-${String(article.id).padStart(2, "0")}.md`;
  const meta = [article.platform, article.published_on && formatDate(article.published_on, lang)].filter(Boolean).join(" · ");

  return (
    <article className="mx-auto flex max-w-[760px] flex-col gap-6 px-5 pt-12 pb-36 sm:px-10 min-[1101px]:px-14">
      {preview && <p role="status" className="m-0 rounded-md border border-[#dcb67a] px-3.5 py-2.5 font-mono text-xs text-[#dcb67a]">{t.previewBanner}</p>}
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

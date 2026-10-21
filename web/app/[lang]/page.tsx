import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { Setup } from "../../components/Setup";
import { getDict, isLang } from "../../i18n";
import { getCategories, getProfile, pick } from "../../lib";

// Temporary page for checking step 1 (Tailwind, fonts, themes, language). Replaced by the real shell in step 2.
export default async function Home({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const [categories, profile] = await Promise.all([getCategories(), getProfile()]);
  const t = getDict(lang);
  const theme = (await cookies()).get("theme")?.value === "light" ? "light" : "dark";

  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col gap-6 px-5 py-10">
      <Setup lang={lang} initialTheme={theme} labels={{ theme: t.themeBtn, lang: t.langGroup }} />
      <div className="font-mono text-sm text-cmt">// {t.projects}</div>
      <h1 className="text-4xl font-bold text-strong">{profile ? pick(lang, profile.name_th, profile.name_en) || t.empty : t.empty}</h1>
      <ul className="flex flex-wrap gap-2 font-mono text-sm">
        {categories.map((c) => (
          <li key={c.id} className="rounded-full bg-chip px-3 py-1 text-fg">
            {pick(lang, c.name_th, c.name_en)}
          </li>
        ))}
      </ul>
    </main>
  );
}

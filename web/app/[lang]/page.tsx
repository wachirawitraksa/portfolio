import { notFound } from "next/navigation";
import { About } from "../../components/sections/About";
import { Articles } from "../../components/sections/Articles";
import { Career } from "../../components/sections/Career";
import { Contact } from "../../components/sections/Contact";
import { Hero } from "../../components/sections/Hero";
import { Projects } from "../../components/sections/Projects";
import { Skills } from "../../components/sections/Skills";
import { getDict, isLang } from "../../i18n";
import { getKindSections } from "../../kind-sections";
import { getArticles, getExperience, getProfile, getSettings, getTags, pick } from "../../lib";

// Every section is built from the API. A section with nothing to show is left out (the explorer uses the same rule).
export default async function Home({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const t = getDict(lang);

  const [profile, settings, experience, kinds, tags] = await Promise.all([getProfile(), getSettings(), getExperience(), getKindSections(lang), getTags()]);
  const articles = await getArticles({ limit: settings?.articles_page_size });

  const intro = profile ? pick(lang, profile.intro_th, profile.intro_en) : "";
  const current = experience.find((j) => j.span === "ongoing");
  const role = current ? pick(lang, current.position_th, current.position_en) : "";

  return (
    <div className="mx-auto max-w-[1000px] px-5 pb-40 sm:px-10 min-[1101px]:px-14">
      <Hero profile={profile} role={role} />
      {intro && <About title={t.about} intro={intro} />}
      {experience.length > 0 && <Career lang={lang} t={t} jobs={experience} />}
      {kinds.map((k) => (
        <Projects key={k.id} id={k.id} file={k.file} title={k.title} kindId={k.kindId} lang={lang} t={t} categories={k.categories} initial={k.list} pageSize={k.pageSize} />
      ))}
      {articles.total > 0 && <Articles lang={lang} t={t} items={articles.items} />}
      {tags.length > 0 && <Skills t={t} tags={tags} />}
      <Contact profile={profile} />
    </div>
  );
}

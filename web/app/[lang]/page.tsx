import { notFound } from "next/navigation";
import { About } from "../../components/sections/About";
import { Articles } from "../../components/sections/Articles";
import { Career } from "../../components/sections/Career";
import { Education } from "../../components/sections/Education";
import { HowIWork } from "../../components/sections/HowIWork";
import { Contact } from "../../components/sections/Contact";
import { Hero } from "../../components/sections/Hero";
import { Projects } from "../../components/sections/Projects";
import { Skills } from "../../components/sections/Skills";
import { getDict, isLang } from "../../i18n";
import { getKindSections } from "../../kind-sections";
import { getArticles, getEducation, getExperience, getHowIWork, getProfile, getSettings, getTags, pick, siteUrl } from "../../lib";

// Every section is built from the API. A section with nothing to show is left out (the explorer uses the same rule).
export default async function Home({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const t = getDict(lang);

  const [profile, settings, experience, education, kinds, how, tags] = await Promise.all([
    getProfile(),
    getSettings(),
    getExperience(),
    getEducation(),
    getKindSections(lang),
    getHowIWork(),
    getTags(),
  ]);
  const articles = await getArticles({ limit: settings?.articles_page_size });

  const intro = profile ? pick(lang, profile.intro_th, profile.intro_en) : "";
  const current = experience.find((j) => j.span === "ongoing");
  // The headline written in the admin wins; without one, the position of the current job stands in for it.
  const headline = profile ? pick(lang, profile.headline_th, profile.headline_en) : "";
  const role = headline || (current ? pick(lang, current.position_th, current.position_en) : "");

  // Structured data for search engines: who this page is about. Only what the owner has published.
  const person = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: profile ? pick(lang, profile.name_th, profile.name_en) : undefined,
    jobTitle: role || undefined,
    url: `${siteUrl()}/${lang}`,
    image: profile?.photo_url ? `${siteUrl()}${profile.photo_url}` : undefined,
    sameAs: profile?.links.map((l) => l.url).filter((u) => /^https?:\/\//.test(u)),
  };

  return (
    <div className="mx-auto max-w-[1000px] px-5 pb-40 sm:px-10 min-[1101px]:px-14">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(person).replace(/</g, "\\u003c") }} />
      <Hero profile={profile} role={role} />
      {intro && <About title={t.about} intro={intro} />}
      {experience.length > 0 && <Career lang={lang} t={t} jobs={experience} />}
      {education.length > 0 && <Education lang={lang} t={t} items={education} />}
      {kinds.map((k) => (
        <Projects key={k.id} id={k.id} file={k.file} title={k.title} kindId={k.kindId} lang={lang} t={t} categories={k.categories} initial={k.list} pageSize={k.pageSize} />
      ))}
      {how && <HowIWork lang={lang} t={t} project={how} />}
      {articles.total > 0 && <Articles lang={lang} t={t} items={articles.items} />}
      {tags.length > 0 && <Skills lang={lang} t={t} tags={tags} />}
      <Contact profile={profile} />
    </div>
  );
}

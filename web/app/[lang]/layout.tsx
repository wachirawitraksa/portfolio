import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { Shell } from "../../components/Shell";
import { getDict, isLang } from "../../i18n";
import { getProfile, getSettings, imageUrl, pick, siteUrl } from "../../lib";
import { getShellData } from "../../shell-data";
import "../fonts";
import "../globals.css";

// Runs before the first paint: show the splash only on the first visit of a browser session, and not for
// people who ask for reduced motion.
const BOOT_SCRIPT = `try{if(!matchMedia("(prefers-reduced-motion: reduce)").matches&&!sessionStorage.getItem("boot"))document.documentElement.dataset.boot="1"}catch(e){}`;

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }): Promise<Metadata> {
  const { lang } = await params;
  if (!isLang(lang)) return {};
  const [profile, settings] = await Promise.all([getProfile(), getSettings()]);
  const name = profile ? pick(lang, profile.name_th, profile.name_en) : "";
  // What the owner wrote in the admin wins; otherwise the title and description are built from the profile.
  const title = (settings && pick(lang, settings.site_title_th, settings.site_title_en)) || (name ? `${name} — Portfolio` : "Portfolio");
  const description =
    (settings && pick(lang, settings.site_description_th, settings.site_description_en)) ||
    (profile ? pick(lang, profile.intro_th, profile.intro_en).replace(/\s+/g, " ").slice(0, 160) : "") ||
    undefined;
  return {
    metadataBase: new URL(siteUrl()),
    title,
    description,
    alternates: { canonical: `/${lang}`, languages: { th: "/th", en: "/en" } },
    openGraph: {
      title,
      description,
      type: "website",
      locale: lang === "th" ? "th_TH" : "en_US",
      images: profile?.photo_url ? [{ url: imageUrl(profile.photo_url, 1280) }] : undefined,
    },
  };
}

export default async function RootLayout({ children, params }: { children: ReactNode; params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  // Theme comes from a cookie so the server renders the right colours on the first paint (no flash).
  const data = await getShellData(lang);
  const theme = (await cookies()).get("theme")?.value === "light" ? "light" : "dark";

  return (
    <html lang={lang} data-theme={theme} suppressHydrationWarning>
      <body className="font-sans antialiased">
        <script dangerouslySetInnerHTML={{ __html: BOOT_SCRIPT }} />
        <Shell lang={lang} t={getDict(lang)} data={data} initialTheme={theme}>
          {children}
        </Shell>
      </body>
    </html>
  );
}

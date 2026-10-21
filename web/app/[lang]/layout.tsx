import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { Shell } from "../../components/Shell";
import { getDict, isLang } from "../../i18n";
import { getProfile, pick } from "../../lib";
import { getShellData } from "../../shell-data";
import "../fonts";
import "../globals.css";

// Runs before the first paint: show the splash only on the first visit of a browser session, and not for
// people who ask for reduced motion.
const BOOT_SCRIPT = `try{if(!matchMedia("(prefers-reduced-motion: reduce)").matches&&!sessionStorage.getItem("boot"))document.documentElement.dataset.boot="1"}catch(e){}`;

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }): Promise<Metadata> {
  const { lang } = await params;
  if (!isLang(lang)) return {};
  const profile = await getProfile();
  const name = profile ? pick(lang, profile.name_th, profile.name_en) : "";
  return { title: name ? `${name} — Portfolio` : "Portfolio" };
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

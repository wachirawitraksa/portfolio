import type { Metadata } from "next";
import { IBM_Plex_Sans_Thai, JetBrains_Mono, Poppins } from "next/font/google";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { Shell } from "../../components/Shell";
import { getDict, isLang } from "../../i18n";
import { getProfile, pick } from "../../lib";
import { getShellData } from "../../shell-data";
import "../globals.css";

const poppins = Poppins({ subsets: ["latin"], weight: ["400", "500", "600", "700", "800"], variable: "--font-poppins", display: "swap" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], weight: ["400", "500", "700"], variable: "--font-jetbrains", display: "swap" });
const plexThai = IBM_Plex_Sans_Thai({ subsets: ["thai", "latin"], weight: ["400", "500", "600", "700"], variable: "--font-plex-thai", display: "swap" });

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
    <html lang={lang} data-theme={theme} className={`${poppins.variable} ${jetbrains.variable} ${plexThai.variable}`}>
      <body className="font-sans antialiased">
        <Shell lang={lang} t={getDict(lang)} data={data} initialTheme={theme}>
          {children}
        </Shell>
      </body>
    </html>
  );
}

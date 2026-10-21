import { notFound } from "next/navigation";
import { FILES } from "../../components/files";
import { isLang } from "../../i18n";
import { getShellData } from "../../shell-data";

// Temporary: one empty block per section so the shell's navigation can be checked. Step 3 replaces it with the real sections.
export default async function Home({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const { sections } = await getShellData(lang);

  return (
    <div className="mx-auto max-w-[1000px] px-5 pb-40 sm:px-10 ide:px-14">
      {sections.map((id) => (
        <section key={id} id={id} className="flex min-h-[70vh] flex-col gap-3 pt-16">
          <div className="font-mono text-[13px] text-cmt">// {FILES[id].name}</div>
        </section>
      ))}
    </div>
  );
}

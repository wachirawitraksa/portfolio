import { notFound } from "next/navigation";
import { getCategories, pick, type Lang } from "../../lib";

export default async function Home({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (lang !== "th" && lang !== "en") notFound();
  const categories = await getCategories();

  return (
    <main>
      <p>
        <a href="/th">ไทย</a> · <a href="/en">English</a>
      </p>
      {/* Placeholder: the real pages come after real content exists. */}
      <ul>
        {categories.map((c) => (
          <li key={c.id}>{pick(lang as Lang, c.name_th, c.name_en)}</li>
        ))}
      </ul>
    </main>
  );
}

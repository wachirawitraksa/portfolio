import { SectionHead, sectionClass } from "./SectionHead";

export function About({ title, intro }: { title: string; intro: string }) {
  return (
    <section id="about" className={sectionClass}>
      <SectionHead file="about.md" title={title} />
      <p className="reveal max-w-[680px] text-lg leading-[1.85] whitespace-pre-line">{intro}</p>
    </section>
  );
}

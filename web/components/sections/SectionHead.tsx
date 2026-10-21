export function SectionHead({ file, title }: { file: string; title: string }) {
  return (
    <div className="reveal flex flex-col gap-3.5">
      <div className="font-mono text-[13px] text-cmt">// {file}</div>
      <h2 className="text-[clamp(28px,4vw,40px)] leading-tight font-bold text-strong">{title}</h2>
    </div>
  );
}

export const sectionClass = "flex flex-col gap-6 pt-28";

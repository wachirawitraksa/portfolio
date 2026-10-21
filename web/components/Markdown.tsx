import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

// Article bodies are Markdown written in the admin. Raw HTML in the text is not rendered (react-markdown's default).
const components: Components = {
  h1: (p) => <h2 className="mt-10 mb-3 text-[28px] leading-tight font-bold text-strong" {...p} />,
  h2: (p) => <h2 className="mt-10 mb-3 text-[24px] leading-tight font-semibold text-strong" {...p} />,
  h3: (p) => <h3 className="mt-8 mb-2 text-xl font-semibold text-strong" {...p} />,
  h4: (p) => <h4 className="mt-6 mb-2 text-lg font-semibold text-strong" {...p} />,
  p: (p) => <p className="my-4" {...p} />,
  ul: (p) => <ul className="my-4 list-disc pl-6 [&_ul]:my-1" {...p} />,
  ol: (p) => <ol className="my-4 list-decimal pl-6 [&_ol]:my-1" {...p} />,
  li: (p) => <li className="my-1" {...p} />,
  a: ({ href, ...p }) => <a href={href} target={href?.startsWith("http") ? "_blank" : undefined} rel="noopener" className="text-brand underline underline-offset-2 hover:text-strong" {...p} />,
  blockquote: (p) => <blockquote className="my-4 border-l-[3px] border-brand pl-4 text-muted" {...p} />,
  hr: () => <hr className="my-8 border-line" />,
  // eslint-disable-next-line @next/next/no-img-element
  img: ({ alt, src }) => <img src={typeof src === "string" ? src : undefined} alt={alt ?? ""} loading="lazy" className="my-4 h-auto max-w-full rounded-lg" />,
  pre: (p) => <pre className="my-4 max-w-full overflow-x-auto rounded-lg bg-term p-4 font-mono text-[13px] leading-relaxed" {...p} />,
  code: ({ className, ...p }) => <code className={`font-mono text-[0.9em] ${className ?? "rounded bg-chip px-1.5 py-0.5"}`} {...p} />,
  table: (p) => (
    <div className="my-4 max-w-full overflow-x-auto">
      <table className="w-full border-collapse text-left text-[15px]" {...p} />
    </div>
  ),
  th: (p) => <th className="border-b border-line px-3 py-2 font-semibold text-strong" {...p} />,
  td: (p) => <td className="border-b border-line px-3 py-2" {...p} />,
};

export function Markdown({ children }: { children: string }) {
  return (
    <div className="text-[17px] leading-[1.85] [overflow-wrap:anywhere]">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}

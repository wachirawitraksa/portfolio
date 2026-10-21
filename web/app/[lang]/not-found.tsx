import Link from "next/link";

// Inside the shell, so the explorer and menus still work. No language is available here, so both are shown.
export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-[820px] flex-col items-start gap-4 px-5 pt-24 sm:px-10">
      <div className="font-mono text-[13px] text-cmt">// 404</div>
      <h1 className="text-4xl font-bold text-strong">ไม่พบหน้านี้ · Page not found</h1>
      <Link href="/" className="rounded-md border border-line px-3.5 py-2.5 font-mono text-xs text-fg no-underline hover:bg-hover hover:text-fg">
        ← cd ~
      </Link>
    </div>
  );
}

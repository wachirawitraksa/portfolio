import type { SectionId, ShellData } from "../shell-data";

type FileInfo = { name: string; badge: string; color: string };

// Each page section is shown as a "file" in the explorer, the way the mockup does.
const FIXED: Record<string, FileInfo> = {
  home: { name: "home.tsx", badge: "TSX", color: "#4ec9b0" },
  about: { name: "about.md", badge: "MD", color: "#519aba" },
  experience: { name: "career.tsx", badge: "TSX", color: "#4ec9b0" },
  education: { name: "education.md", badge: "MD", color: "#519aba" },
  how: { name: "how-i-work.md", badge: "MD", color: "#519aba" },
  articles: { name: "articles/", badge: "▸", color: "#dcb67a" },
  skills: { name: "skills.json", badge: "{}", color: "#cbcb41" },
  contact: { name: "contact.css", badge: "#", color: "#569cd6" },
};

export const RESUME_FILE: FileInfo = { name: "resume.pdf", badge: "PDF", color: "#e06c75" };

// Kinds are dynamic (they come from the admin), so their file names come from the shell data.
export function fileInfo(id: SectionId, data: ShellData): FileInfo {
  const kind = data.kinds.find((k) => k.id === id);
  if (kind) return { name: kind.file, badge: "▸", color: "#dcb67a" };
  return FIXED[id] ?? FIXED.home;
}

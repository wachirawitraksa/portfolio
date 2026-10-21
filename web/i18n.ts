// UI text only (menus, buttons, section titles). Site content (names, projects, jobs) always comes from the API.
import type { Lang } from "./lib";

export const LANGS: Lang[] = ["th", "en"];
export const isLang = (value: string): value is Lang => (LANGS as string[]).includes(value);

const th = {
  menubar: "เมนู",
  langGroup: "ภาษา",
  themeBtn: "สลับธีมมืด/สว่าง",
  sidebarBtn: "แสดง/ซ่อนแถบไฟล์ (Ctrl+B)",
  terminalBtn: "แสดง/ซ่อนเทอร์มินัล (Ctrl+J)",
  askBtn: "ถาม AI",
  close: "ปิด",
  skip: "ข้าม (Esc)",
  seeWork: "./ดูผลงาน",
  about: "เกี่ยวกับ",
  career: "ประวัติการทำงาน",
  present: "ปัจจุบัน",
  projects: "ผลงาน",
  filter: "กรองตามหมวด",
  all: "ทั้งหมด",
  more: "ดูเพิ่ม",
  articles: "บทความ",
  skills: "ทักษะ",
  contact: "ติดต่อ",
  copyEmail: "คัดลอกอีเมล",
  emailCopied: "คัดลอกอีเมลแล้ว",
  fProblem: "ปัญหาที่แก้",
  fRole: "บทบาทของผม",
  fWork: "สิ่งที่ทำ",
  fResult: "ผลลัพธ์",
  fLearned: "สิ่งที่ได้เรียนรู้",
  fNext: "ถ้าทำต่อจะทำอะไร",
  empty: "ยังไม่มีข้อมูล",
};

const en: typeof th = {
  menubar: "Menu",
  langGroup: "Language",
  themeBtn: "Toggle dark/light theme",
  sidebarBtn: "Toggle file sidebar (Ctrl+B)",
  terminalBtn: "Toggle terminal (Ctrl+J)",
  askBtn: "Ask AI",
  close: "Close",
  skip: "Skip (Esc)",
  seeWork: "./view-work",
  about: "About",
  career: "Experience",
  present: "Present",
  projects: "Projects",
  filter: "Filter by category",
  all: "All",
  more: "Show more",
  articles: "Articles",
  skills: "Skills",
  contact: "Contact",
  copyEmail: "Copy email",
  emailCopied: "Email copied",
  fProblem: "Problem",
  fRole: "My role",
  fWork: "What I did",
  fResult: "Result",
  fLearned: "What I learned",
  fNext: "Next steps",
  empty: "Nothing here yet",
};

export type Dict = typeof th;
export const getDict = (lang: Lang): Dict => (lang === "th" ? th : en);

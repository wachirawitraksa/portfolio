from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from .i18n import tr, translate_source

TEMPLATE_DIR = Path(__file__).parent / "templates"

# The admin menu: (group, [(label, path, exact, icon)]). `exact` keeps "/rag" from lighting up on "/rag/questions".
NAV = [
    ("", [("ภาพรวม", "/", True, "home")]),
    (
        "เนื้อหา",
        [
            ("ข้อมูลส่วนตัว", "/profile", False, "user"),
            ("ประวัติการทำงาน", "/work", False, "briefcase"),
            ("ประวัติการศึกษา", "/education", False, "cap"),
            ("ผลงาน / รายการ", "/projects", False, "folder"),
            ("บทความ", "/articles", False, "file"),
        ],
    ),
    (
        "จัดหมวด",
        [
            ("ประเภท", "/categories", False, "layers"),
            ("ชนิด", "/kinds", False, "shapes"),
            ("tag เทคโนโลยี", "/tags", False, "tag"),
        ],
    ),
    (
        "ช่องถามตอบ",
        [
            ("สถานะและลองถาม", "/rag", True, "message"),
            ("คำถามจากผู้เข้าชม", "/rag/questions", False, "inbox"),
            ("glossary", "/glossary", False, "book"),
        ],
    ),
    (
        "ระบบ",
        [
            ("ตั้งค่าการแสดงผล", "/settings", False, "sliders"),
            ("บัญชีและความปลอดภัย", "/account", False, "shield"),
            ("session ที่ล็อกอินอยู่", "/sessions", False, "monitor"),
            ("ถังขยะ", "/trash", False, "trash"),
        ],
    ),
]

# The "create" menu at the top of the sidebar: (label, path).
QUICK_CREATE = [
    ("ประวัติการทำงาน", "/work/new"),
    ("ประวัติการศึกษา", "/education/new"),
    ("ผลงาน / รายการ", "/projects/new"),
    ("บทความ", "/articles/new"),
    ("กลุ่มคำ glossary", "/glossary/new"),
    ("tag เทคโนโลยี", "/tags/new"),
]

LANGS = ("th", "en")
THEMES = ("light", "dark")


def admin_path(request) -> str:
    """The path as the browser sees it on the admin host, which has no /admin prefix."""
    path = request.url.path
    return path[len("/admin") :] or "/" if path.startswith("/admin") else path


def nav_active(current: str, href: str, exact: bool) -> bool:
    if exact or href == "/":
        return current == href
    return current == href or current.startswith(href + "/")


def nav_current(current: str) -> tuple[str, str]:
    """(group, label) of the menu item the visitor is on, for the header. Empty strings off the menu."""
    for group, items in NAV:
        for label, href, exact, _icon in items:
            if nav_active(current, href, exact):
                return group, label
    return "", ""


def read_cookie(request, name: str, allowed: tuple[str, ...], default: str = "") -> str:
    value = request.cookies.get(name, "")
    return value if value in allowed else default


class EnglishLoader(FileSystemLoader):
    """Loads the same template files, with the Thai in their source turned into English first. The owner's own
    text never goes through here: it is not in the source, it only arrives when the page is drawn."""

    def get_source(self, environment, template):
        source, filename, uptodate = super().get_source(environment, template)
        return translate_source(source), filename, uptodate


def build(english: bool) -> Jinja2Templates:
    loader = (EnglishLoader if english else FileSystemLoader)(str(TEMPLATE_DIR))
    env = Environment(loader=loader, autoescape=True)
    env.globals.update(
        NAV=NAV,
        QUICK_CREATE=QUICK_CREATE,
        admin_path=admin_path,
        nav_active=nav_active,
        nav_current=nav_current,
        ui_theme=lambda request: read_cookie(request, "theme", THEMES),
        ui_lang=lambda request: read_cookie(request, "lang", LANGS, "th"),
        ui_sidebar=lambda request: read_cookie(request, "sidebar", ("collapsed", "open"), "open"),
    )
    # {{ text | tr }}: text that Python made (an error message, a label). Thai pages leave it as it is.
    env.filters["tr"] = lambda value: tr(value, english)
    env.filters["trmap"] = lambda mapping: {key: tr(value, english) for key, value in mapping.items()}
    return Jinja2Templates(env=env)


class LanguageTemplates:
    """One set of templates per language; the visitor's lang cookie picks which one draws the page."""

    def __init__(self) -> None:
        self.thai = build(english=False)
        self.english = build(english=True)

    @property
    def env(self):
        return self.thai.env

    def TemplateResponse(self, request, name, context=None, *args, **kwargs):
        engine = self.english if read_cookie(request, "lang", LANGS, "th") == "en" else self.thai
        return engine.TemplateResponse(request, name, context, *args, **kwargs)


templates = LanguageTemplates()

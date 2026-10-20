from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# The admin menu: (group, [(label, path, exact)]). `exact` keeps "/rag" from lighting up on "/rag/questions".
NAV = [
    ("", [("ภาพรวม", "/", True)]),
    (
        "เนื้อหา",
        [
            ("ผลงาน / รายการ", "/projects", False),
            ("ประวัติการทำงาน", "/work", False),
            ("ประวัติการศึกษา", "/education", False),
            ("บทความ", "/articles", False),
            ("ข้อมูลส่วนตัว", "/profile", False),
        ],
    ),
    (
        "จัดหมวด",
        [("ประเภท", "/categories", False), ("ชนิด", "/kinds", False), ("tag เทคโนโลยี", "/tags", False)],
    ),
    (
        "ช่องถามตอบ",
        [("สถานะและลองถาม", "/rag", True), ("คำถามจากผู้เข้าชม", "/rag/questions", False), ("glossary", "/glossary", False)],
    ),
    (
        "ระบบ",
        [
            ("ตั้งค่าการแสดงผล", "/settings", False),
            ("ถังขยะ", "/trash", False),
            ("บัญชีและความปลอดภัย", "/account", False),
            ("session ที่ล็อกอินอยู่", "/sessions", False),
        ],
    ),
]


def admin_path(request) -> str:
    """The path as the browser sees it on the admin host, which has no /admin prefix."""
    path = request.url.path
    return path[len("/admin") :] or "/" if path.startswith("/admin") else path


def nav_active(current: str, href: str, exact: bool) -> bool:
    if exact or href == "/":
        return current == href
    return current == href or current.startswith(href + "/")


templates.env.globals["NAV"] = NAV
templates.env.globals["admin_path"] = admin_path
templates.env.globals["nav_active"] = nav_active

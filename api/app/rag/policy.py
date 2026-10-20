"""Questions that are answered by rule, never by the model: greetings, requests for salary or a phone
number (sent to email instead), and attempts to talk the assistant out of its job."""
import re

from .text import has_thai

GREETINGS = frozenset(
    "hi hello hey hola yo สวัสดี หวัดดี ดี สวัสดีครับ สวัสดีค่ะ ดีครับ ดีค่ะ good morning afternoon evening "
    "there ครับ ค่ะ คะ นะ".split()
)

# Pay and personal phone numbers are for a direct conversation, not for the website.
# Whole phrases only: Thai has no spaces, so a bare "ไลน์" would also match "ออนไลน์" (online),
# and a bare "phone" would catch a question about a phone app.
CONTACT_TOPICS_TH = (
    "เงินเดือน", "ค่าตัว", "ค่าจ้าง", "เรทเงิน", "เรทราคา", "เบอร์โทร", "เบอร์มือถือ", "เบอร์ติดต่อ",
    "เบอร์ส่วนตัว", "ขอเบอร์", "เบอร์ของคุณ", "โทรหา", "ไอดีไลน์", "แอดไลน์", "ขอไลน์",
)
CONTACT_TOPICS_EN = re.compile(
    r"\b(salary|salaries|pay rate|hourly rate|day rate|compensation|how much (do|does|would) (you|he|she|they) "
    r"(charge|earn|make|cost)|(phone|mobile|cell|telephone) number|your phone|call (you|him|her)|whatsapp|line id)\b"
)

# Phrases that try to change the assistant's instructions or make it reveal them.
INJECTION_EN = re.compile(
    r"(ignore|disregard|forget|override|bypass)\s+(all\s+|any\s+|the\s+|your\s+|my\s+)?"
    r"(previous|prior|above|earlier|system|initial|these|those)?\s*(instructions?|prompts?|rules?|directions?|guidelines?)"
    r"|(reveal|show|print|repeat|leak|tell me|display)\s+(me\s+)?(your|the)\s+(system\s+|hidden\s+|initial\s+)?(prompt|instructions?|rules)"
    r"|system\s+prompt|developer\s+mode|jailbreak|\bdan\s+mode\b|new\s+instructions?"
    r"|you\s+are\s+now\b|from\s+now\s+on\s+you|pretend\s+(to\s+be|you\s+are)"
)
INJECTION_TH = (
    "เมินคำสั่ง", "ละเว้นคำสั่ง", "ลืมคำสั่ง", "ไม่ต้องสนใจคำสั่ง", "ไม่ต้องทำตามคำสั่ง", "คำสั่งก่อนหน้า", "คำสั่งเดิม",
    "ข้ามคำสั่ง", "แสดงคำสั่ง", "เปิดเผยคำสั่ง", "พรอมต์ของคุณ", "พร้อมต์ของคุณ", "ซิสเต็มพรอมต์", "สมมติว่าคุณเป็น",
    "ต่อจากนี้คุณคือ", "ตอนนี้คุณคือ",
)


def is_greeting(text: str) -> bool:
    tokens = text.split()
    return bool(tokens) and len(tokens) <= 4 and all(t in GREETINGS for t in tokens)


def is_injection(raw: str, text: str) -> bool:
    lowered = raw.lower()
    if INJECTION_EN.search(lowered) or INJECTION_EN.search(text):
        return True
    squeezed = text.replace(" ", "")
    return any(phrase.replace(" ", "") in squeezed for phrase in INJECTION_TH)


def asks_for_private_contact(text: str) -> bool:
    return bool(CONTACT_TOPICS_EN.search(text)) or any(topic in text for topic in CONTACT_TOPICS_TH)


def classify(raw: str, text: str) -> str | None:
    """"blocked", "redirect", "greeting" or None when the question should go to the search."""
    if is_injection(raw, text):
        return "blocked"
    if asks_for_private_contact(text):
        return "redirect"
    if is_greeting(text):
        return "greeting"
    return None


def reply_in_thai(text: str) -> bool:
    return has_thai(text)


def message(kind: str, thai: bool, email: str) -> str:
    where_th = f"ที่อีเมล {email}" if email else "ผ่านช่องทางติดต่อบนหน้าเว็บ"
    where_en = f"by email at {email}" if email else "through the contact links on this site"
    if kind == "blocked":
        return (
            "ขออภัย ฉันตอบได้เฉพาะเรื่องผลงาน ประสบการณ์ และบทความที่อยู่บนเว็บนี้ ลองถามเรื่องเหล่านั้นได้เลย"
            if thai
            else "Sorry, I can only answer questions about the projects, experience and articles on this site. "
            "Feel free to ask about those."
        )
    if kind == "redirect":
        return (
            f"เรื่องเงินเดือน ค่าจ้าง และช่องทางส่วนตัว ขอคุยกันโดยตรงจะดีกว่า ติดต่อได้{where_th}"
            if thai
            else f"Pay and personal contact details are best discussed directly. You can reach out {where_en}."
        )
    if kind == "greeting":
        return (
            "สวัสดีครับ ถามเกี่ยวกับผลงาน ประสบการณ์การทำงาน หรือบทความได้เลย เช่น \"มีผลงานอะไรบ้าง\" หรือ \"ใช้เทคโนโลยีอะไรบ้าง\""
            if thai
            else "Hello! Ask about the projects, work experience or articles, for example \"What projects do you have?\" "
            "or \"Which technologies do you use?\""
        )
    if kind == "no_answer":
        return (
            f"ไม่พบข้อมูลเรื่องนี้บนเว็บ ถ้าสนใจสอบถามเพิ่มเติม ติดต่อได้{where_th}"
            if thai
            else f"I could not find that on this site. If you would like to know more, you can reach out {where_en}."
        )
    if kind == "fallback":
        return (
            "ตอนนี้สรุปคำตอบให้ไม่ได้ ลองดูส่วนที่เกี่ยวข้องด้านล่างได้เลย"
            if thai
            else "I cannot write a summary right now. These are the parts of the site that match your question."
        )
    if kind == "rate_limited":
        return (
            f"วันนี้ถามครบจำนวนที่กำหนดแล้ว กรุณาลองใหม่พรุ่งนี้ หรือติดต่อโดยตรง{where_th}"
            if thai
            else f"The question limit for today has been reached. Please try again tomorrow, or reach out {where_en}."
        )
    return ""

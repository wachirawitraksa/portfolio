"""English for the admin pages. The pages are written in Thai.

Two things are translated, and never anything the owner typed:
  * the TEMPLATE SOURCE, before Jinja compiles it. Everything Thai in a template file is fixed text by
    definition, so changing it cannot touch the owner's data (which only arrives when the page is drawn).
  * TEXT THAT PYTHON MAKES (error messages, status labels, the to-do list), through the `tr` filter, which
    translates a whole string only when it matches an entry; anything else passes through unchanged.

Each entry maps a Thai phrase to its English; entries are matched longest first, so a whole sentence wins over
the words inside it. A pattern may hold {0}, {1} ... for numbers or names that change ("มีผลงานฉบับร่าง {0} ชิ้น"),
which lets the English reorder them.

Rules for the English text: no double quotes and no apostrophes (they sit inside HTML attributes and
JavaScript strings; use the typographic apostrophe instead), and nothing that HTML would need escaped. A test
checks that every admin page, drawn in English from English-only data, has no Thai left in it."""
import re

# fmt: off
CATALOG: dict[str, str] = {
    # --- words and short labels ------------------------------------------------------------------
    "หลังบ้าน": "Admin", "ผู้ดูแลเว็บ": "Site owner", "ภาพรวม": "Overview", "เนื้อหา": "Content", "จัดหมวด": "Categories",
    "ช่องถามตอบ": "Question box", "ระบบ": "System", "ผลงาน / รายการ": "Projects / items", "ผลงาน": "Projects",
    "ประวัติการทำงาน": "Work history", "ประวัติการศึกษา": "Education", "บทความ": "Articles", "ข้อมูลส่วนตัว": "Profile",
    "ประเภท": "Categories", "ชนิด": "Kinds", "tag เทคโนโลยี": "Technology tags", "Tag เทคโนโลยี": "Technology tags",
    "สถานะและลองถาม": "Status and try a question", "คำถามจากผู้เข้าชม": "Visitor questions", "glossary": "Glossary",
    "ตั้งค่าการแสดงผล": "Display settings", "ถังขยะ": "Trash", "บัญชีและความปลอดภัย": "Account and security",
    "session ที่ล็อกอินอยู่": "Active sessions", "สร้างใหม่": "Create new", "กลุ่มคำ glossary": "Glossary group",
    "ออกจากระบบ": "Log out", "เมนูหลังบ้าน": "Admin menu", "ย่อ/ขยายเมนู": "Collapse / expand menu",
    "สลับธีมสว่าง/มืด": "Switch light / dark theme", "ภาษา": "Language",
    "บันทึก": "Save", "ยกเลิก": "Cancel", "แก้ไข": "Edit", "ลบ": "Delete", "ลบถาวร": "Delete for good", "กู้คืน": "Restore",
    "ซ่อน": "Hide", "แสดง": "Show", "เพิ่ม": "Add", "เอาออก": "Remove", "อัปโหลด": "Upload", "ลองค้น": "Try search",
    "ลองค้นหา": "Search", "ลองถาม": "Try a question", "ลองถาม (ดูว่าระบบหาเจออะไร มั่นใจแค่ไหน ยังไม่เรียกโมเดล)": "Try a question",
    "ขยับขึ้น": "Move up", "ขยับลง": "Move down", "เลื่อนขึ้น": "Move up", "เลื่อนลง": "Move down",
    "ซ่อนอยู่": "Hidden", "ถูกซ่อน": "Hidden", "สร้างข้อมูลใหม่": "Rebuild", "เผยแพร่": "Published", "ร่าง": "Draft", "หน้าแรก": "Home page", "ขึ้นหน้าแรก": "Show on the home page",
    "เอาออกจากหน้าแรก": "Remove from the home page", "ชื่อ": "Name", "ไทย": "Thai", "ชื่อไทย": "Thai name", "ชื่ออังกฤษ": "English name",
    "ชื่อภาษาไทย": "Name in Thai", "ชื่อภาษาอังกฤษ": "Name in English", "ปี": "Year", "สถานะ": "Status", "รายการ": "items",
    "ชิ้น": "items", "ครั้ง": "times", "วัน": "days", "คะแนน": "Score", "ที่มา": "Source", "แหล่งที่มา": "Sources", "เสียง": "Sound",
    "ล่าสุด": "Latest", "ผล": "Result", "คำถาม": "Question", "คำ": "Word", "ผลลัพธ์": "Result", "โจทย์": "Problem",
    "บทบาท": "Role", "สิ่งที่ทำ": "What I did", "รายละเอียด": "Details", "รูป": "Image", "รูปภาพ": "Images", "รูปปก": "Cover image",
    "รูป #": "Image #", "ลิงก์": "Link", "อีเมล": "Email", "รหัสผ่าน": "Password", "ที่อยู่": "Location", "ที่ทำงาน": "Workplace",
    "ช่วงเวลา": "Period", "วันที่": "Date", "ผู้ออก": "Issuer", "หมายเหตุ": "Note", "ตั้งค่า": "Settings", "ปกติ": "OK",
    "ปิด": "Off", "เปิด": "On", "สูง": "High", "กลาง": "Medium", "ต่ำ / ไม่เจอ": "Low / not found", "ทั้งหมด": "All",
    "ตอบไม่ได้": "Unanswered", "ถูกบล็อก": "Blocked", "ทักทาย": "Greeting", "ล้าสมัย": "Out of date", "แล้ว": "done",
    "ใหม่": "New", "ควรทำ": "To do", "แนะนำ": "Suggested", "ไปแปล": "Translate", "เปิดถังขยะ": "Open trash",
    "ดูสถานะ": "View status", "ดูคำถาม": "View questions", "ดูรายการ": "View list", "ดูบทความ": "View articles",
    "ดูอีก": "Show", "เพิ่มรูป": "Add images", "กรอกข้อมูล": "Fill in", "เพิ่มผลงาน": "Add a project",
    "+ ผลงาน": "+ Project", "+ บทความ": "+ Article", "+ ประวัติการทำงาน": "+ Work history", "+ เพิ่ม": "+ Add",
    "← กลับไปรายการ": "← Back to the list", "ที่ลบแล้ว": "Deleted", "ในถังขยะ": "In the trash",
    "ระดับ": "Level", "สถาบัน": "Institution", "วุฒิ": "Degree", "สาขา": "Field", "เกรด": "Grade", "สรุป": "Summary",
    "รูปแบบ": "Type", "เวลา": "Time", "ข้อ ·": "item ·", "เริ่มเมื่อ": "Started", "เบราว์เซอร์": "Browser", "เพิกถอน": "Revoke",
    "(เครื่องนี้)": "(this device)", "งานประจำ": "Full-time", "พาร์ทไทม์": "Part-time", "สัญญาจ้าง": "Contract",
    "ฟรีแลนซ์": "Freelance", "ฝึกงาน": "Internship", "อื่น ๆ": "Other", "กิจกรรม / งานสั้น": "Event / short gig",
    "มัธยมศึกษา": "High school", "ปริญญาตรี": "Bachelor’s degree", "ปริญญาโท": "Master’s degree", "ปริญญาเอก": "Doctorate",
    "อาชีวศึกษา (ปวช. / ปวส.)": "Vocational", "ประกาศนียบัตร / หลักสูตรระยะสั้น": "Certificate / short program",
    "ผลงาน / ใบเซอร์ / รายการ": "Projects / certificates / items", "รูปภาพ / ภาพหน้าจอ": "Images / screenshots",
    "ใบเซอร์ / รางวัล / คอร์ส": "Certificates / awards / courses", "ช่องทางติดต่อ": "Contact links",
    "ช่องทางติดต่ออื่น": "Other contact links", "ชื่อช่องทาง": "Link name", "+ เพิ่มช่องทาง": "+ Add a link",
    "ยังไม่มีช่องทางติดต่อ": "No contact links yet", "ไม่ตอบสนอง": "not responding", "ตั้งค่าแล้ว": "set up", "ยังไม่ตั้งค่า": "not set up",
    "ตรงกับเนื้อหา": "matches the content", "ยังไม่ได้สร้าง": "not built yet", "ที่เก็บไฟล์": "File storage", "ฐานข้อมูล": "Database",
    "โมเดลตอบคำถาม": "Answer model", "ข้อมูลช่องถามตอบ": "Question box data", "สถานะระบบ": "System status",
    "สิ่งที่ต้องดูแล": "To look after", "ผลงานที่เผยแพร่": "Published projects", "บทความที่เผยแพร่": "Published articles",
    "รูปภาพทั้งหมด": "All images", "กลุ่มคำใน glossary": "Glossary groups", "ในถังขยะ": "In the trash",
    # --- page titles and headings ------------------------------------------------------------------------
    "เข้าสู่ระบบ": "Log in", "เข้าสู่ระบบหลังบ้าน": "Admin log in", "รหัส TOTP 6 หลัก": "6-digit TOTP code", "รหัส TOTP": "TOTP code",
    "เข้าสู่ระบบด้วย GitHub": "Log in with GitHub", "รายการทั้งหมด": "All items", "ถังขยะ: รายการ": "Trash: items",
    "ถังขยะ: บทความ": "Trash: articles", "ถังขยะ: ประเภทผลงาน": "Trash: categories", "ถังขยะ: ชนิดของรายการ": "Trash: kinds",
    "ถังขยะ: tag เทคโนโลยี": "Trash: technology tags", "ถังขยะ: glossary": "Trash: glossary",
    "ถังขยะ: ประวัติการทำงาน": "Trash: work history", "ถังขยะ: ประวัติการศึกษา": "Trash: education",
    "ประเภทผลงาน": "Project categories", "ชนิดของรายการ": "Kinds of items", "glossary (คำที่มีความหมายเดียวกัน)": "Glossary (words that mean the same)",
    "ช่องถามตอบ (RAG)": "Question box (RAG)", "ข้อมูลส่วนตัว (หน้าแรก)": "Profile (home page)", "บัญชี": "Account",
    "ตั้งค่าการแสดงผล": "Display settings", "รหัส TOTP ใหม่": "New TOTP code", "ผมเป็นใคร": "Who I am", "รูปของผม": "My photo",
    "CV (PDF)": "CV (PDF)", "จำนวนที่แสดงในแต่ละส่วน": "How many items each section shows", "วิธีการทำงาน": "How I work",
    "เปลี่ยนรหัสผ่าน": "Change password", "รีเซ็ต TOTP": "Reset TOTP", "เปิดใช้ TOTP": "Turn on TOTP", "GitHub": "GitHub",
    "แก้ไขรายการ": "Edit item", "เพิ่มรายการ": "Add item", "แก้ไขบทความ": "Edit article", "เพิ่มบทความ": "Add article",
    "แก้ไขประเภท": "Edit category", "เพิ่มประเภท": "Add category", "แก้ไขชนิด": "Edit kind", "เพิ่มชนิด": "Add kind",
    "แก้ไข tag": "Edit tag", "เพิ่ม tag": "Add tag", "แก้ไขกลุ่มคำ": "Edit word group", "เพิ่มกลุ่มคำ": "Add word group",
    "แก้ไขประวัติการทำงาน": "Edit work history", "เพิ่มประวัติการทำงาน": "Add work history",
    "แก้ไขประวัติการศึกษา": "Edit education", "เพิ่มประวัติการศึกษา": "Add education",
    "+ เพิ่มรายการ": "+ Add item", "+ เพิ่มบทความ": "+ Add article", "+ เพิ่มประเภท": "+ Add category", "+ เพิ่มชนิด": "+ Add kind",
    "+ เพิ่ม tag": "+ Add tag", "+ เพิ่มกลุ่มคำ": "+ Add word group", "+ เพิ่มประวัติการทำงาน": "+ Add work history",
    "+ เพิ่มประวัติการศึกษา": "+ Add education", "พิมพ์ชื่อก่อน": "Start with the name", "ชื่อและที่มา": "Name and source",
    "ตำแหน่งและที่ทำงาน": "Position and workplace", "ตำแหน่ง / หัวข้อ และที่ทำงาน": "Position / title and workplace",
    "สถาบันและหลักสูตร": "Institution and program", "ชื่อบทความ ·": "Article title ·", "ชื่อบทความ": "Article title",
    "ตำแหน่ง / หัวข้อ": "Position / title", "ตำแหน่ง / หัวข้อ ·": "Position / title ·", "สถาบัน / สาขา": "Institution / field",
    "ที่ทำงาน / ผู้จัด": "Workplace / organizer", "วุฒิ / ชื่อหลักสูตร": "Degree / program name", "สาขา / วิชาเอก": "Field / major",
    "เกรด / เกียรตินิยม": "Grade / honors", "ระดับการศึกษา": "Level of education", "คำที่เท่ากัน": "Equal words", "คำที่มีความหมายเดียวกัน": "Words that mean the same",
    "ชื่อย่อ / ชื่อเรียกอื่น": "Short names / other names", "ช่องที่ใช้": "Fields used", "ช่องที่ใช้กับชนิดนี้": "Fields this kind uses",
    "เฉพาะช่องพื้นฐาน": "Basic fields only", "ข้อมูลที่ใช้ค้นหา": "Search data", "คำที่ใช้ค้น:": "Search terms:", "ความมั่นใจ:": "Confidence:",
    "ข้อมูลที่ใช้ค้นหา": "Search data", "รายละเอียดเพิ่มเติม": "More details", "การแสดงผล": "Display", "ซ่อนจากหน้าเว็บ": "Hide from the website",
    "ลิงก์และข้อมูลอื่น": "Links and other information", "ช่วงเวลา (มีวันเริ่มและวันสิ้นสุด)": "Date range (with a start and an end date)",
    "ยังทำอยู่": "Still working", "วันเดียว": "Single day", "(วันเดียว)": "(single day)", "ยังเรียนอยู่": "Still studying",
    "เรียนจบแล้ว (มีเดือนที่สิ้นสุด)": "Finished (with an end month)", "– ปัจจุบัน": "– present", "วันที่เริ่ม": "Start date",
    "วันที่สิ้นสุด": "End date", "สิ้นสุด (เดือน-ปี)": "End (month-year)", "เริ่มเรียน (เดือน-ปี)": "Start (month-year)",
    "เริ่มงาน (เดือน-ปี)": "Start (month-year)", "วันที่เผยแพร่": "Publish date", "วันที่ได้รับ": "Date received",
    "ลิงก์ตรวจสอบ": "Verification link", "ลิงก์บทความ": "Article link", "ชื่อแพลตฟอร์ม": "Platform name",
    "ลิงก์ repo": "Repo link", "ลิงก์ demo": "Demo link", "ลิงก์ demo ที่กดใช้ได้จริง": "Working demo link", "ลิงก์ repo / demo": "Repo / demo links",
    "ลิงก์ไปแพลตฟอร์มอื่น": "Link to another platform", "เขียนในเว็บนี้": "Written on this site", "ที่อยู่ / อยู่ที่ไหน": "Location",
    "แนะนำตัวสั้น ๆ": "Short introduction", "อีเมลติดต่อ": "Contact email", "รูปโปรไฟล์": "Profile photo",
    "เทคโนโลยี / tag": "Technology / tags", "เครื่องมือที่ใช้ / tag": "Tools used / tags", "หัวข้อ / tag": "Topics / tags",
    "เครื่องมือ": "Tools", "เทคโนโลยี": "Technology", "เรื่องราว (โจทย์ สิ่งที่ทำ บทบาท ผลลัพธ์ สิ่งที่ได้เรียน)": "Story (problem, what I did, role, result, what I learned)",
    "ใบเซอร์ / รางวัล (ผู้ออก วันที่ได้รับ ลิงก์ตรวจสอบ)": "Certificate / award (issuer, date, verification link)",
    "โจทย์ / ทำขึ้นมาเพราะอะไร / แก้ปัญหาอะไรให้ใคร": "Problem / why it was made / whose problem it solves",
    "บทบาทของผม (ถ้าทำกับคนอื่น)": "My role (if made with others)", "ผลลัพธ์ที่วัดได้ (ใส่เฉพาะตัวเลขที่ตรวจสอบได้)": "Measurable result (only numbers that can be checked)",
    "สิ่งที่ได้เรียน / ถ้าทำใหม่จะต่างไปอย่างไร": "What I learned / what I would do differently", "สิ่งที่ยังอยากทำต่อ": "What I want to do next",
    "ชนิดนี้ไม่ใช้ช่อง:": "This kind does not use:", "ลิงก์ repo / demo": "Repo / demo links", "ปี": "Year",
    # --- sentences and hints -------------------------------------------------------------------------------
    "(กรอกทีหลังได้)": "(can be filled in later)", "(ไม่บังคับ)": "(optional)", "(เช่น Medium, dev.to)": "(for example Medium, dev.to)",
    "(เช่น ผลงาน ใบเซอร์ รางวัล)": "(for example project, certificate, award)",
    "(ข้อมูลที่เคยกรอกยังเก็บไว้ ไม่หาย)": "(what was typed there is kept, not lost)",
    "ยังไม่มีชนิด": "No kinds yet", "เพิ่มชนิดก่อน": "Add a kind first", "ยังไม่ได้กรอก": "not filled in", "ยังไม่ได้แปล": "not translated:",
    "ยังไม่มีรูป": "No photo yet", "บันทึกรายการก่อน แล้วจึงเพิ่มรูปได้": "Save the item first, then you can add images",
    "เพิ่มรูป": "Add images", "(JPEG, PNG, GIF, WebP · เลือกได้หลายไฟล์)": "(JPEG, PNG, GIF, WebP · several files at once)",
    "บันทึกคำบรรยาย": "Save caption", "คำบรรยาย · ไทย": "Caption · Thai", "ตั้งเป็นรูปปก": "Set as cover", "รูปที่ลบแล้ว": "Deleted images",
    "กู้คืนรูป #": "Restore image #", "ชื่อเรียกอื่น (หนึ่งบรรทัดต่อหนึ่งชื่อ ใช้เป็น glossary ให้ระบบถามตอบหาเจอ)": "Other names (one per line, used as glossary so the question box can find it)",
    "พิมพ์ชื่อ แล้วกด Enter หรือ + เพิ่ม": "Type a name, then press Enter or + Add", "(ไม่เกิน": "(at most", "พิมพ์ชื่อใหม่แล้วกดเพิ่มได้เลย)": "type a new name and press Add)",
    "(พิมพ์ชื่อใหม่แล้วกดเพิ่มได้เลย)": "(type a new name and press Add)", "ครบแล้ว (": "Limit reached (", "ตัวอักษร": "characters", "ตัวอักษร)": "characters)",
    "(อย่างน้อย": "(at least", "(ใช้เมื่อที่มาเป็น \"ลิงก์ไปแพลตฟอร์มอื่น\")": "(used when the source is a link to another platform)",
    "(ใช้เมื่อที่มาเป็น \"เขียนในเว็บนี้\" · เขียนด้วย Markdown ได้)": "(used when the source is written on this site · Markdown works)",
    "(เว้นว่างได้เฉพาะ \"กิจกรรม / งานสั้น\")": "(may be empty only for event / short gig)",
    "(หนึ่งบรรทัดต่อหนึ่งข้อ · ไม่ใส่รายละเอียดลับของบริษัท)": "(one item per line · no confidential company details)",
    "สิ่งที่ทำ (หนึ่งบรรทัดต่อหนึ่งข้อ · ไม่ใส่รายละเอียดลับของบริษัท)": "What I did (one item per line · no confidential company details)",
    "(ใส่เฉพาะที่ตรวจสอบได้จากใบทรานสคริปต์)": "(only what a transcript shows)",
    "(หนึ่งบรรทัดต่อหนึ่งข้อ เช่น หัวข้อโครงงาน รางวัล กิจกรรม · ไม่บังคับ)": "(one item per line, such as thesis topic, awards, activities · optional)",
    "(หนึ่งบรรทัดต่อหนึ่งคำ ไทยหรืออังกฤษก็ได้ อย่างน้อย 2 คำ)": "(one word per line, Thai or English, at least 2 words)",
    "งานยาวเป็นปีเลือก \"ช่วงเวลา\" · กิจกรรมสั้นที่แทรกอยู่ระหว่างงานยาวเลือก \"วันเดียว\" ได้ ไทม์ไลน์เรียงตามวันที่เริ่ม": "A job that lasts years: choose Date range. A short activity inside a long job: choose Single day. The timeline is ordered by start date.",
    "กรอกได้ทีละภาษา ช่องที่ยังว่างจะมีป้ายเตือนในรายการ และหน้าเว็บจะแสดงอีกภาษาแทน": "You can fill in one language at a time. An empty one gets a warning in the list, and the website shows the other language instead.",
    "ตอนเพิ่มหรือแก้ไขรายการ ฟอร์มจะแสดงเฉพาะช่องที่ติ๊กไว้ตามชนิดที่เลือก (ชื่อ ประเภท ชื่อเรียกอื่น และสถานะแสดงเสมอ) ข้อมูลที่เคยกรอกในช่องที่ซ่อนจะไม่หาย": "When adding or editing an item, the form shows only the fields ticked for the chosen kind (name, category, other names and status always show). Data typed in a hidden field is kept.",
    "ชื่อ (เช่น PostgreSQL)": "Name (for example PostgreSQL)", "ชื่อย่อ / ชื่อเรียกอื่น (หนึ่งบรรทัดต่อหนึ่งชื่อ เช่น pg, postgres)": "Short names / other names (one per line, such as pg, postgres)",
    "ระบบถามตอบ (RAG) ใช้ชื่อเหล่านี้ช่วยหาผลงานที่เกี่ยวข้อง": "The question box (RAG) uses these names to find related projects.",
    "ช่วยให้ช่องถามตอบหาเจอแม้ผู้ถามใช้คำคนละคำ เช่น สต็อก = stock = inventory · tag เทคโนโลยีและชื่อเรียกอื่นของผลงานเป็น glossary ให้อัตโนมัติอยู่แล้ว": "Helps the question box find answers even when the visitor uses a different word, for example stock = inventory. Technology tags and other project names already count as glossary automatically.",
    "ยังไม่มีกลุ่มคำ": "No word groups yet", "ยังไม่มีรายการ กด \"เพิ่มรายการ\" เพื่อเริ่มต้น": "No items yet. Press Add item to start.",
    "ยังไม่มีบทความ กด \"เพิ่มบทความ\" เพื่อเริ่มต้น": "No articles yet. Press Add article to start.",
    "ยังไม่มีประเภทผลงาน กด \"เพิ่มประเภท\" เพื่อเริ่มต้น": "No categories yet. Press Add category to start.",
    "ยังไม่มีชนิด กด \"เพิ่มชนิด\" เพื่อเริ่มต้น (เช่น ผลงาน ใบเซอร์ รางวัล คอร์ส กิจกรรม)": "No kinds yet. Press Add kind to start (for example project, certificate, award, course, activity).",
    "ยังไม่มี tag กด \"เพิ่ม tag\" เพื่อเริ่มต้น": "No tags yet. Press Add tag to start.",
    "ยังไม่มีประวัติการศึกษา กด \"เพิ่มประวัติการศึกษา\" เพื่อเริ่มต้น": "No education yet. Press Add education to start.",
    "ยังไม่มีประวัติการทำงาน กด \"เพิ่มรายการ\" เพื่อเริ่มต้น": "No work history yet. Press Add item to start.",
    "ยังไม่มีรายการ กด \"เพิ่มรายการ\" เพื่อเริ่มต้น": "No items yet. Press Add item to start.",
    "ถังขยะว่างอยู่": "The trash is empty",
    # --- profile and settings --------------------------------------------------------------------------------
    "อัปโหลดรูป": "Upload a photo", "เปลี่ยนรูป": "Change photo", "เอารูปออก": "Remove photo", "อัปโหลดไฟล์": "Upload a file", "เปลี่ยนไฟล์": "Change file",
    "เอาไฟล์ออก": "Remove file", "ยังไม่มีไฟล์": "No file yet", "ผลงานที่ใช้เล่า": "Project used for the story", "— ไม่แสดง —": "— Hide —",
    "(ยังไม่เผยแพร่)": "(not published yet)", "ผลงานเด่นบนหน้าแรก": "Featured projects on the home page", "จำนวนชิ้นที่ขึ้นหน้าแรก": "How many items go on the home page",
    "คลังผลงาน": "Project library", "จำนวนชิ้นต่อหนึ่งครั้งที่โหลด": "Items per load", "จำนวนบทความต่อหนึ่งครั้งที่โหลด": "Articles per load",
    ": ต้องเป็นตัวเลข": ": must be a number", "หน้าเว็บเล่าวิธีการทำงานของผมผ่านผลงานจริงหนึ่งชิ้น เลือกชิ้นที่อยากให้ใช้เล่า (ต้องเผยแพร่แล้วจึงจะขึ้นหน้าเว็บ) · ไม่เลือก = ไม่แสดงส่วนนี้": "The website tells how I work through one real project. Choose which one (it must be published to show). Choose none to hide the section.",
    "แนะนำตัว": "Introduction", "ไม่พบผลงานที่เลือกสำหรับ \"วิธีการทำงาน\"": "The project chosen for How I work was not found",
    # --- account ---------------------------------------------------------------------------------------------
    "รหัสผ่านปัจจุบัน": "Current password", "รหัสผ่านใหม่": "New password", "พิมพ์รหัสผ่านใหม่อีกครั้ง": "Type the new password again",
    "เปลี่ยนแล้วทุกเครื่องที่ล็อกอินอยู่ (รวมเครื่องนี้) จะถูกออกจากระบบ ต้องล็อกอินใหม่": "After changing it, every device that is logged in (this one too) is logged out and must log in again.",
    "เปิดใช้อยู่": "On", "ยังไม่ได้เปิดใช้": "Not turned on", "· การรีเซ็ตจะสร้างรหัสลับใหม่ (รหัสเดิมใช้ไม่ได้) และให้ทุกเครื่องออกจากระบบ": "· Resetting makes a new secret (the old one stops working) and logs every device out.",
    "ยังไม่ได้ตั้งค่า GitHub OAuth (GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET / GITHUB_REDIRECT_URI)": "GitHub OAuth is not set up (GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET / GITHUB_REDIRECT_URI)",
    "เชื่อมกับบัญชี GitHub แล้ว ล็อกอินด้วยปุ่ม GitHub ได้": "Linked to a GitHub account. You can log in with the GitHub button.",
    "เชื่อมบัญชี GitHub ของคุณ เพื่อล็อกอินด้วยปุ่ม GitHub ได้ (ใช้ได้เฉพาะบัญชีที่เชื่อมไว้ ระบบไม่สร้างบัญชีใหม่ให้ใคร)": "Link your GitHub account to log in with the GitHub button (only a linked account works; no new accounts are ever created).",
    "ยกเลิกการเชื่อม": "Unlink", "เชื่อมบัญชี GitHub": "Link GitHub account", "เชื่อมบัญชี GitHub แล้ว": "GitHub account linked",
    "ยกเลิกการเชื่อม GitHub แล้ว": "GitHub unlinked", "เชื่อมบัญชี GitHub ไม่สำเร็จ (ยืนยันกับ GitHub ไม่ผ่าน หรือบัญชีนี้ถูกใช้อยู่)": "Linking GitHub failed (GitHub did not confirm, or the account is already used)",
    "ทุกเครื่องถูกออกจากระบบแล้ว เพิ่มรหัสลับนี้ในแอป authenticator ก่อนล็อกอินใหม่": "Every device is logged out. Add this secret to your authenticator app before logging in again.",
    "หน้านี้แสดงครั้งเดียว": "This page is shown only once", "รหัสลับ": "Secret", "URI (สำหรับแอปที่นำเข้าจากลิงก์)": "URI (for apps that import from a link)",
    "ไปหน้าเข้าสู่ระบบ": "Go to log in", "ลองบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่": "Too many tries. Please wait a moment and try again.",
    "รหัสผ่านปัจจุบันไม่ถูกต้อง": "The current password is wrong", "รหัสผ่านใหม่ต้องยาวอย่างน้อย": "The new password must be at least",
    "รหัสผ่านใหม่สองช่องไม่ตรงกัน": "The two new password fields do not match", "อีเมล รหัสผ่าน หรือรหัส TOTP ไม่ถูกต้อง": "Email, password or TOTP code is wrong",
    "เข้าสู่ระบบด้วย GitHub ไม่สำเร็จ": "GitHub log in failed", "ไม่ตรงกับ": "does not match", "ออกจากระบบแล้ว": "Logged out",
    # --- trash ------------------------------------------------------------------------------------------------
    "ล้างถังขยะทั้งหมด (": "Empty the whole trash (", "ล้างเฉพาะหมวดนี้": "Empty this group only", "ลบถาวรแล้ว": "Deleted for good",
    "รายการที่ยังมีของอื่นใช้อยู่": "items that something else still uses", "· ข้าม": "· skipped", "ของรายการ #": "of item #",
    "กู้คืนแล้ว (รายการที่เผยแพร่ให้ผู้เข้าชมจะกลับมาเป็น \"ซ่อน\" ให้ตรวจก่อน)": "Restored (items visitors can see come back as Hidden so you can check them first)",
    "ของที่ลบจะมาอยู่ที่นี่ก่อน กู้คืนได้ · \"ลบถาวร\" ลบทั้งข้อมูลและไฟล์ในที่เก็บไฟล์ กู้คืนไม่ได้อีก": "Deleted things land here first and can be restored. Delete for good removes the data and the files in storage and cannot be undone.",
    "ลบรายการนี้ถาวร กู้คืนไม่ได้ ยืนยัน?": "Delete this item for good? It cannot be restored.",
    "ลบถาวรแล้ว": "Deleted for good",
    # --- question box admin ------------------------------------------------------------------------------------
    "ความมั่นใจ": "Confidence", "ลองถาม": "Try a question", "คำถาม": "Question", "ข้อมูลที่ใช้ค้นหา": "Search data",
    "สร้างข้อมูลสำหรับค้นหาใหม่": "Rebuild the search data", "สร้างข้อมูลสำหรับค้นหาใหม่แล้ว": "The search data was rebuilt",
    "ข้อมูลตรงกับเนื้อหาปัจจุบันแล้ว": "The data matches the current content", "ยังไม่มีข้อมูล กด \"สร้างใหม่\" เพื่อเริ่มต้น": "No data yet. Press Create new to start.",
    "ไม่พบข้อมูลที่ตรงกับคำถามนี้": "Nothing matches this question", "แก้แป้นพิมพ์เป็น:": "Keyboard fixed to:", "· เพิ่มจาก glossary:": "· added from glossary:",
    "· เสียง:": "· sound:", "ดูคำถามจากผู้เข้าชม (และที่ตอบไม่ได้) →": "See visitor questions (and unanswered ones) →", "จัดการ glossary →": "Manage glossary →",
    "← กลับไปหน้าช่องถามตอบ": "← Back to the question box", "ตอบ (มั่นใจสูง)": "Answered (high confidence)", "ตอบ (ไม่การันตี)": "Answered (not guaranteed)",
    "ไม่มีข้อมูลบนเว็บ": "Not on the website", "สรุปไม่ได้ (โมเดลไม่พร้อม)": "Could not summarize (model unavailable)", "เบนไปอีเมล": "Sent to email",
    "ถูกบล็อก / เบนไปอีเมล": "Blocked / sent to email", "ตอบไม่ได้และถูกถามซ้ำ": "Unanswered and asked again",
    "คำถามที่ตอบไม่ได้และถูกถามซ้ำ": "Unanswered questions that were asked again", "(เอาไปเติมเนื้อหา หรือเพิ่มใน glossary)": "(use them to add content or add to the glossary)",
    "ยังไม่มีคำถามในหมวดนี้": "No questions in this group yet", "เก็บล็อก": "Log kept for", "ลบล็อกแล้ว": "Log deleted:",
    "ลบล็อกที่เก่ากว่า": "Delete log older than", "ลบล็อกทั้งหมด": "Delete the whole log", "ลบล็อกคำถามทั้งหมดถาวร ยืนยัน?": "Delete the whole question log for good? Are you sure?",
    "(ดูว่าระบบหาเจออะไร มั่นใจแค่ไหน ยังไม่เรียกโมเดล)": "(see what the search finds and how sure it is; no model is called)",
    "ครั้ง · เรียกโมเดล": "times · model calls", "ครั้ง · ตอบจาก cache": "times · answered from cache",
    "24 ชั่วโมงที่ผ่านมา: ถาม": "Last 24 hours: asked", "ช่องถามตอบ 24 ชั่วโมงที่ผ่านมา": "Question box, last 24 hours",
    "ครั้ง · บันทึกคำถามพร้อมค่าแฮชของ IP (ไม่เก็บ IP จริง)": "times · questions are logged with a hash of the IP (the real IP is not kept)",
    "วัน (ตั้งที่ ASK_LOG_DAYS) แล้วลบเองเป็นระยะ · ตอนนี้มี": "days (set by ASK_LOG_DAYS), then deleted from time to time · there are now",
    "ตอบไม่ได้ 7 วันนี้": "Unanswered in the last 7 days",
    "สรุปสั้น ๆ ·": "Short summary ·", "ถาม": "Asked",
    "· บันทึกคำถามพร้อมค่าแฮชของ IP (ไม่เก็บ IP จริง)": "· questions are logged with a hash of the IP (the real IP is not kept)",
    "ช่องถามตอบอ่านเฉพาะผลงาน (เผยแพร่แล้ว), ประวัติการทำงาน (ไม่ซ่อน), บทความ (เผยแพร่แล้ว) และข้อมูลส่วนตัว หลังแก้เนื้อหาต้องกดสร้างใหม่ (glossary มีผลทันที ไม่ต้องสร้างใหม่)": "The question box reads only projects (published), work history (not hidden), education (not hidden), articles (published) and the profile. After editing content, press rebuild (the glossary takes effect at once).",
    "เนื้อหาเปลี่ยนไปหลังสร้างครั้งล่าสุด (": "The content changed since the last build (", "ชิ้น · สร้างเมื่อ": "items · built at",
    "ชิ้น) กดสร้างใหม่เพื่อให้ช่องถามตอบเห็นเนื้อหาล่าสุด": "items). Rebuild so the question box sees the latest content.",
    "สร้างข้อมูลช่องถามตอบใหม่": "Rebuild the question box data", "เพิ่มใหม่": "added", "ถูกแก้": "edited", "ถูกลบ": "removed",
    # --- dashboard -----------------------------------------------------------------------------------------------
    "สถานะของเว็บและสิ่งที่ต้องดูแล": "The state of the site and what needs attention", "ไม่มีอะไรค้าง ทุกอย่างเรียบร้อย": "Nothing is waiting. All is in order.",
    "ผลงานที่ยังแปลไม่ครบสองภาษา": "projects not fully translated",
    # --- Python messages (validation, notices) --------------------------------------------------------------------
    "ต้องกรอกชื่ออย่างน้อยหนึ่งภาษา": "Enter a name in at least one language", "ต้องกรอกชื่อ tag": "Enter a tag name",
    "ต้องกรอกที่ทำงาน": "Enter the workplace", "ต้องกรอกตำแหน่ง / หัวข้ออย่างน้อยหนึ่งภาษา": "Enter the position / title in at least one language",
    "ต้องกรอกชื่อบทความอย่างน้อยหนึ่งภาษา": "Enter the article title in at least one language", "ต้องกรอกชื่อสถาบันอย่างน้อยหนึ่งภาษา": "Enter the institution in at least one language",
    "ต้องกรอกชื่อแพลตฟอร์ม เช่น Medium": "Enter the platform name, for example Medium", "ต้องกรอกชื่อช่องทาง เช่น GitHub": "Enter the link name, for example GitHub",
    "ต้องเลือกวันที่": "Choose a date", "ต้องเลือกวันที่เริ่ม": "Choose a start date", "ต้องเลือกวันที่สิ้นสุด": "Choose an end date",
    "ต้องเลือกเดือนที่เริ่มเรียน": "Choose the start month", "ต้องเลือกเดือนที่สิ้นสุด": "Choose the end month",
    "วันที่สิ้นสุดต้องไม่ก่อนวันที่เริ่ม": "The end date must not be before the start date", "เดือนที่สิ้นสุดต้องไม่ก่อนเดือนที่เริ่ม": "The end month must not be before the start month",
    "วันที่ไม่ถูกต้อง": "The date is not valid", "ช่วงเวลาไม่ถูกต้อง": "The period is not valid", "รูปแบบงานไม่ถูกต้อง": "The type of work is not valid",
    "ระดับการศึกษาไม่ถูกต้อง": "The level of education is not valid", "สถานะไม่ถูกต้อง": "The status is not valid", "ชนิดบทความไม่ถูกต้อง": "The article source is not valid",
    "อีเมลไม่ถูกต้อง": "The email is not valid", "ไม่พบชนิดที่เลือก": "The chosen kind was not found",
    "ลิงก์ต้องขึ้นต้นด้วย http:// หรือ https://": "The link must start with http:// or https://", "ลิงก์บทความต้องขึ้นต้นด้วย http:// หรือ https://": "The article link must start with http:// or https://",
    "บทความที่เขียนในเว็บต้องมีเนื้อหาอย่างน้อยหนึ่งภาษา": "An article written on this site needs content in at least one language",
    "ปีต้องเป็นตัวเลข เช่น 2025": "The year must be a number, for example 2025", "ต้องขึ้นต้นด้วย http:// หรือ https://": "must start with http:// or https://",
    "เลือกประเภทได้ไม่เกิน": "You can choose at most", "ใส่คำที่มีความหมายเดียวกันอย่างน้อย": "Enter words that mean the same, at least",
    "ไฟล์ใหญ่เกิน": "The file is larger than", "รับเฉพาะไฟล์ JPEG, PNG, GIF หรือ WebP": "Only JPEG, PNG, GIF or WebP files are accepted", "CV ต้องเป็นไฟล์ PDF": "The CV must be a PDF file",
    "ลบไม่ได้ เพราะยังมีผลงาน": "Cannot delete: there are still projects in this category (", "ลบไม่ได้ เพราะยังมีรายการ": "Cannot delete: there are still items of this kind (",
    "เขียนในเว็บนี้": "Written on this site", "ต้องเป็นตัวเลข": "must be a number",
}
# fmt: on

# Sentences with numbers or names inside. {0}, {1} are filled from the Thai text; the English may reorder them.
PATTERNS: dict[str, str] = {
    "{0} – ปัจจุบัน": "{0} – present",
    "{0}ต้องขึ้นต้นด้วย http:// หรือ https://": "{0} must start with http:// or https://",
    "มีผลงานฉบับร่าง {0} ชิ้นที่ยังไม่เผยแพร่": "{0} draft project(s) not published yet",
    "มีบทความฉบับร่าง {0} ชิ้น": "{0} draft article(s)",
    "ผลงานที่เผยแพร่แล้วแต่ยังไม่มีรูป {0} ชิ้น": "{0} published project(s) without an image",
    "{0}ที่ยังแปลไม่ครบสองภาษา {1} รายการ": "{0}: {1} item(s) not fully translated into both languages",
    "ข้อมูลส่วนตัวหน้าแรกยังไม่ครบ: {0}": "The home page profile is incomplete: {0}",
    "ข้อมูลช่องถามตอบล้าสมัย ({0} ชิ้น)": "The question box data is out of date ({0} item(s))",
    "มีคำถามที่ตอบไม่ได้ {0} ข้อใน 7 วันนี้ (เอาไปเติมเนื้อหาได้)": "{0} unanswered question(s) in the last 7 days (use them to add content)",
    "ยังไม่มีผลงาน เริ่มเพิ่มชิ้นแรกได้เลย": "No projects yet. Add the first one.",
    "ยังไม่ได้ตั้ง GEMINI_API_KEY ช่องถามตอบจึงตอบแบบพาไปอ่านส่วนที่เกี่ยวข้อง (ยังไม่สรุปคำตอบ)": "GEMINI_API_KEY is not set, so the question box only points to the related parts of the site (no written answers yet)",
    "มีของในถังขยะ {0} รายการ": "{0} item(s) in the trash",
    "{0}ที่ไม่ตอบสนอง": "{0} not responding",
    "{0}ไม่ตอบสนอง": "{0} not responding",
    "ฐานข้อมูล และ ที่เก็บไฟล์ไม่ตอบสนอง": "The database and the file storage are not responding",
    "ฐานข้อมูลไม่ตอบสนอง": "The database is not responding", "ที่เก็บไฟล์ไม่ตอบสนอง": "The file storage is not responding",
    "ลบถาวรแล้ว {0} รายการ": "{0} item(s) deleted for good",
    "ลบถาวรแล้ว {0} รายการ · ข้าม {1} รายการที่ยังมีของอื่นใช้อยู่": "{0} item(s) deleted for good · {1} skipped because something else still uses them",
    "ลบ{0}ทั้งหมดในถังขยะถาวร ({1} รายการ) ยืนยัน?": "Delete all of {0} in the trash for good ({1} items)? Are you sure?",
    "ลบทุกอย่างในถังขยะถาวร ({0} รายการ) กู้คืนไม่ได้ ยืนยัน?": "Delete everything in the trash for good ({0} items)? It cannot be restored.",
    "ล้างถังขยะทั้งหมด ({0})": "Empty the whole trash ({0})",
    "ทั้งหมด {0} ชิ้น · สร้างเมื่อ {1}": "{0} items in total · built at {1}",
    "ลบล็อกแล้ว {0} รายการ": "{0} logged question(s) deleted",
    "เก็บล็อก {0} วัน (ตั้งที่ ASK_LOG_DAYS) แล้วลบเองเป็นระยะ · ตอนนี้มี {1} รายการ": "Log kept for {0} days (set by ASK_LOG_DAYS) and cleaned up from time to time · {1} logged now",
    "ลบล็อกที่เก่ากว่า {0} วัน": "Delete log older than {0} days",
    "ถาม {0} ครั้ง · เรียกโมเดล {1} ครั้ง": "Asked {0} times · model called {1} times",
    "ตอบไม่ได้ 7 วันนี้ {0} ข้อ": "Unanswered in the last 7 days: {0}",
    "24 ชั่วโมงที่ผ่านมา: ถาม {0} ครั้ง · เรียกโมเดล {1} ครั้ง · ตอบจาก cache {2} ครั้ง": "Last 24 hours: asked {0} times · model called {1} times · answered from cache {2} times",
    "เนื้อหาเปลี่ยนไปหลังสร้างครั้งล่าสุด ({0}) กดสร้างใหม่เพื่อให้ช่องถามตอบเห็นเนื้อหาล่าสุด": "The content changed since the last build ({0}). Rebuild so the question box sees the latest content.",
    "ลบ{0}ทั้งหมดในถังขยะถาวร ({1} รายการ)": "Delete all of {0} in the trash for good ({1} items)",
    "ลบไม่ได้ เพราะยังมีผลงาน {0} ชิ้นอยู่ในประเภทนี้ ย้ายผลงานออกก่อน หรือกด 'ซ่อน' ประเภทนี้แทน": "Cannot delete: {0} project(s) are still in this category. Move them out first, or Hide the category instead.",
    "ลบไม่ได้ เพราะยังมีรายการ {0} ชิ้นเป็นชนิดนี้ เปลี่ยนชนิดของรายการเหล่านั้นก่อน หรือกด 'ซ่อน' ชนิดนี้แทน": "Cannot delete: {0} item(s) are still of this kind. Change their kind first, or Hide the kind instead.",
    "เลือกประเภทได้ไม่เกิน {0} ประเภท": "You can choose at most {0} categories",
    "ไฟล์ใหญ่เกิน {0} MB": "The file is larger than {0} MB",
    "รหัสผ่านใหม่ต้องยาวอย่างน้อย {0} ตัวอักษร": "The new password must be at least {0} characters",
    "ใส่คำที่มีความหมายเดียวกันอย่างน้อย {0} คำ": "Enter at least {0} words that mean the same",
    "{0}: ต้องเป็นตัวเลข {1}–{2}": "{0}: must be a number from {1} to {2}",
    "(ไม่เกิน {0} พิมพ์ชื่อใหม่แล้วกดเพิ่มได้เลย)": "(at most {0}; type a new name and press Add)",
    "ครบ {0} แล้ว": "{0} reached",
    "ยังไม่ได้แปล {0} ช่อง": "{0} field(s) not translated",
    "(รหัสผ่านอย่างน้อย {0} ตัวอักษร)": "(at least {0} characters)",
    "รหัสผ่านใหม่ (อย่างน้อย {0} ตัวอักษร)": "New password (at least {0} characters)",
    "ชนิดนี้ไม่ใช้ช่อง: {0} (ข้อมูลที่เคยกรอกยังเก็บไว้ ไม่หาย)": "This kind does not use: {0} (what was typed there is kept, not lost)",
}
# Where a Thai phrase is the name of a field that appears inside the patterns above, these give the English.
# (The dashboard builds "{section} not fully translated" from these section names.)
SECTIONS = {"ผลงาน": "Projects", "ประวัติการทำงาน": "Work history", "ประวัติการศึกษา": "Education", "บทความ": "Articles", "ข้อมูลส่วนตัว": "Profile"}


def _space_flexible(escaped: str) -> str:
    """Thai text in a template can break across lines, so any run of spaces matches any whitespace."""
    return re.sub(r"(?:\\ )+", r"\\s+", escaped)


def _split_pattern(thai: str):
    return re.split(r"\{(\d+)\}", thai)  # text, index, text, index, ...


def _compile(capture: str, flexible: bool):
    rules = []
    for thai, english in PATTERNS.items():
        regex = ""
        for i, part in enumerate(_split_pattern(thai)):
            regex += capture if i % 2 else (_space_flexible(re.escape(part)) if flexible else re.escape(part))
        rules.append((len(thai), re.compile(regex, re.S), english))
    rules.sort(key=lambda rule: -rule[0])
    return rules


# In template source a placeholder is a Jinja expression such as {{ total }}; it must not run past a tag.
SOURCE_RULES = _compile(r"([^<>]+?)", flexible=True)
# On a whole Python string a placeholder is any text.
STRING_RULES = _compile(r"(.+?)", flexible=False)
_phrases = sorted(CATALOG, key=len, reverse=True)
PHRASE_RE = re.compile("|".join(_space_flexible(re.escape(p)) for p in _phrases), re.S)
_BY_FLAT = {re.sub(r"\s+", " ", p): CATALOG[p] for p in _phrases}


def _phrase(text: str) -> str:
    return PHRASE_RE.sub(lambda m: _BY_FLAT[re.sub(r"\s+", " ", m.group(0))], text)


def translate_source(source: str) -> str:
    """The English version of a template file. Sentences with {{ }} inside are matched as patterns first,
    then every remaining Thai phrase is replaced."""
    for _length, regex, english in SOURCE_RULES:
        source = regex.sub(lambda match, english=english: english.format(*match.groups()), source)
    return _phrase(source)


def tr(text, english: bool):
    """Text made by Python, in the language asked for. Thai stays Thai unless `english`. Only a string that
    is a whole entry, or a whole pattern, is translated, so the owner's own text passes through untouched."""
    if not english or not isinstance(text, str) or not THAI_LETTER.search(text):
        return text
    flat = re.sub(r"\s+", " ", text.strip())
    if flat in _BY_FLAT:
        return _BY_FLAT[flat]
    for _length, regex, translation in STRING_RULES:
        match = regex.fullmatch(flat)
        if match:
            values = [SECTIONS.get(g, _phrase(g)) for g in match.groups()]
            return translation.format(*values)
    return text


THAI_LETTER = re.compile("[\u0e00-\u0e7f]")

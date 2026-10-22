# การดูแลระบบ: เฝ้าระวัง แจ้งเตือน และ CI

## 1. รู้ได้อย่างไรว่าอะไรพัง

มี 3 ชั้น ใช้ร่วมกัน:

| ชั้น | บอกอะไร | อยู่ที่ไหน |
|---|---|---|
| **Docker healthcheck** | container ไหนไม่ตอบ (`web`, `api`, `db`) | `docker ps` ดูคอลัมน์ STATUS ต้องเป็น `healthy` |
| **หน้า "ภาพรวม" ใน admin** | ฐานข้อมูล/ที่เก็บไฟล์ล่ม, **โมเดลตอบคำถามล้มเหลว**, ข้อมูลช่องถามตอบล้าสมัย | admin → ภาพรวม ("สิ่งที่ต้องดูแล" + "สถานะระบบ") |
| **Uptime Kuma** (ไม่บังคับ) | เว็บล่มแล้ว **ส่งแจ้งเตือนให้** (Discord/Telegram/อีเมล) | `docker compose --profile monitor up -d` |

สองชั้นแรกต้องมีคนเปิดดูเอง ถ้าต้องการให้ระบบ "ส่งข้อความหาคุณ" ให้ติดตั้งชั้นที่ 3

## 2. โมเดลตอบคำถามพัง

ผู้เข้าชมไม่เห็น error เขาจะได้คำตอบแบบ "สรุปไม่ได้ ลองอ่านส่วนเหล่านี้" แทน (โหมด `fallback`)
คุณจะรู้ได้จาก:

- หน้า "ภาพรวม": ป้ายแดง **"โมเดลตอบคำถาม ล้มเหลว N ครั้ง"** และรายการ "โมเดลตอบคำถามล้มเหลว N ครั้งใน 24 ชั่วโมง" (นับเฉพาะเมื่อมี `GEMINI_API_KEY` และคำถามนั้นค้นหาเจอแต่ตอบด้วยโมเดลไม่ได้)
- log: `docker logs portfolio-api 2>&1 | grep portfolio.llm` ได้บรรทัดเช่น
  `gemini model gemini-2.5-flash-lite returned 404: This model ... is no longer available to new users`

สาเหตุที่พบบ่อย:

| log | สาเหตุ | แก้ |
|---|---|---|
| `returned 404 ... no longer available` | Google เลิกรุ่นนั้น | เปลี่ยน `GEMINI_MODEL_CHEAP` / `GEMINI_MODEL_SMART` ใน `.env` เป็นรุ่นที่ใช้ได้ แล้ว `docker compose up -d api` |
| `returned 429` | โควตาหมด | รอ/เพิ่มโควตาใน Google AI Studio |
| `returned 400/403` | คีย์ผิดหรือถูกยกเลิก | สร้างคีย์ใหม่ใส่ `GEMINI_API_KEY` |
| `returned 5xx` หรือ timeout | Google มีปัญหา | รอ ระบบยังใช้ได้ในโหมด fallback |

ดูรุ่นที่คีย์ของคุณเรียกได้ (ไม่พิมพ์คีย์):

```
docker exec portfolio-api python -c "import httpx; from app.config import get_settings as g; s=g(); r=httpx.get('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200', headers={'x-goog-api-key': s.gemini_api_key}); print([m['name'].split('/')[1] for m in r.json().get('models',[]) if 'generateContent' in m.get('supportedGenerationMethods',[]) and 'flash' in m['name']])"
```

## 3. ตั้งแจ้งเตือนเว็บล่ม (Uptime Kuma)

```
docker compose --profile monitor up -d
```

เปิด http://localhost:3001 (เปลี่ยนพอร์ตด้วย `MONITOR_PORT` ใน `.env`) สร้างบัญชีผู้ดูแลครั้งแรก แล้วเพิ่ม monitor ชนิด HTTP:

| ชื่อ | URL | ผ่านเมื่อ | บอกอะไร |
|---|---|---|---|
| เว็บ | `https://<SITE_DOMAIN>/robots.txt` | 200 | web (Next.js) ยังทำงาน |
| API | `https://<SITE_DOMAIN>/api/health/live` | 200 | API ยังทำงาน |
| ฐานข้อมูล+ไฟล์ | `https://<SITE_DOMAIN>/api/health` | 200 (ล่มจะได้ 503) | DB และ storage ตอบ |
| หลังบ้าน | `https://<ADMIN_DOMAIN>/login` | 200 | หน้า admin เปิดได้ |

(ใช้ `http://web:3000/robots.txt`, `http://api:8000/api/health` ถ้าอยากเช็กภายในเครือข่าย Docker)

เพิ่มช่องทางแจ้งเตือนที่ Settings → Notifications:
- **Discord**: สร้าง Webhook ในช่อง (ตั้งค่าช่อง → การเชื่อมต่อ → Webhooks) วาง URL
- **Telegram**: สร้างบอทกับ @BotFather ได้ token แล้วใส่ chat ID
- **อีเมล (SMTP)**: ใส่ host/user/password ของผู้ให้บริการอีเมล

แล้วกด "Default enabled" ให้ monitor ทั้งหมดใช้ช่องทางนี้ และกด Test เพื่อให้แน่ใจว่าข้อความถึง

**ข้อจำกัดที่ต้องรู้**: Uptime Kuma รันบนเครื่องเดียวกับเว็บ ถ้าทั้งเครื่องดับก็จะไม่มีใครส่งแจ้งเตือน จึงควรมี monitor ภายนอกอีกตัว (เช่น UptimeRobot หรือ Better Stack แบบฟรี) ชี้ที่ `https://<SITE_DOMAIN>/api/health`

ตอนนี้ Uptime Kuma เปิดที่ `127.0.0.1` เท่านั้น ถ้าจะเปิดผ่านโดเมนให้ใส่หลังพร็อกซีพร้อมรหัสผ่านก่อน

## 4. CI (GitHub Actions)

ไฟล์: `.github/workflows/ci.yml` รันทุกครั้งที่ push เข้า `main` และทุก pull request:

| งาน | ตรวจอะไร |
|---|---|
| **api** | `pytest` ทั้งชุด (ใช้ Postgres + pgvector ชั่วคราว), และ CSS ของ admin ที่ commit ไว้ต้องตรงกับ template |
| **web** | `api-types.ts` ตรงกับ `openapi.json`, `tsc`, `next build`, `npm audit` (ระดับ high ขึ้นไป) |
| **images** | build image ของ `api` และ `web` ได้ |

เมื่อ CI แดง:

- **"The committed admin stylesheet matches the templates"** แก้/เพิ่ม class ใน template แล้วลืม build CSS → รัน
  `api/scripts/build_css.sh` (Git Bash/Linux) หรือ `api\scripts\build_css.ps1` (PowerShell) แล้ว commit `api/app/static/admin.css`
- **"api-types.ts matches openapi.json"** API เปลี่ยน schema → รัน `python -m scripts.export_openapi` ใน `api/` แล้ว `npm run api:types` ใน `web/` และ commit ทั้งสองไฟล์
- **npm audit** มีช่องโหว่ระดับ high ในแพ็กเกจที่ใช้จริง → อัปเกรดแพ็กเกจนั้น

ตั้ง branch protection ให้ต้องผ่าน CI ก่อน merge ได้ที่ GitHub → Settings → Branches (ทำเองครั้งเดียว)

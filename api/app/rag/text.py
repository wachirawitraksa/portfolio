"""Clean up a question before searching. Pure functions, no database, no network.

normalize        tone marks, Thai digits, stretched letters ("มากกกก"), spacing, case
fix_keyboard     text typed with the wrong keyboard language ("l;ylfu" is "สวัสดี")
skeleton         a rough phonetic key, so "tam ngan arai" can find "ทำงานอะไร"
"""
import re
import unicodedata

from pythainlp.corpus import thai_words
from pythainlp.tokenize import word_tokenize
from pythainlp.transliterate import romanize
from pythainlp.util import normalize as thai_normalize
from pythainlp.util import thai_digit_to_arabic_digit

MAX_QUESTION_CHARS = 300

THAI_CHAR = re.compile("[฀-๿]")
ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")
THAI_RUN = re.compile(r"([฀-๿])\1{2,}")  # same Thai letter 3+ times: stretched
LATIN_RUN = re.compile(r"([a-z])\1{2,}")
# Keep letters and digits, plus + # . so c++, c#, node.js and .net survive. Everything else separates words.
SEPARATORS = re.compile(r"[^\w+#.฀-๿]+", re.UNICODE)
SPACES = re.compile(r"\s+")

STOPWORDS = frozenset(
    "ผม คุณ เขา ครับ ค่ะ คะ นะ จ้ะ ไหม มั้ย หรือ หรอ คือ ที่ ของ และ กับ ใน เป็น มี ได้ ไป มา บ้าง บ้างไหม "
    "อะไร อย่างไร ยังไง ทำไม เมื่อไหร่ เมื่อไร ที่ไหน ใคร กี่ เท่าไหร่ เท่าไร หน่อย ช่วย บอก เล่า "
    "a an the is are was were be do does did of to in on for with and or about me you your i my he she it "
    "this that what which who how tell show explain describe have has had any some many there they we our get got also".split()
)

# English words people type in a question that are not part of any project text.
COMMON_ENGLISH = frozenset(
    "hello hi hey thanks thank please what who how why when where which can could does do did is are was "
    "tell show me about your you work works worked working project projects experience skill skills tool tools "
    "article articles write written contact email cv resume certificate award course job role company team "
    "language languages built build make made use used using stack tech technology years year".split()
)


def has_thai(text: str) -> bool:
    return bool(THAI_CHAR.search(text))


def normalize(text: str, limit: int | None = MAX_QUESTION_CHARS) -> str:
    """Clean text for searching. A question is capped at `limit` letters; pass None for site content."""
    text = unicodedata.normalize("NFKC", text)
    if limit:
        text = text[: limit * 2]
    text = ZERO_WIDTH.sub("", text)
    text = thai_digit_to_arabic_digit(text)
    text = thai_normalize(text)  # repeated tone marks / vowels, wrong mark order
    text = text.lower()
    text = THAI_RUN.sub(r"\1", text)  # มากกกก -> มาก
    text = LATIN_RUN.sub(r"\1\1", text)  # coooool -> cool
    words = []
    for word in SEPARATORS.sub(" ", text).split():
        word = word.rstrip(".")  # a full stop ends a sentence, but c++ and c# keep their symbols
        if word.strip(".+#"):
            words.append(word)
    result = " ".join(words)
    return result[:limit] if limit else result


def tokenize(text: str) -> list[str]:
    """Words of an already normalized text. Thai is cut with the newmm dictionary tokenizer."""
    tokens: list[str] = []
    for chunk in text.split():
        if has_thai(chunk):
            tokens.extend(t for t in word_tokenize(chunk, engine="newmm", keep_whitespace=False) if t.strip())
        else:
            tokens.append(chunk)
    return tokens


def content_tokens(tokens: list[str]) -> list[str]:
    """Tokens worth searching for: no stop words, no single stray letters."""
    return [t for t in tokens if t not in STOPWORDS and (len(t) > 1 or t.isdigit())]


# --- wrong keyboard language ------------------------------------------------------------------

# Thai Kedmanee layout, by the QWERTY key that produces each character.
_UNSHIFTED = dict(zip(
    "`1234567890-=qwertyuiop[]\\asdfghjkl;'zxcvbnm,./",
    "_ๅ/-ภถุึคตจขชๆไำพะัีรนยบลฃฟหกดเ้่าสวงผปแอิืทมใฝ",
))
_SHIFTED = dict(zip(
    '~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:"ZXCVBNM<>?',
    '%+๑๒๓๔ู฿๕๖๗๘๙๐"ฎฑธํ๊ณฯญฐ,ฅฤฆฏโฌ็๋ษศซ.()ฉฮฺ์?ฒฬฦ',
))
LATIN_TO_THAI = {**_UNSHIFTED, **_SHIFTED}
THAI_TO_LATIN: dict[str, str] = {}
for _latin, _thai in {**_SHIFTED, **_UNSHIFTED}.items():  # unshifted wins when a character is on both
    THAI_TO_LATIN[_thai] = _latin

_THAI_DICTIONARY = thai_words()


def thai_word_ratio(text: str) -> float:
    """Share of the text's letters that sit inside real Thai dictionary words (0 for no Thai at all).
    Counted by letters, not words: a gibberish string can still contain one short real word."""
    tokens = [t for t in word_tokenize(text, engine="newmm", keep_whitespace=False) if t.strip()]
    total = sum(len(t) for t in tokens)
    if not total:
        return 0.0
    return sum(len(t) for t in tokens if t in _THAI_DICTIONARY and len(t) >= 2) / total


def known_ratio(text: str, vocabulary: set[str]) -> float:
    """Share of the English words in `text` that the site (or everyday English) uses."""
    words = [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 2]
    if not words:
        return 0.0
    return sum(1 for w in words if w in vocabulary or w in COMMON_ENGLISH) / len(words)


def fix_keyboard(text: str, vocabulary: set[str] | None = None) -> tuple[str, bool]:
    """Swap Thai/English keyboard mistakes. `vocabulary` is the lower-cased words of the site's own text.

    Give it the raw text: on a Thai keyboard some letters sit on the punctuation keys (; ' [ ] , .), and the
    upper and lower case of a key are different Thai letters, so normalize() must run afterwards.

    English letters that read as Thai words are converted ("l;ylfu" -> "สวัสดี"). Thai letters that read
    as known English words are converted back. When neither is convincing the text is returned untouched."""
    vocabulary = vocabulary or set()
    if not text.strip():
        return text, False
    if not has_thai(text):
        if known_ratio(text, vocabulary) >= 0.5:
            return text, False  # already readable English
        converted = "".join(LATIN_TO_THAI.get(c, c) for c in text)
        if has_thai(converted) and thai_word_ratio(converted) >= 0.8:
            return normalize(converted), True
        return text, False
    if thai_word_ratio(text) >= 0.7:
        return text, False  # already readable Thai
    converted = "".join(THAI_TO_LATIN.get(c, c) for c in text).lower()
    if not has_thai(converted) and known_ratio(converted, vocabulary) >= 0.8:
        return normalize(converted), True
    return text, False


# --- thai typed in latin letters ("karaoke") --------------------------------------------------

def skeleton(word: str) -> str:
    """A rough sound key for a Latin word. Thai romanization and what people type differ in small ways
    (tham / tam, phrom / prom), so drop h, fold similar letters and collapse repeats."""
    word = re.sub(r"[^a-z]", "", word.lower())
    word = word.replace("ph", "p").replace("th", "t").replace("kh", "k")
    word = word.replace("h", "").replace("w", "u").replace("y", "i").replace("j", "c").replace("v", "u")
    return re.sub(r"(.)\1+", r"\1", word)


def sound_key(tokens: list[str]) -> str:
    """Space separated skeletons of the tokens. Thai tokens are romanized first (royin system)."""
    keys = []
    for token in tokens:
        latin = romanize(token) if has_thai(token) else token
        key = skeleton(latin)
        if len(key) >= 2:
            keys.append(key)
    return " ".join(keys)


def language_of(text: str) -> str:
    """"th", "en" or "mixed", by the letters used."""
    thai = len(THAI_CHAR.findall(text))
    latin = len(re.findall(r"[a-z]", text))
    if thai and latin:
        return "mixed"
    return "th" if thai else "en"

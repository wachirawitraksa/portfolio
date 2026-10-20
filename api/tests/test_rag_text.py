from app.rag.text import (
    content_tokens,
    fix_keyboard,
    language_of,
    normalize,
    skeleton,
    sound_key,
    tokenize,
)

VOCAB = {"portfolio", "postgresql", "docker", "stock", "inventory", "typescript"}


def test_normalize_stretched_letters_digits_case_and_spacing():
    assert normalize("มากกกกก") == "มาก"
    assert normalize("Coooool   PROJECT!!!") == "cool project"
    assert normalize("ปี ๒๕๖๗  ๑๒๓") == "ปี 2567 123"
    assert normalize("  hello​   world \n") == "hello world"


def test_normalize_keeps_what_technology_names_need():
    assert normalize("C++ and C# with Node.js, .NET?") == "c++ and c# with node.js .net"
    assert normalize("a/b (c)") == "a b c"


def test_normalize_fixes_doubled_tone_marks_and_caps_length():
    assert "่่" not in normalize("ก่่อน")
    assert len(normalize("ก" * 1000 + " x" * 1000)) <= 300


def test_tokenize_cuts_thai_and_keeps_latin_words():
    tokens = tokenize(normalize("คุณทำงานอะไรมาบ้าง with docker"))
    assert "ทำงาน" in tokens and "docker" in tokens
    assert "คุณ" not in content_tokens(tokens) and "docker" in content_tokens(tokens)


def test_thai_typed_on_the_english_keyboard_is_converted():
    assert fix_keyboard("l;ylfu", VOCAB) == ("สวัสดี", True)
    fixed, changed = fix_keyboard("l;ylfu", set())  # works without the site's own vocabulary
    assert changed and fixed == "สวัสดี"


def test_english_typed_on_the_thai_keyboard_is_converted_back():
    assert fix_keyboard("หะนแา", VOCAB) == ("stock", True)
    assert fix_keyboard("กนแาำพ", VOCAB) == ("docker", True)


def test_readable_text_is_left_alone():
    assert fix_keyboard("what projects do you have", VOCAB) == ("what projects do you have", False)
    assert fix_keyboard("docker", VOCAB) == ("docker", False)
    assert fix_keyboard("คุณทำงานอะไร", VOCAB) == ("คุณทำงานอะไร", False)
    assert fix_keyboard("", VOCAB) == ("", False)


def test_unknown_latin_words_are_not_forced_into_thai():
    assert fix_keyboard("zzqx kkvv", VOCAB)[1] is False


def test_skeleton_folds_spelling_differences():
    assert skeleton("tham") == skeleton("tam") == "tam"
    assert skeleton("Phrom") == skeleton("prom")
    assert skeleton("noo") == "no"


def test_karaoke_question_matches_the_romanized_thai_text():
    typed = sound_key(tokenize(normalize("tam ngan arai")))
    thai = sound_key(tokenize(normalize("ทำงานอะไร")))
    assert typed and thai
    # every typed word's sound key appears in the Thai text's key
    joined = thai.replace(" ", "")
    assert all(word in joined for word in typed.split())


def test_language_of():
    assert language_of("สวัสดี") == "th" and language_of("hello") == "en" and language_of("ใช้ docker") == "mixed"

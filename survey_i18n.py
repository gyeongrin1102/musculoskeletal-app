"""증상조사 화면 번역.

번역문은 translations/survey_translations.csv 에 있습니다.
- 첫 줄(머리글): 구분, ko, vi, zh, ru, km, id, fil  (언어를 늘리려면 열을 추가: 예) th, en ...)
- ko 열: 화면에 쓰는 한국어 원문 (이 값으로 번역을 찾으므로 고치지 마세요)
- 번역 칸이 비어 있으면 한국어 원문이 그대로 보입니다.

응답 값은 언어와 관계없이 한국어 보기(원문)로 저장되므로 판정·집계·출력은 같게 처리됩니다.
"""

import csv
import os

VERSION = 3  # 이 파일을 고치면 숫자를 올려 주세요 (실행 중인 앱이 새 코드로 다시 읽음)

CSV_PATH = os.path.join(os.path.dirname(__file__), "translations", "survey_translations.csv")

# 언어 코드 → (화면 표시 이름, 저장용 한국어 이름)
LANGUAGES = {
    "ko": ("한국어", "한국어"),
    "vi": ("Tiếng Việt", "베트남어"),
    "zh": ("中文", "중국어"),
    "en": ("English", "영어"),
    "th": ("ภาษาไทย", "태국어"),
    "uz": ("Oʻzbekcha", "우즈베크어"),
    "km": ("ភាសាខ្មែរ", "캄보디아어"),
    "ne": ("नेपाली", "네팔어"),
    "id": ("Bahasa Indonesia", "인도네시아어"),
    "fil": ("Filipino", "필리핀어"),
    "mn": ("Монгол", "몽골어"),
    "ru": ("Русский", "러시아어"),
}

_cache = {"mtime": None, "table": {}, "langs": ["ko"]}


def _load():
    try:
        mtime = os.path.getmtime(CSV_PATH)
    except OSError:
        return _cache
    if _cache["mtime"] == mtime:
        return _cache
    table, langs = {}, ["ko"]
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = [c.strip() for c in (reader.fieldnames or [])]
        langs += [c for c in cols if c and c not in ("ko", "구분")]
        for row in reader:
            row = {(k or "").strip(): (v or "") for k, v in row.items()}
            key = row.get("ko", "")
            if not key.strip():
                continue
            table[key] = {c: row.get(c, "").strip() for c in langs if c != "ko"}
    _cache.update(mtime=mtime, table=table, langs=langs)
    return _cache


def available_languages():
    """번역 열이 있는 언어 코드 목록 (ko 포함)."""
    return list(_load()["langs"])


def display_name(code):
    return LANGUAGES.get(code, (code, code))[0]


def stored_name(code):
    return LANGUAGES.get(code, (code, code))[1]


def translate(text, lang):
    if lang == "ko" or text is None:
        return text
    entry = _load()["table"].get(text)
    if entry and entry.get(lang):
        return entry[lang]
    return text


def missing_keys(keys, lang):
    table = _load()["table"]
    return [k for k in keys if not (table.get(k) or {}).get(lang)]

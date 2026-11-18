"""근골격계질환 증상조사표 공통 모듈.

- 서식 문항·보기: 근골격계부담작업 유해요인조사 고시 별지 제2호서식 /
  KOSHA GUIDE E-G-1-2025 별지 제2호서식의 문항과 보기를 그대로 사용합니다.
  (보기를 바꾸면 판정 기준과 지난 조사 결과 비교가 어려워지므로 수정하지 마세요.)
- 판정: KOSHA GUIDE E-G-1-2025 8.1 표 2 (NIOSH 증상 기준)
- 출력: Word(.docx) / PDF / 엑셀 집계표

Streamlit 에 의존하지 않으므로 단독으로 테스트할 수 있습니다.
"""

from __future__ import annotations

import io
import os
from datetime import datetime

# =========================================================
# 서식 문항·보기 (별지 제2호서식)
# =========================================================

FORM_TITLE = "근골격계질환 증상조사표"

BODY_PARTS = ["목", "어깨", "팔/팔꿈치", "손/손목/손가락", "허리", "다리/발"]

# 좌우 구분 문항이 있는 부위 (서식 Ⅱ-1)
SIDE_PARTS = ["어깨", "팔/팔꿈치", "손/손목/손가락", "다리/발"]
SIDE_OPTIONS = ["오른쪽", "왼쪽", "양쪽 모두"]

GENDER_OPTIONS = ["남", "여"]
MARRIAGE_OPTIONS = ["기혼", "미혼"]

HOBBY_OPTIONS = [
    "컴퓨터 관련 활동",
    "악기연주(피아노, 바이올린 등)",
    "뜨개질 붓글씨",
    "테니스/배드민턴/스쿼시",
    "축구/족구/농구/스키",
    "해당사항 없음",
]

HOUSEWORK_OPTIONS = [
    "거의 하지 않는다",
    "1시간 미만",
    "1-2시간 미만",
    "2-3시간 미만",
    "3시간 이상",
]

DISEASE_OPTIONS = ["류머티스 관절염", "당뇨병", "루프스병", "통풍", "알코올중독"]
DISEASE_STATUS_OPTIONS = ["완치", "치료나 관찰 중"]

INJURY_PARTS = ["손/손가락/손목", "팔/팔꿈치", "어깨", "목", "허리", "다리/발"]

LOAD_OPTIONS = ["전혀 힘들지 않음", "견딜만 함", "약간 힘듦", "매우 힘듦"]

YES_NO = ["아니오", "예"]

DURATION_OPTIONS = [
    "1일 미만",
    "1일-1주일 미만",
    "1주일-1달 미만",
    "1달-6개월 미만",
    "6개월 이상",
]

SEVERITY_OPTIONS = ["약한 통증", "중간 통증", "심한 통증", "매우 심한 통증"]

SEVERITY_GUIDE = {
    "약한 통증": "약간 불편한 정도이나 작업에 열중할 때는 못 느낀다",
    "중간 통증": "작업 중 통증이 있으나 귀가 후 휴식을 취하면 괜찮다",
    "심한 통증": "작업 중 통증이 비교적 심하고 귀가 후에도 통증이 계속된다",
    "매우 심한 통증": "통증 때문에 작업은 물론 일상생활을 하기가 어렵다",
}

FREQUENCY_OPTIONS = [
    "6개월에 1번",
    "2-3달에 1번",
    "1달에 1번",
    "1주일에 1번",
    "매일",
]

CONSEQUENCE_OPTIONS = [
    "병원·한의원 치료",
    "약국치료",
    "병가, 산재",
    "작업 전환",
    "해당사항 없음",
    "기타",
]

Q_HOBBY = (
    "1. 규칙적인(한번에 30분 이상, 1주일에 적어도 2-3회 이상) 여가 및 "
    "취미활동을 하고 계시는 곳에 표시하여 주십시오."
)
Q_HOUSEWORK = (
    "2. 귀하의 하루 평균 가사노동시간(밥하기, 빨래하기, 청소하기, "
    "2살 미만의 아이 돌보기 등)은 얼마나 됩니까?"
)
Q_DISEASE = (
    "3. 귀하는 의사로부터 다음과 같은 질병에 대해 진단을 받은 적이 있습니까?"
)
Q_INJURY = (
    "4. 과거에 운동 중 혹은 사고로(교통사고, 넘어짐, 추락 등) 인해 "
    "손/손가락/손목, 팔/팔꿈치, 어깨, 목, 허리, 다리/발 부위를 다친 적이 있습니까?"
)
Q_LOAD = "5. 현재 하고 계시는 일의 육체적 부담 정도는 어느 정도라고 생각합니까?"

Q_SYMPTOM = (
    "지난 1년 동안 손/손가락/손목, 팔/팔꿈치, 어깨, 목, 허리, 다리/발 중 "
    "어느 한 부위에서라도 귀하의 작업과 관련하여 통증이나, 쑤시는 느낌, "
    "뻣뻣함, 화끈거리는 느낌, 무감각 혹은 찌릿찌릿함 등의 증상을 "
    "느끼신 적이 있습니까?"
)

PART_QUESTIONS = [
    ("통증부위", "1. 통증의 구체적 부위는?"),
    ("지속기간", "2. 한번 아프기 시작하면 통증 기간은 얼마 동안 지속됩니까?"),
    ("증상정도", "3. 그때의 아픈 정도는 어느 정도입니까? (보기 참조)"),
    ("빈도", "4. 지난 1년 동안 이러한 증상을 얼마나 자주 경험하셨습니까?"),
    ("최근1주증상", "5. 지난 1주일 동안에도 이러한 증상이 있었습니까?"),
    ("통증으로인한일", "6. 지난 1년 동안 이러한 통증으로 인해 어떤 일이 있었습니까?"),
]

PART_OPTIONS = {
    "지속기간": DURATION_OPTIONS,
    "증상정도": SEVERITY_OPTIONS,
    "빈도": FREQUENCY_OPTIONS,
    "최근1주증상": YES_NO,
    "통증으로인한일": CONSEQUENCE_OPTIONS,
}

NOTICE_USE = (
    "이 조사는 근골격계부담작업 유해요인조사의 일부로, 작업환경 개선을 위한 "
    "기초자료로만 사용합니다. 증상조사 결과는 근골격계질환의 이환을 "
    "부정하거나 입증하는 근거 또는 반증자료로 활용할 수 없습니다."
)

JUDGMENTS = ["통증호소자", "관리대상자", "정상"]

# =========================================================
# 예전 버전 응답(보기 문구가 달랐던 기록) 호환
# =========================================================

LEGACY_MAP = {
    # 지속기간
    "1일 이상 ~ 1주일 미만": "1일-1주일 미만",
    "1주일 이상 ~ 1개월 미만": "1주일-1달 미만",
    "1개월 이상 ~ 6개월 미만": "1달-6개월 미만",
    # 빈도
    "6개월에 1번 정도": "6개월에 1번",
    "2~3개월에 1번 정도": "2-3달에 1번",
    "1개월에 1번 정도": "1달에 1번",
    "1주일에 1번 정도": "1주일에 1번",
    # 가사노동
    "1~2시간": "1-2시간 미만",
    "2~3시간": "2-3시간 미만",
    # 취미
    "악기 연주": "악기연주(피아노, 바이올린 등)",
    "뜨개질/자수/붓글씨": "뜨개질 붓글씨",
    "축구/족구/농구/스키 등": "축구/족구/농구/스키",
    # 질병
    "류마티스 관절염": "류머티스 관절염",
}


def norm(value):
    """보기 문구를 현행 서식 문구로 맞춥니다."""
    if value is None:
        return None
    text = str(value).strip()
    if text in ("", "None", "nan"):
        return None
    return LEGACY_MAP.get(text, text)


def split_multi(value):
    """'a, b' 형식 문자열 또는 리스트를 리스트로."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = value
    else:
        text = str(value)
        if text in ("", "None", "nan"):
            return []
        # 보기 안에 쉼표가 있는 항목(예: '병가, 산재')을 보호
        protected = text
        for opt in CONSEQUENCE_OPTIONS + HOBBY_OPTIONS:
            if "," in opt:
                protected = protected.replace(opt, opt.replace(",", "§"))
        items = [x.replace("§", ",") for x in protected.split(",")]
    return [norm(x) for x in items if norm(x)]


def join_multi(items):
    return ", ".join(i for i in items if i)


# =========================================================
# 판정 (KOSHA GUIDE E-G-1-2025 8.1 표 2)
# =========================================================

def _index(value, options):
    value = norm(value)
    return options.index(value) if value in options else -1


def classify_body_part(duration, severity, frequency, symptom="예"):
    """부위별 판정.

    관리대상자: 1주일 이상 지속되거나(OR) 1달에 1번 이상 발생 + 중간 정도 이상
    통증호소자: 1주일 이상 지속되고(AND) 1달에 1번 이상 발생 + 심한/매우 심한
    정상: 위 두 가지에 해당하지 않는 경우

    '심한 통증' 이상이지만 기간·빈도 중 하나만 해당하면, 통증호소자 조건
    (둘 다)에는 못 미치므로 관리대상자로 분류합니다.
    """
    if symptom != "예":
        return "정상"

    long_duration = _index(duration, DURATION_OPTIONS) >= 2      # 1주일-1달 미만 이상
    frequent = _index(frequency, FREQUENCY_OPTIONS) >= 2         # 1달에 1번 이상
    sev = _index(severity, SEVERITY_OPTIONS)                     # 1=중간, 2=심한, 3=매우 심한

    if long_duration and frequent and sev >= 2:
        return "통증호소자"
    if (long_duration or frequent) and sev >= 1:
        return "관리대상자"
    return "정상"


def final_judgment(part_judgments):
    for level in JUDGMENTS:
        if level in part_judgments:
            return level
    return "정상"


def judge_record(record):
    """기록(dict)의 부위별·최종 판정을 다시 계산해 dict 로 돌려줍니다."""
    result = {}
    has = record.get("근골격계증상여부") == "예"
    for part in BODY_PARTS:
        symptom = record.get(f"{part}_증상여부") if has else "아니오"
        result[f"{part}_판정"] = classify_body_part(
            record.get(f"{part}_지속기간"),
            record.get(f"{part}_증상정도"),
            record.get(f"{part}_빈도"),
            symptom,
        )
    result["최종판정"] = final_judgment(result.values())
    return result


def survey_year(record):
    for key in ("조사연도",):
        if record.get(key):
            try:
                return int(record[key])
            except (TypeError, ValueError):
                pass
    for key in ("제출일시", "created_at"):
        text = str(record.get(key) or "")
        if len(text) >= 4 and text[:4].isdigit():
            return int(text[:4])
    return None


# =========================================================
# 출력 공통
# =========================================================

ON, OFF = "■", "□"   # 나눔고딕·맑은 고딕 모두에 있는 기호


def _clean(value):
    if value is None:
        return ""
    text = str(value)
    if text in ("None", "nan"):
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def opts_line(options, selected, sep="  "):
    sel = set(selected if isinstance(selected, (list, set, tuple)) else [selected])
    sel = {norm(s) for s in sel}
    return sep.join(f"{ON if o in sel else OFF} {o}" for o in options)


def _blank_line(value, width=6):
    text = _clean(value)
    return text if text else "\u3000" * width


def general_rows(r):
    """Ⅰ부 기본사항을 (항목, 내용) 행으로."""
    b = _blank_line
    return [
        ("성명", b(r.get("성명"), 8)),
        ("연령", f"만 {b(r.get('연령'), 2)} 세"),
        ("성별", opts_line(GENDER_OPTIONS, r.get("성별"))),
        ("현 직장경력",
         f"{b(r.get('현직장_근무년'), 2)} 년 {b(r.get('현직장_근무개월'), 2)} 개월째 근무 중"),
        ("작업부서",
         f"{b(r.get('작업부서'), 4)} 부  {b(r.get('라인/세부부서'), 4)} 라인  "
         f"{b(r.get('수행작업'), 4)} 작업"),
        ("결혼여부", opts_line(MARRIAGE_OPTIONS, r.get("결혼여부"))),
        ("현재 하고 있는 작업\n(구체적으로)",
         f"작업내용: {b(r.get('현재작업'), 10)}\n"
         f"작업기간: {b(r.get('현재작업_수행년'), 2)} 년 "
         f"{b(r.get('현재작업_수행개월'), 2)} 개월째 하고 있음"),
        ("1일 근무시간",
         f"{b(r.get('1일근무시간'), 2)} 시간\n"
         f"근무 중 휴식시간(식사시간 제외) {b(r.get('휴식시간_분'), 2)} 분씩 "
         f"{b(r.get('휴식횟수'), 2)} 회 휴식"),
        ("현 작업을 하기 전에\n했던 작업",
         f"작업내용: {b(r.get('이전작업'), 10)}\n"
         f"작업기간: {b(r.get('이전작업_수행년'), 2)} 년 "
         f"{b(r.get('이전작업_수행개월'), 2)} 개월 동안 했음"),
    ]


def history_items(r):
    """Ⅰ부 1~5번 문항을 (질문, 응답줄 리스트) 로."""
    disease = norm(r.get("질병진단여부"))
    injury = norm(r.get("과거손상여부"))
    return [
        (Q_HOBBY, [opts_line(HOBBY_OPTIONS, split_multi(r.get("취미활동")))]),
        (Q_HOUSEWORK, [opts_line(HOUSEWORK_OPTIONS, norm(r.get("가사노동")))]),
        (Q_DISEASE, [
            "(보기: " + opts_line(DISEASE_OPTIONS, split_multi(r.get("진단질병"))) + ")",
            f"{ON if disease == '아니오' else OFF} 아니오   "
            f"{ON if disease == '예' else OFF} 예 ('예'인 경우 현재상태는? "
            + opts_line(DISEASE_STATUS_OPTIONS, norm(r.get("질병현재상태"))) + ")",
        ]),
        (Q_INJURY, [
            f"{ON if injury == '아니오' else OFF} 아니오   "
            f"{ON if injury == '예' else OFF} 예 ('예'인 경우 상해 부위는? "
            + opts_line(INJURY_PARTS, split_multi(r.get("과거손상부위"))) + ")",
        ]),
        (Q_LOAD, [opts_line(LOAD_OPTIONS, norm(r.get("육체적부담")))]),
    ]


def symptom_header_line(r):
    s = norm(r.get("근골격계증상여부"))
    return [
        f"{ON if s == '아니오' else OFF} 아니오 (수고하셨습니다. 설문을 다 마치셨습니다.)",
        f"{ON if s == '예' else OFF} 예 (\"예\"라고 답하신 분은 아래 표의 통증부위에 "
        "체크하고, 해당 통증부위의 세로줄로 내려가며 해당사항에 체크해 주십시오)",
    ]


def part_cell(r, part, field):
    """Ⅱ부 표의 한 칸: 보기 리스트(각 줄)."""
    active = norm(r.get("근골격계증상여부")) == "예" and r.get(f"{part}_증상여부") == "예"
    value = r.get(f"{part}_{field}") if active else None
    if field == "통증부위":
        if part not in SIDE_PARTS:
            return []
        return [f"{ON if norm(value) == o else OFF} {o}" for o in SIDE_OPTIONS]
    options = PART_OPTIONS[field]
    if field == "통증으로인한일":
        chosen = split_multi(value) if active else []
        if active and not chosen and r.get(f"{part}_치료경험") == "예":
            chosen = ["병원·한의원 치료"]   # 예전 버전 기록
        lines = []
        for o in options:
            if o == "기타":
                etc = _clean(r.get(f"{part}_통증으로인한일_기타")) if active else ""
                lines.append(f"{ON if o in chosen else OFF} 기타({etc or chr(0x3000) * 3})")
            else:
                lines.append(f"{ON if o in chosen else OFF} {o}")
        return lines
    return [f"{ON if norm(value) == o else OFF} {o}" for o in options]


def part_header(r, part):
    active = norm(r.get("근골격계증상여부")) == "예" and r.get(f"{part}_증상여부") == "예"
    return f"{ON if active else OFF} {part}"


def judgment_rows(r):
    j = judge_record(r)
    return [(p, j[f"{p}_판정"]) for p in BODY_PARTS], j["최종판정"]


def file_stem(r):
    name = _clean(r.get("성명")) or "무기명"
    dept = _clean(r.get("작업부서"))
    date = _clean(r.get("제출일시"))[:10].replace("-", "")
    parts = [p for p in (date, dept, name) if p]
    stem = "_".join(parts) or "증상조사표"
    return "".join(c for c in stem if c not in '\\/:*?"<>|')


# =========================================================
# Word (.docx)
# =========================================================

def _docx_font(run, size=None, bold=False):
    from docx.oxml.ns import qn
    from docx.shared import Pt

    run.font.name = "맑은 고딕"
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(fonts)
    fonts.set(qn("w:eastAsia"), "맑은 고딕")
    if size:
        run.font.size = Pt(size)
    run.bold = bold


def _cell_text(cell, lines, size=8.5, bold=False, align=None, shade=None):
    from docx.oxml.ns import qn
    from docx.shared import Pt

    if isinstance(lines, str):
        lines = lines.split("\n")
    cell.text = ""
    for i, line in enumerate(lines or [""]):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.1
        if align is not None:
            p.alignment = align
        _docx_font(p.add_run(line), size, bold)
    if shade:
        tcpr = cell._element.get_or_add_tcPr()
        shd = tcpr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:fill"): shade})
        tcpr.append(shd)


def _para(doc, text, size=9.5, bold=False, align=None, before=4, after=2):
    from docx.shared import Pt

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    if align is not None:
        p.alignment = align
    _docx_font(p.add_run(text), size, bold)
    return p


def _set_col_widths(table, widths_cm):
    from docx.shared import Cm

    for row in table.rows:
        for idx, w in enumerate(widths_cm):
            row.cells[idx].width = Cm(w)


def _write_form(doc, r, org="", include_judgment=False):
    from docx.enum.text import WD_ALIGN_PARAGRAPH as AL

    _para(doc, FORM_TITLE, 16, True, AL.CENTER, 0, 2)
    if org:
        _para(doc, org, 9, False, AL.CENTER, 0, 4)
    meta = []
    if _clean(r.get("제출일시")):
        meta.append(f"작성일시: {_clean(r.get('제출일시'))}")
    if meta:
        _para(doc, "  ".join(meta), 8, False, AL.RIGHT, 0, 2)

    _para(doc, "Ⅰ. 아래 사항을 직접 기입해 주시기 바랍니다.", 10, True)
    rows = general_rows(r)
    t = doc.add_table(rows=len(rows), cols=2)
    t.style = "Table Grid"
    for i, (k, v) in enumerate(rows):
        _cell_text(t.rows[i].cells[0], k, 8.5, True, AL.CENTER, "EEF2F7")
        _cell_text(t.rows[i].cells[1], v, 9)
    _set_col_widths(t, [3.6, 14.4])

    for q, lines in history_items(r):
        _para(doc, q, 9, True, before=5, after=1)
        for line in lines:
            _para(doc, "   " + line, 8.5, before=0, after=0)

    # ---------------- Ⅱ 부
    doc.add_page_break()
    _para(doc, "Ⅱ. " + Q_SYMPTOM, 9.5, True, before=0)
    for line in symptom_header_line(r):
        _para(doc, "   " + line, 8.5, before=0, after=0)

    t = doc.add_table(rows=1 + len(PART_QUESTIONS), cols=1 + len(BODY_PARTS))
    t.style = "Table Grid"
    _cell_text(t.rows[0].cells[0], "통증 부위", 8.5, True, AL.CENTER, "EEF2F7")
    for j, part in enumerate(BODY_PARTS, start=1):
        _cell_text(t.rows[0].cells[j], part_header(r, part), 8.5, True, AL.CENTER, "EEF2F7")
    for i, (field, label) in enumerate(PART_QUESTIONS, start=1):
        _cell_text(t.rows[i].cells[0], label, 7.5, True, shade="F7F9FC")
        for j, part in enumerate(BODY_PARTS, start=1):
            _cell_text(t.rows[i].cells[j], part_cell(r, part, field), 7.2)
    _set_col_widths(t, [3.0] + [2.5] * len(BODY_PARTS))

    _para(doc, "<보기> 아픈 정도", 8.5, True, before=6, after=1)
    for k, v in SEVERITY_GUIDE.items():
        _para(doc, f"   · {k}: {v}", 8, before=0, after=0)

    _para(doc, "※ " + NOTICE_USE, 7.5, before=6)

    if include_judgment:
        rows, final = judgment_rows(r)
        _para(doc, "【관리자용】 판정 결과 (KOSHA GUIDE E-G-1-2025 8.1 표 2)", 9, True, before=8)
        t = doc.add_table(rows=2, cols=len(BODY_PARTS) + 1)
        t.style = "Table Grid"
        for j, (part, judg) in enumerate(rows):
            _cell_text(t.rows[0].cells[j], part, 8, True, AL.CENTER, "EEF2F7")
            _cell_text(t.rows[1].cells[j], judg, 8.5, judg != "정상", AL.CENTER)
        _cell_text(t.rows[0].cells[-1], "최종판정", 8, True, AL.CENTER, "EEF2F7")
        _cell_text(t.rows[1].cells[-1], final, 9, True, AL.CENTER,
                   {"통증호소자": "F8D7DA", "관리대상자": "FFF3CD"}.get(final))


def _new_doc():
    from docx import Document
    from docx.shared import Cm

    doc = Document()
    for s in doc.sections:
        s.page_height, s.page_width = Cm(29.7), Cm(21.0)
        s.top_margin = s.bottom_margin = Cm(1.5)
        s.left_margin = s.right_margin = Cm(1.5)
    return doc


def build_docx(records, org="", include_judgment=False):
    """한 명 이상의 응답을 공식 서식 형태의 Word 파일 하나로 만듭니다.
    빈 양식이 필요하면 records=[{}] 를 넘깁니다."""
    if isinstance(records, dict):
        records = [records]
    doc = _new_doc()
    for i, r in enumerate(records):
        if i:
            doc.add_page_break()
        _write_form(doc, r or {}, org, include_judgment)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# =========================================================
# PDF (reportlab)
# =========================================================

FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
     "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", None),
    (os.path.join(os.path.dirname(__file__), "fonts", "NanumGothic.ttf"),
     os.path.join(os.path.dirname(__file__), "fonts", "NanumGothicBold.ttf"), None),
    ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf", None),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", None, 0),
]

_PDF_FONT = None


def _pdf_font():
    """(일반, 굵게) 폰트 이름. 한글 폰트가 없으면 None."""
    global _PDF_FONT
    if _PDF_FONT is not None:
        return _PDF_FONT or None
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for regular, bold, index in FONT_CANDIDATES:
        if not os.path.exists(regular):
            continue
        try:
            kw = {"subfontIndex": index} if index is not None else {}
            pdfmetrics.registerFont(TTFont("KR", regular, **kw))
            if bold and os.path.exists(bold):
                pdfmetrics.registerFont(TTFont("KR-B", bold))
                _PDF_FONT = ("KR", "KR-B")
            else:
                _PDF_FONT = ("KR", "KR")
            return _PDF_FONT
        except Exception:
            continue
    _PDF_FONT = False
    return None


def pdf_available():
    try:
        return _pdf_font() is not None
    except Exception:
        return False


def build_pdf(records, org="", include_judgment=False):
    if isinstance(records, dict):
        records = [records]
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)

    fonts = _pdf_font()
    if not fonts:
        raise RuntimeError("PDF용 한글 폰트를 찾지 못했습니다. (packages.txt 의 fonts-nanum 확인)")
    reg, bold = fonts

    def st(size, b=False, align=0, lead=1.3):
        return ParagraphStyle("s", fontName=bold if b else reg, fontSize=size,
                              leading=size * lead, alignment=align, wordWrap="CJK")

    def P(text, size=9, b=False, align=0):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), st(size, b, align))

    grid = [("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#555555")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    head_bg = colors.HexColor("#EEF2F7")

    story = []
    width = A4[0] - 30 * mm
    for n, r in enumerate(records):
        r = r or {}
        if n:
            story.append(PageBreak())
        story.append(P(FORM_TITLE, 16, True, 1))
        if org:
            story.append(P(org, 9, False, 1))
        if _clean(r.get("제출일시")):
            story.append(P(f"작성일시: {_clean(r.get('제출일시'))}", 8, False, 2))
        story.append(Spacer(1, 4))
        story.append(P("Ⅰ. 아래 사항을 직접 기입해 주시기 바랍니다.", 10, True))
        story.append(Spacer(1, 3))
        data = [[P(k, 8.5, True, 1), P(v, 9)] for k, v in general_rows(r)]
        t = Table(data, colWidths=[36 * mm, width - 36 * mm])
        t.setStyle(TableStyle(grid + [("BACKGROUND", (0, 0), (0, -1), head_bg)]))
        story.append(t)
        for q, lines in history_items(r):
            story.append(Spacer(1, 5))
            story.append(P(q, 9, True))
            for line in lines:
                story.append(P("   " + line, 8.5))

        story.append(PageBreak())
        story.append(P("Ⅱ. " + Q_SYMPTOM, 9.5, True))
        for line in symptom_header_line(r):
            story.append(P("   " + line, 8.5))
        story.append(Spacer(1, 4))
        first = 30 * mm
        col = (width - first) / len(BODY_PARTS)
        data = [[P("통증 부위", 8.5, True, 1)] + [P(part_header(r, p), 8.5, True, 1) for p in BODY_PARTS]]
        for field, label in PART_QUESTIONS:
            data.append([P(label, 7.5, True)] +
                        [P("\n".join(part_cell(r, p, field)), 7.3) for p in BODY_PARTS])
        t = Table(data, colWidths=[first] + [col] * len(BODY_PARTS))
        t.setStyle(TableStyle(grid + [
            ("BACKGROUND", (0, 0), (-1, 0), head_bg),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F7F9FC")),
            ("VALIGN", (1, 1), (-1, -1), "TOP")]))
        story.append(t)
        story.append(Spacer(1, 6))
        story.append(P("<보기> 아픈 정도", 8.5, True))
        for k, v in SEVERITY_GUIDE.items():
            story.append(P(f"   · {k}: {v}", 8))
        story.append(Spacer(1, 6))
        story.append(P("※ " + NOTICE_USE, 7.5))

        if include_judgment:
            rows, final = judgment_rows(r)
            story.append(Spacer(1, 8))
            story.append(P("【관리자용】 판정 결과 (KOSHA GUIDE E-G-1-2025 8.1 표 2)", 9, True))
            story.append(Spacer(1, 3))
            data = [[P(p, 8, True, 1) for p, _ in rows] + [P("최종판정", 8, True, 1)],
                    [P(j, 8.5, j != "정상", 1) for _, j in rows] + [P(final, 9, True, 1)]]
            t = Table(data, colWidths=[width / 7] * 7)
            color = {"통증호소자": "#F8D7DA", "관리대상자": "#FFF3CD"}.get(final)
            style = grid + [("BACKGROUND", (0, 0), (-1, 0), head_bg)]
            if color:
                style.append(("BACKGROUND", (-1, 1), (-1, 1), colors.HexColor(color)))
            t.setStyle(TableStyle(style))
            story.append(t)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title=FORM_TITLE)
    doc.build(story)
    return buf.getvalue()


# =========================================================
# 엑셀 집계표
# =========================================================

def summary_tables(records):
    """집계용 표(개인 식별정보 없음)를 pandas DataFrame 으로."""
    import pandas as pd

    rows = []
    for r in records:
        j = judge_record(r)
        row = {"작업부서": _clean(r.get("작업부서")) or "(미기재)",
               "증상여부": norm(r.get("근골격계증상여부")) or "",
               "최종판정": j["최종판정"]}
        for p in BODY_PARTS:
            row[f"{p}_증상"] = (row["증상여부"] == "예" and r.get(f"{p}_증상여부") == "예")
            row[f"{p}_판정"] = j[f"{p}_판정"]
        rows.append(row)
    df = pd.DataFrame(rows)
    total = len(df)

    def pct(n):
        return round(n / total * 100, 1) if total else 0.0

    part_rows = []
    for p in BODY_PARTS:
        if total:
            sym = int(df[f"{p}_증상"].sum())
            mgmt = int((df[f"{p}_판정"] == "관리대상자").sum())
            pain = int((df[f"{p}_판정"] == "통증호소자").sum())
        else:
            sym = mgmt = pain = 0
        part_rows.append({"부위": p, "증상 응답(명)": sym, "증상 응답률(%)": pct(sym),
                          "관리대상자(명)": mgmt, "통증호소자(명)": pain,
                          "관리대상자+통증호소자(%)": pct(mgmt + pain)})
    by_part = pd.DataFrame(part_rows)

    dept_rows = []
    if total:
        for dept, g in df.groupby("작업부서"):
            n = len(g)
            dept_rows.append({
                "작업부서": dept, "응답자(명)": n,
                "정상(명)": int((g["최종판정"] == "정상").sum()),
                "관리대상자(명)": int((g["최종판정"] == "관리대상자").sum()),
                "통증호소자(명)": int((g["최종판정"] == "통증호소자").sum()),
                "관리대상자+통증호소자(%)": round(
                    (g["최종판정"] != "정상").sum() / n * 100, 1),
            })
    by_dept = pd.DataFrame(dept_rows, columns=[
        "작업부서", "응답자(명)", "정상(명)", "관리대상자(명)", "통증호소자(명)",
        "관리대상자+통증호소자(%)"])

    overall = pd.DataFrame([{
        "응답자(명)": total,
        "증상 응답(명)": int((df["증상여부"] == "예").sum()) if total else 0,
        "정상(명)": int((df["최종판정"] == "정상").sum()) if total else 0,
        "관리대상자(명)": int((df["최종판정"] == "관리대상자").sum()) if total else 0,
        "통증호소자(명)": int((df["최종판정"] == "통증호소자").sum()) if total else 0,
    }])
    return overall, by_part, by_dept


RAW_COLUMNS = [
    "제출일시", "조사연도", "성명", "성별", "연령", "결혼여부", "작업부서", "라인/세부부서",
    "수행작업", "현직장_근무년", "현직장_근무개월", "현재작업", "현재작업_수행년",
    "현재작업_수행개월", "1일근무시간", "휴식시간_분", "휴식횟수", "이전작업",
    "이전작업_수행년", "이전작업_수행개월", "취미활동", "가사노동", "질병진단여부",
    "진단질병", "질병현재상태", "과거손상여부", "과거손상부위", "육체적부담",
    "근골격계증상여부",
]
PART_FIELDS = ["증상여부", "통증부위", "지속기간", "증상정도", "빈도", "최근1주증상",
               "통증으로인한일", "통증으로인한일_기타", "판정"]


def build_xlsx(records, title="", include_personal=True):
    """연도별 보관·보고용 엑셀.

    include_personal=True : 집계 + 판정 대상자 명단 + 응답 원자료 (담당자 보관용)
    include_personal=False: 집계 시트만 (개인이 드러나지 않음, 공유·보고용)
    """
    import pandas as pd
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    overall, by_part, by_dept = summary_tables(records)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        start = 3
        overall.to_excel(w, "집계", index=False, startrow=start)
        by_part.to_excel(w, "집계", index=False, startrow=start + 4)
        by_dept.to_excel(w, "집계", index=False, startrow=start + 6 + len(by_part))
        ws = w.sheets["집계"]
        ws["A1"] = title or f"{FORM_TITLE} 집계표"
        ws["A1"].font = Font(size=14, bold=True)
        ws["A2"] = ("판정 기준: KOSHA GUIDE E-G-1-2025 8.1 표 2 · 생성일시 "
                    + datetime.now().strftime("%Y-%m-%d %H:%M"))
        ws["A2"].font = Font(size=9, color="666666")
        ws.cell(row=start, column=1, value="■ 전체 현황").font = Font(bold=True)
        ws.cell(row=start + 4, column=1, value="■ 신체부위별 현황").font = Font(bold=True)
        ws.cell(row=start + 6 + len(by_part), column=1, value="■ 부서별 현황").font = Font(bold=True)

        if include_personal:
            raw = []
            for r in records:
                j = judge_record(r)
                row = {c: _clean(r.get(c)) for c in RAW_COLUMNS}
                if not row["조사연도"]:
                    row["조사연도"] = survey_year(r) or ""
                for p in BODY_PARTS:
                    for f in PART_FIELDS:
                        row[f"{p}_{f}"] = (j[f"{p}_판정"] if f == "판정"
                                           else _clean(r.get(f"{p}_{f}")))
                row["최종판정"] = j["최종판정"]
                raw.append(row)
            raw_df = pd.DataFrame(raw)
            target = raw_df[raw_df["최종판정"] != "정상"] if len(raw_df) else raw_df
            cols = ["최종판정", "성명", "작업부서", "라인/세부부서", "수행작업", "연령", "성별"]
            judged_parts = []
            for r in target.to_dict("records") if len(target) else []:
                judged_parts.append(", ".join(
                    f"{p}({r[f'{p}_판정']})" for p in BODY_PARTS if r[f"{p}_판정"] != "정상"))
            target_df = target[cols].copy() if len(target) else pd.DataFrame(columns=cols)
            target_df["해당 부위"] = judged_parts
            order = {"통증호소자": 0, "관리대상자": 1}
            if len(target_df):
                target_df = target_df.sort_values("최종판정", key=lambda s: s.map(order))
            target_df.to_excel(w, "판정대상자 명단", index=False)
            raw_df.to_excel(w, "응답 원자료", index=False)

        thin = Side(style="thin", color="999999")
        head_fill = PatternFill("solid", fgColor="EEF2F7")
        for ws in w.sheets.values():
            for row in ws.iter_rows():
                for c in row:
                    if c.value is None or c.row <= 2:
                        continue
                    c.border = Border(top=thin, bottom=thin, left=thin, right=thin)
                    c.alignment = Alignment(vertical="center", wrap_text=False)
            # 머리글 행 강조
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("■"):
                        c.border = Border()
            for col in range(1, ws.max_column + 1):
                letter = get_column_letter(col)
                longest = max((len(str(c.value)) for c in ws[letter] if c.value is not None
                               and c.row > 2), default=8)
                ws.column_dimensions[letter].width = min(max(10, longest * 1.7), 40)
        for ws in w.sheets.values():
            header_rows = [1] if ws.title != "집계" else [start + 1, start + 5, start + 7 + len(by_part)]
            for hr in header_rows:
                for c in ws[hr]:
                    if c.value is not None:
                        c.font = Font(bold=True)
                        c.fill = head_fill
            if ws.title != "집계":
                ws.freeze_panes = "B2"
            # 인쇄 시 한 쪽 너비에 맞춤
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
            ws.page_setup.orientation = "landscape" if ws.title != "집계" else "portrait"
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
        if include_personal:
            red = PatternFill("solid", fgColor="F8D7DA")
            yellow = PatternFill("solid", fgColor="FFF3CD")
            ws = w.sheets["판정대상자 명단"]
            for row in ws.iter_rows(min_row=2):
                fill = {"통증호소자": red, "관리대상자": yellow}.get(row[0].value)
                if fill:
                    row[0].fill = fill
    return buf.getvalue()


# =========================================================
# 저장용 데이터 정리
# =========================================================

def finalize_record(answers):
    """화면 응답(dict) → 저장용 기록. 판정·호환 필드를 채웁니다."""
    r = dict(answers)
    now = datetime.now()
    r.setdefault("제출일시", now.strftime("%Y-%m-%d %H:%M:%S"))
    r.setdefault("조사연도", now.year)
    has = r.get("근골격계증상여부") == "예"
    selected = set(r.get("_선택부위") or [])
    for p in BODY_PARTS:
        on = has and p in selected
        r[f"{p}_증상여부"] = "예" if on else "아니오"
        if not on:
            for f in PART_FIELDS:
                if f not in ("증상여부", "판정"):
                    r[f"{p}_{f}"] = ""
        else:
            consequences = split_multi(r.get(f"{p}_통증으로인한일"))
            r[f"{p}_통증으로인한일"] = join_multi(consequences)
            # 예전 대시보드·보고서 호환 필드
            r[f"{p}_치료경험"] = "예" if "병원·한의원 치료" in consequences else "아니오"
        if not on:
            r[f"{p}_치료경험"] = ""
    r.pop("_선택부위", None)
    r.update(judge_record(r))
    for key in ("취미활동", "진단질병", "과거손상부위"):
        if isinstance(r.get(key), (list, tuple)):
            r[key] = join_multi(r[key])
    return r

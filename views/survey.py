"""근로자용 근골격계질환 증상조사 (5단계 화면, 다국어).

1 기본 사항 → 2 생활과 병력 → 3 통증 유무와 부위 → 4 부위별 세부 문항 → 5 확인과 제출
문항과 보기는 별지 제2호서식 그대로이며(survey_form.py), 판정은 제출 시 자동 처리됩니다.
화면 언어만 바뀌고, 응답 값은 항상 한국어 보기로 저장됩니다(survey_i18n.py).
"""

import smtplib
from datetime import datetime
from email.mime.text import MIMEText

import importlib

import streamlit as st

import survey_form as sf
import survey_i18n as i18n

if getattr(i18n, "VERSION", 0) < 3:   # 서버에 예전 번역 모듈이 남아 있으면 새로 읽음
    i18n = importlib.reload(i18n)
from session_query_cache import clear_session_query_cache

PREFIX = "w_"
STEPS = ["기본 사항", "생활과 병력", "통증 유무와 부위", "부위별 세부 문항", "확인과 제출"]


def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


SITE = secret("SITE_NAME", "") or sf.SITE_NAME

# ---------------------------------------------------------
# 단계를 넘어가도 입력값이 지워지지 않게 유지
# (Streamlit 은 화면에 없는 위젯의 값을 지우므로 매 실행마다 다시 보관)
# ---------------------------------------------------------
for _k in list(st.session_state.keys()):
    if isinstance(_k, str) and _k.startswith(PREFIX):
        st.session_state[_k] = st.session_state[_k]

ss = st.session_state
ss.setdefault("sv_step", 0)

LANGS = i18n.available_languages()
if ss.get("survey_lang") not in LANGS:
    ss["survey_lang"] = "ko"


def lang():
    return ss.get("survey_lang") or "ko"


def t(text, **kw):
    out = i18n.translate(text, lang())
    return out.format(**kw) if kw else out


def tf(option):
    """보기(한국어 값) → 화면 표시용."""
    return t(option)


def v(field):
    return ss.get(PREFIX + field)


def go(step):
    ss.sv_step = step
    ss.pop("sv_errors", None)


def reset_survey():
    for k in list(ss.keys()):
        if isinstance(k, str) and (k.startswith(PREFIX) or k.startswith("sv_")):
            del ss[k]


def language_picker():
    if len(LANGS) <= 1:
        return
    st.radio("🌐 언어 · Language", LANGS, index=None, horizontal=True,
             format_func=i18n.display_name, key="survey_lang")


# ---------------------------------------------------------
# 신체 그림
# ---------------------------------------------------------

def body_svg(selected):
    on, off, line = "#E4572E", "#E9EDF2", "#8A96A8"

    def c(part):
        return on if part in selected else off

    return f"""
<svg viewBox="0 0 220 330" width="100%" style="max-width:260px;display:block;margin:auto"
     xmlns="http://www.w3.org/2000/svg" role="img">
  <g stroke="{line}" stroke-width="1.5">
    <circle cx="110" cy="32" r="22" fill="#F4F6F9"/>
    <rect x="99" y="54" width="22" height="16" rx="4" fill="{c('목')}"/>
    <path d="M60 74 Q110 62 160 74 L160 92 L60 92 Z" fill="{c('어깨')}"/>
    <rect x="72" y="92" width="76" height="62" fill="#F4F6F9"/>
    <rect x="72" y="154" width="76" height="34" fill="{c('허리')}"/>
    <rect x="40" y="78" width="20" height="92" rx="9" fill="{c('팔/팔꿈치')}"/>
    <rect x="160" y="78" width="20" height="92" rx="9" fill="{c('팔/팔꿈치')}"/>
    <ellipse cx="50" cy="186" rx="12" ry="15" fill="{c('손/손목/손가락')}"/>
    <ellipse cx="170" cy="186" rx="12" ry="15" fill="{c('손/손목/손가락')}"/>
    <rect x="74" y="188" width="32" height="116" rx="10" fill="{c('다리/발')}"/>
    <rect x="114" y="188" width="32" height="116" rx="10" fill="{c('다리/발')}"/>
    <ellipse cx="88" cy="312" rx="18" ry="8" fill="{c('다리/발')}"/>
    <ellipse cx="132" cy="312" rx="18" ry="8" fill="{c('다리/발')}"/>
  </g>
  <g font-size="10" fill="#334" font-family="sans-serif" text-anchor="middle">
    <text x="110" y="66">{t('목')}</text><text x="110" y="86">{t('어깨')}</text>
    <text x="110" y="175">{t('허리')}</text><text x="110" y="250">{t('다리/발')}</text>
  </g>
</svg>"""


def choose_parts():
    label = t("아팠던 부위를 모두 누르세요")
    if hasattr(st, "pills"):
        return st.pills(label, sf.BODY_PARTS, selection_mode="multi", format_func=tf,
                        key=PREFIX + "_선택부위")
    return st.multiselect(label, sf.BODY_PARTS, format_func=tf, key=PREFIX + "_선택부위")


# ---------------------------------------------------------
# 단계별 화면
# ---------------------------------------------------------

CONSENT_LINES = [
    "수집 항목: 성명, 연령, 성별, 업체명·공정·작업 정보, 진단받은 질병, 과거 손상, 신체부위별 통증 정보",
    "이용 목적: 근골격계부담작업 유해요인조사 및 작업환경 개선, 근로자 건강관리",
    "보유 기간: 5년 (유해요인조사 결과 보존기간)",
    "열람 범위: 응답 원본은 보건관리 담당자만 열람하며, 집계 자료에는 개인이 드러나지 않습니다.",
    "동의를 거부할 수 있으며, 이 경우 담당자에게 종이 조사표를 요청해 주세요.",
]


def step_intro():
    language_picker()
    st.title(t(sf.FORM_TITLE))
    st.caption(SITE)
    with st.container(border=True):
        st.markdown(
            t("현재 업무와 관련하여 느끼는 신체 증상·불편감을 5단계로 나누어 여쭙니다.") + "  \n"
            + t("약 3~5분 정도 걸립니다.")
        )
        st.markdown(
            f"**{t('작성 전 확인해 주세요')}**\n"
            f"- {t('증상을 크게 또는 작게 평가하지 마시고 있는 그대로 응답해 주세요.')}\n"
            f"- {t('이 조사는 3년마다 실시하는 근골격계부담작업 유해요인조사의 일부입니다.')}\n"
            f"- {t(sf.NOTICE_USE)}"
        )
    with st.expander(t("개인정보(건강정보) 수집·이용 안내"), expanded=False):
        st.markdown("\n".join("- " + t(line) for line in CONSENT_LINES))
    agree = st.checkbox(t("위 안내를 읽었으며, 건강정보를 포함한 개인정보 수집·이용에 동의합니다."),
                        key=PREFIX + "_동의")
    if st.button(t("조사 시작하기  ›"), type="primary", width="stretch", disabled=not agree):
        go(1)
        st.rerun()


def step_basic():
    st.text_input(t("현장명"), value=SITE, disabled=True, key="sv_site_display")
    c1, c2 = st.columns(2)
    c1.text_input(t("성명") + " *", key=PREFIX + "성명")
    c2.number_input(t("연령 (만 나이)") + " *", min_value=15, max_value=100, value=None, step=1,
                    key=PREFIX + "연령")
    c1, c2 = st.columns(2)
    c1.radio(t("성별") + " *", sf.GENDER_OPTIONS, index=None, horizontal=True, format_func=tf,
             key=PREFIX + "성별")
    c2.radio(t("결혼여부"), sf.MARRIAGE_OPTIONS, index=None, horizontal=True, format_func=tf,
             key=PREFIX + "결혼여부")

    st.markdown(f"**{t('현 직장경력')}**")
    c1, c2 = st.columns(2)
    c1.number_input(t("년"), 0, 60, value=None, step=1, key=PREFIX + "현직장_근무년")
    c2.number_input(t("개월째 근무 중"), 0, 11, value=None, step=1, key=PREFIX + "현직장_근무개월")

    c1, c2 = st.columns(2)
    c1.text_input(t("업체명") + " *", placeholder=t("예: ○○건설"), key=PREFIX + "업체명")
    c2.text_input(t("공정"), placeholder=t("예: 철근, 형틀, 전기"), key=PREFIX + "공정")

    st.markdown(f"**{t('현재 하고 있는 작업 (구체적으로)')}**")
    st.text_input(t("작업내용"), placeholder=t("예: 철근 운반·결속"), key=PREFIX + "현재작업")
    c1, c2 = st.columns(2)
    c1.number_input(t("작업기간 - 년"), 0, 60, value=None, step=1, key=PREFIX + "현재작업_수행년")
    c2.number_input(t("개월째 하고 있음"), 0, 11, value=None, step=1, key=PREFIX + "현재작업_수행개월")

    st.markdown(f"**{t('1일 근무시간')}**")
    c1, c2, c3 = st.columns(3)
    c1.number_input(t("시간"), 0.0, 24.0, value=None, step=0.5, key=PREFIX + "1일근무시간")
    c2.number_input(t("휴식시간(식사 제외) 분씩"), 0, 300, value=None, step=5, key=PREFIX + "휴식시간_분")
    c3.number_input(t("회 휴식"), 0, 30, value=None, step=1, key=PREFIX + "휴식횟수")

    st.markdown(f"**{t('현 작업을 하기 전에 했던 작업')}**")
    st.text_input(t("작업내용"), placeholder=t("없으면 '없음'"), key=PREFIX + "이전작업")
    c1, c2 = st.columns(2)
    c1.number_input(t("작업기간 - 년"), 0, 60, value=None, step=1, key=PREFIX + "이전작업_수행년")
    c2.number_input(t("개월 동안 했음"), 0, 11, value=None, step=1, key=PREFIX + "이전작업_수행개월")


def check_basic():
    errors = []
    if not (v("성명") or "").strip():
        errors.append(t("성명을 입력해 주세요."))
    if v("연령") is None:
        errors.append(t("연령을 입력해 주세요."))
    if not v("성별"):
        errors.append(t("성별을 선택해 주세요."))
    if not (v("업체명") or "").strip():
        errors.append(t("업체명을 입력해 주세요."))
    return errors


def step_history():
    st.markdown(f"**{t(sf.Q_HOBBY)}**")
    st.multiselect(t("해당 항목 모두 선택"), sf.HOBBY_OPTIONS, format_func=tf,
                   key=PREFIX + "취미활동", placeholder=t("선택하세요"))

    st.markdown(f"**{t(sf.Q_HOUSEWORK)}**")
    st.radio("2", sf.HOUSEWORK_OPTIONS, index=None, format_func=tf, key=PREFIX + "가사노동",
             label_visibility="collapsed")

    st.markdown(f"**{t(sf.Q_DISEASE)}**")
    st.caption("(" + t("보기") + ": " + ", ".join(t(d) for d in sf.DISEASE_OPTIONS) + ")")
    st.radio("3", sf.YES_NO, index=None, horizontal=True, format_func=tf,
             key=PREFIX + "질병진단여부", label_visibility="collapsed")
    if v("질병진단여부") == "예":
        st.multiselect(t("진단받은 질병"), sf.DISEASE_OPTIONS, format_func=tf,
                       key=PREFIX + "진단질병", placeholder=t("선택하세요"))
        st.radio(t("현재상태는?"), sf.DISEASE_STATUS_OPTIONS, index=None, horizontal=True,
                 format_func=tf, key=PREFIX + "질병현재상태")

    st.markdown(f"**{t(sf.Q_INJURY)}**")
    st.radio("4", sf.YES_NO, index=None, horizontal=True, format_func=tf,
             key=PREFIX + "과거손상여부", label_visibility="collapsed")
    if v("과거손상여부") == "예":
        st.multiselect(t("상해 부위는?"), sf.INJURY_PARTS, format_func=tf,
                       key=PREFIX + "과거손상부위", placeholder=t("선택하세요"))

    st.markdown(f"**{t(sf.Q_LOAD)}**")
    st.radio("5", sf.LOAD_OPTIONS, index=None, horizontal=True, format_func=tf,
             key=PREFIX + "육체적부담", label_visibility="collapsed")


def check_history():
    errors = []
    hobbies = v("취미활동") or []
    if not hobbies:
        errors.append(t("1번(여가 및 취미활동): 해당 항목을 선택해 주세요. 없으면 '해당사항 없음'."))
    elif "해당사항 없음" in hobbies and len(hobbies) > 1:
        errors.append(t("1번: '해당사항 없음'은 다른 항목과 함께 고를 수 없습니다."))
    if not v("가사노동"):
        errors.append(t("2번(가사노동시간)을 선택해 주세요."))
    if not v("질병진단여부"):
        errors.append(t("3번(질병 진단)을 선택해 주세요."))
    elif v("질병진단여부") == "예":
        if not v("진단질병"):
            errors.append(t("3번: 진단받은 질병을 선택해 주세요."))
        if not v("질병현재상태"):
            errors.append(t("3번: 현재상태를 선택해 주세요."))
    if not v("과거손상여부"):
        errors.append(t("4번(과거 손상)을 선택해 주세요."))
    elif v("과거손상여부") == "예" and not v("과거손상부위"):
        errors.append(t("4번: 상해 부위를 선택해 주세요."))
    if not v("육체적부담"):
        errors.append(t("5번(육체적 부담 정도)을 선택해 주세요."))
    return errors


def step_symptom():
    st.markdown(f"**{t(sf.Q_SYMPTOM)}**")
    st.radio("symptom", sf.YES_NO, index=None, horizontal=True, format_func=tf,
             key=PREFIX + "근골격계증상여부", label_visibility="collapsed")
    if v("근골격계증상여부") == "예":
        c1, c2 = st.columns([1, 1.2])
        with c2:
            selected = choose_parts() or []
            st.caption(t("그림에서 선택한 부위가 빨간색으로 표시됩니다."))
        with c1:
            st.markdown(body_svg(selected), unsafe_allow_html=True)
    elif v("근골격계증상여부") == "아니오":
        st.success(t("통증이 없으시면 다음 단계에서 바로 제출할 수 있습니다."))


def check_symptom():
    if not v("근골격계증상여부"):
        return [t("증상 여부를 선택해 주세요.")]
    if v("근골격계증상여부") == "예" and not v("_선택부위"):
        return [t("아팠던 부위를 하나 이상 선택해 주세요.")]
    return []


def step_parts():
    parts = [p for p in sf.BODY_PARTS if p in (v("_선택부위") or [])]
    with st.expander(t("<보기> 아픈 정도 기준"), expanded=True):
        for k, txt in sf.SEVERITY_GUIDE.items():
            st.markdown(f"- **{t(k)}**: {t(txt)}")
    q = dict(sf.PART_QUESTIONS)
    for part in parts:
        with st.container(border=True):
            st.subheader(f"📍 {t(part)}")
            if part in sf.SIDE_PARTS:
                st.radio(t(q["통증부위"]), sf.SIDE_OPTIONS, index=None, horizontal=True,
                         format_func=tf, key=f"{PREFIX}{part}_통증부위")
            st.radio(t(q["지속기간"]), sf.DURATION_OPTIONS, index=None, format_func=tf,
                     key=f"{PREFIX}{part}_지속기간")
            st.radio(t(q["증상정도"]), sf.SEVERITY_OPTIONS, index=None, format_func=tf,
                     key=f"{PREFIX}{part}_증상정도",
                     captions=[t(sf.SEVERITY_GUIDE[o]) for o in sf.SEVERITY_OPTIONS])
            st.radio(t(q["빈도"]), sf.FREQUENCY_OPTIONS, index=None, format_func=tf,
                     key=f"{PREFIX}{part}_빈도")
            st.radio(t(q["최근1주증상"]), sf.YES_NO, index=None, horizontal=True, format_func=tf,
                     key=f"{PREFIX}{part}_최근1주증상")
            st.multiselect(t(q["통증으로인한일"]), sf.CONSEQUENCE_OPTIONS, format_func=tf,
                           key=f"{PREFIX}{part}_통증으로인한일",
                           placeholder=t("해당 항목 모두 선택"))
            if "기타" in (v(f"{part}_통증으로인한일") or []):
                st.text_input(t("기타 내용"), key=f"{PREFIX}{part}_통증으로인한일_기타")


def check_parts():
    errors = []
    for part in [p for p in sf.BODY_PARTS if p in (v("_선택부위") or [])]:
        missing = []
        if part in sf.SIDE_PARTS and not v(f"{part}_통증부위"):
            missing.append(t("1번 구체적 부위"))
        for no, field in [(2, "지속기간"), (3, "증상정도"), (4, "빈도"), (5, "최근1주증상")]:
            if not v(f"{part}_{field}"):
                missing.append(t("{n}번", n=no))
        conseq = v(f"{part}_통증으로인한일") or []
        if not conseq:
            missing.append(t("{n}번", n=6))
        elif "해당사항 없음" in conseq and len(conseq) > 1:
            errors.append(t("{part}: 6번 '해당사항 없음'은 다른 항목과 함께 고를 수 없습니다.",
                            part=t(part)))
        elif "기타" in conseq and not (v(f"{part}_통증으로인한일_기타") or "").strip():
            missing.append(t("6번 기타 내용"))
        if missing:
            errors.append(t("{part}: {items} 응답이 필요합니다.", part=t(part),
                            items=", ".join(missing)))
    return errors


def collect():
    data = {}
    for k in list(ss.keys()):
        if isinstance(k, str) and k.startswith(PREFIX) and k != PREFIX + "_동의":
            val = ss[k]
            if isinstance(val, str):
                val = val.strip()
            data[k[len(PREFIX):]] = val
    # 조건부 문항: 상위 응답이 '예'가 아니면 하위 응답은 버림
    if data.get("질병진단여부") != "예":
        data["진단질병"], data["질병현재상태"] = [], ""
    if data.get("과거손상여부") != "예":
        data["과거손상부위"] = []
    for part in sf.BODY_PARTS:
        if "기타" not in (data.get(f"{part}_통증으로인한일") or []):
            data[f"{part}_통증으로인한일_기타"] = ""
    # 현장·업체·공정 (대시보드·보고서가 쓰는 예전 칸에도 같은 값을 넣음)
    data["현장명"] = SITE
    data["업체명"] = data.get("업체명") or ""
    data["공정"] = data.get("공정") or ""
    data["작업부서"] = data["업체명"]
    data["라인/세부부서"] = data["공정"]
    data["응답언어"] = i18n.stored_name(lang())
    return sf.finalize_record(data)


def step_confirm():
    record = collect()
    st.markdown(t("응답 내용을 확인해 주세요. 고칠 부분이 있으면 '이전'으로 돌아가 수정할 수 있습니다."))
    with st.container(border=True):
        process = f" · {record['공정']}" if record.get("공정") else ""
        st.markdown(
            f"**{record.get('성명', '')}** · {record.get('연령', '')} · {tf(record.get('성별') or '')}  \n"
            f"{record.get('업체명', '')}{process}"
        )
        if record.get("근골격계증상여부") == "예":
            for p in sf.BODY_PARTS:
                if record.get(f"{p}_증상여부") == "예":
                    side = record.get(f"{p}_통증부위")
                    vals = [record.get(f"{p}_{f}") for f in ("지속기간", "증상정도", "빈도")]
                    side_txt = f" ({tf(side)})" if side else ""
                    st.markdown(f"- **{t(p)}**{side_txt}: " + " · ".join(tf(x) for x in vals if x))
        else:
            st.markdown("- " + t("지난 1년간 작업 관련 근골격계 증상: 없음"))
    st.checkbox(t("입력한 내용이 사실과 같음을 확인합니다."), key="sv_confirm")


# ---------------------------------------------------------
# 제출 처리
# ---------------------------------------------------------

def get_supabase():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def already_submitted(client, record):
    """같은 해에 같은 성명·업체·성별로 낸 응답이 있는지 확인 (중복 제출 방지).

    survey_results 에 RLS 가 걸려 있으면 근로자 화면(익명)은 조회할 수 없으므로
    supabase/survey_duplicate_check.sql 의 함수를 먼저 사용합니다."""
    year = int(record.get("조사연도") or datetime.now().year)
    try:
        res = client.rpc("survey_already_submitted", {
            "p_name": record.get("성명", ""),
            "p_department": record.get("작업부서", ""),
            "p_gender": record.get("성별") or "",
            "p_year": year,
        }).execute()
        if isinstance(res.data, bool):
            return res.data
    except Exception:
        pass  # 함수가 없으면 아래 직접 조회로
    try:
        res = (client.table("survey_results").select("id, survey_data")
               .eq("name", record.get("성명", ""))
               .eq("department", record.get("작업부서", ""))
               .gte("created_at", f"{year}-01-01")
               .execute())
    except Exception:
        return False
    for row in res.data or []:
        prev = row.get("survey_data") or {}
        if not prev.get("성별") or prev.get("성별") == record.get("성별"):
            return True
    return False


def send_alert(record):
    """통증호소자 응답이 들어오면 담당자에게 메일 (설정된 경우만).
    메일에는 성명·건강정보를 넣지 않고, 관리자 화면에서 확인하도록 안내합니다."""
    to = secret("ALERT_EMAIL_TO")
    host = secret("SMTP_HOST")
    if not (to and host):
        return
    try:
        body = (
            f"[{sf.FORM_TITLE}] 통증호소자로 판정된 응답이 접수되었습니다.\n\n"
            f"- 접수 시각: {record.get('제출일시')}\n"
            f"- 업체명: {record.get('업체명', '')}\n\n"
            "개인 응답 내용은 관리자 화면(증상조사표 출력·보관 / 대시보드)에서 확인해 주세요."
        )
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = f"[증상조사] 통증호소자 응답 접수 - {record.get('업체명', '')}"
        sender = secret("SMTP_FROM") or secret("SMTP_USER")
        msg["From"] = sender
        msg["To"] = to
        with smtplib.SMTP(host, int(secret("SMTP_PORT", 587)), timeout=10) as s:
            s.starttls()
            if secret("SMTP_USER"):
                s.login(secret("SMTP_USER"), secret("SMTP_PASSWORD"))
            s.sendmail(sender, [x.strip() for x in str(to).split(",")], msg.as_string())
    except Exception:
        pass  # 알림 실패가 제출을 막지 않도록


def submit():
    record = collect()
    try:
        client = get_supabase()
    except Exception as e:
        st.error(t("저장소 연결에 실패했습니다. 담당자에게 알려 주세요.") + f" ({e})")
        return
    if already_submitted(client, record):
        st.error(t("올해 같은 성명·업체로 제출된 응답이 이미 있습니다. 내용을 고쳐야 하면 보건관리 담당자에게 알려 주세요."))
        return
    db_data = {
        "name": record.get("성명", ""),
        "gender": record.get("성별", ""),
        "age": int(record["연령"]) if record.get("연령") is not None else None,
        "marriage": record.get("결혼여부") or "",
        "department": record.get("작업부서", ""),
        "sub_department": record.get("라인/세부부서", ""),
        "current_work": record.get("현재작업", ""),
        "symptom_exists": record.get("근골격계증상여부", ""),
        "final_judgment": record.get("최종판정", ""),
        "survey_data": record,
    }
    try:
        client.table("survey_results").insert(db_data).execute()
    except Exception as e:
        st.error(t("저장 중 오류가 발생했습니다. 잠시 후 다시 눌러 주세요.") + f" ({e})")
        return
    clear_session_query_cache()
    if record.get("최종판정") == "통증호소자":
        send_alert(record)
    ss.sv_done = record
    go(6)
    st.rerun()


def step_done():
    record = ss.get("sv_done") or {}
    st.title(t("제출이 완료되었습니다"))
    st.success(t("응답해 주셔서 감사합니다. 결과는 작업환경 개선에 활용됩니다."))
    st.caption(t("통증이 계속되거나 심해지면 보건관리 담당자와 상담해 주세요."))
    try:
        if sf.pdf_available():
            st.download_button(t("내 응답 사본 받기 (PDF)"), sf.build_pdf([record]),
                               f"{sf.file_stem(record)}_증상조사표.pdf", "application/pdf",
                               width="stretch")
        else:
            st.download_button(
                t("내 응답 사본 받기 (Word)"), sf.build_docx([record]),
                f"{sf.file_stem(record)}_증상조사표.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch")
        if lang() != "ko":
            st.caption(t("사본은 한국어 공식 서식으로 제공됩니다."))
    except Exception:
        pass
    if st.button(t("새 응답 작성 (다른 사람)"), width="stretch"):
        reset_survey()
        st.rerun()


# ---------------------------------------------------------
# 화면 구성
# ---------------------------------------------------------

step = ss.sv_step

if step == 0:
    step_intro()
    st.stop()
if step == 6:
    step_done()
    st.stop()

top_l, top_r = st.columns([1.4, 1])
with top_l:
    st.markdown(f"#### {t(sf.FORM_TITLE)}")
with top_r:
    language_picker()

no_symptom = v("근골격계증상여부") == "아니오"
st.progress(step / 5, text=t("{step} / 5 단계", step=step) + " · " + t(STEPS[step - 1]))
st.header(f"{step}. {t(STEPS[step - 1])}")

screens = {1: (step_basic, check_basic), 2: (step_history, check_history),
           3: (step_symptom, check_symptom), 4: (step_parts, check_parts),
           5: (step_confirm, lambda: [])}
render, check = screens[step]
render()

for msg in ss.get("sv_errors", []):
    st.error(msg)

st.divider()
left, right = st.columns(2)
prev_step = 3 if (step == 5 and no_symptom) else step - 1
if left.button(t("‹ 이전"), width="stretch"):
    go(prev_step)
    st.rerun()

if step < 5:
    if right.button(t("다음 ›"), type="primary", width="stretch"):
        errors = check()
        if errors:
            ss.sv_errors = errors
            st.rerun()
        # 통증이 없으면 서식처럼 4단계(부위별 문항)를 건너뜀
        go(5 if (step == 3 and no_symptom) else step + 1)
        st.rerun()
else:
    if right.button(t("제출하기"), type="primary", width="stretch",
                    disabled=not ss.get("sv_confirm")):
        with st.spinner(t("저장 중입니다…")):
            submit()

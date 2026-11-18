"""관리자: 증상조사표 출력·보관.

- 응답자별 조사표를 별지 제2호서식 형태(Word / PDF)로 출력
- 여러 명을 한 파일로 일괄 출력하거나 개별 파일 묶음(ZIP)으로 내려받기
- 조사연도별 집계·보관용 엑셀 (담당자 보관용 / 개인정보 없는 보고용)
- 종이 조사표가 필요한 근로자용 빈 양식
- 예전 판정 방식으로 저장된 응답을 현행 기준으로 다시 판정
"""

import io
import zipfile
from datetime import datetime

import pandas as pd
import streamlit as st

import survey_form as sf
from auth import get_authenticated_supabase, logout_button, require_admin
from session_query_cache import clear_session_query_cache, get_cached_query
from ui_theme import apply_theme

require_admin()
apply_theme()
UNKNOWN_COMPANY = "업체 미분류"

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


ORG = secret("ORG_NAME", "")


supabase = get_authenticated_supabase()


def _fetch_rows():
    return (supabase.table("survey_results").select("*")
            .order("created_at", desc=True).execute().data or [])


def load_records():
    rows = get_cached_query("survey_print_rows", _fetch_rows)
    records = []
    for row in rows:
        r = dict(row.get("survey_data") or {})
        fallback = {"성명": "name", "성별": "gender", "연령": "age", "결혼여부": "marriage",
                    "작업부서": "department", "라인/세부부서": "sub_department",
                    "현재작업": "current_work", "근골격계증상여부": "symptom_exists"}
        for k, col in fallback.items():
            if not r.get(k) and row.get(col) not in (None, ""):
                r[k] = row.get(col)
        if not r.get("제출일시") and row.get("created_at"):
            r["제출일시"] = str(row["created_at"])[:19].replace("T", " ")
        if not r.get("업체명") and (row.get("company") or row.get("company_name")):
            r["업체명"] = row.get("company") or row.get("company_name")
        r["_업체"] = sf.company_of(r) or UNKNOWN_COMPANY
        r["_id"] = row.get("id")
        r["_저장판정"] = row.get("final_judgment") or r.get("최종판정") or ""
        r["_판정"] = sf.judge_record(r)["최종판정"]
        r["_연도"] = sf.survey_year(r) or sf.survey_year({"created_at": row.get("created_at")})
        records.append(r)
    return records


st.title("🖨️ 증상조사표 출력·보관")
logout_button()
st.caption(
    "응답을 별지 제2호서식 형태로 출력하고, 조사연도별로 내려받아 보관합니다. "
    "판정은 KOSHA GUIDE E-G-1-2025 8.1 표 2 기준입니다."
)

tab_out, tab_xlsx, tab_blank, tab_fix = st.tabs(
    ["응답자 조사표 출력", "집계·보관 엑셀", "빈 양식(종이 조사용)", "판정 재계산"])

# ---------------------------------------------------------
# 빈 양식은 DB 없이도 동작
# ---------------------------------------------------------
with tab_blank:
    st.write("스마트폰 사용이 어려운 근로자에게 나눠 줄 빈 조사표입니다. 문항과 보기는 서식 그대로입니다.")
    c1, c2 = st.columns(2)
    c1.download_button("빈 양식 Word", sf.build_docx([{}], ORG), "근골격계질환_증상조사표_빈양식.docx",
                       DOCX_MIME, width="stretch")
    if sf.pdf_available():
        c2.download_button("빈 양식 PDF", sf.build_pdf([{}], ORG), "근골격계질환_증상조사표_빈양식.pdf",
                           "application/pdf", width="stretch")
    st.caption("종이로 받은 조사표는 근로자용 설문 화면에 대신 입력하면 집계에 함께 반영됩니다.")

try:
    records = load_records()
except Exception as e:
    for t in (tab_out, tab_xlsx, tab_fix):
        with t:
            st.error(f"응답을 불러오지 못했습니다: {e}")
    st.stop()

if not records:
    for t in (tab_out, tab_xlsx, tab_fix):
        with t:
            st.info("아직 제출된 응답이 없습니다.")
    st.stop()

years = sorted({r["_연도"] for r in records if r["_연도"]}, reverse=True)

# ---------------------------------------------------------
# 응답자 조사표 출력
# ---------------------------------------------------------
with tab_out:
    c0, c1, c2, c3, c4 = st.columns([1.3, 1, 1.4, 1.4, 1.2])
    year = c1.selectbox("조사연도", years, key="po_year")
    companies = sorted({r["_업체"] for r in records})
    company = c0.selectbox("업체", ["전체 업체"] + companies, key="po_company")
    pool = [r for r in records if r["_연도"] == year
            and (company == "전체 업체" or r["_업체"] == company)]
    depts = sorted({str(r.get("작업부서") or "(미기재)") for r in pool})
    dept = c2.multiselect("작업부서", depts, placeholder="전체")
    judg = c3.multiselect("판정", sf.JUDGMENTS, placeholder="전체")
    name_q = c4.text_input("성명 검색")

    shown = [r for r in pool
             if (not dept or str(r.get("작업부서") or "(미기재)") in dept)
             and (not judg or r["_판정"] in judg)
             and (not name_q or name_q.strip() in str(r.get("성명", "")))]

    table = pd.DataFrame([{
        "선택": True,
        "제출일시": r.get("제출일시", ""),
        "업체": r["_업체"],
        "성명": r.get("성명", ""),
        "작업부서": r.get("작업부서", ""),
        "라인": r.get("라인/세부부서", ""),
        "판정": r["_판정"],
    } for r in shown])

    if table.empty:
        st.info("조건에 맞는 응답이 없습니다.")
    else:
        edited = st.data_editor(
            table, hide_index=True, width="stretch",
            disabled=["제출일시", "업체", "성명", "작업부서", "라인", "판정"],
            column_config={"선택": st.column_config.CheckboxColumn("선택", width="small")},
            key=f"po_table_{company}_{year}_{len(shown)}")
        chosen = [shown[i] for i, on in enumerate(edited["선택"].tolist()) if on]
        st.caption(f"{len(shown)}명 중 {len(chosen)}명 선택")

        c1, c2 = st.columns(2)
        fmt = c1.radio("파일 형식", ["PDF", "Word"] if sf.pdf_available() else ["Word"],
                       horizontal=True)
        mode = c2.radio("묶는 방식", ["한 파일로 합치기", "1인 1파일(ZIP)"], horizontal=True)
        with_judg = st.checkbox("관리자용 판정 결과 표 포함", value=True,
                                help="근로자에게 돌려줄 사본이면 체크를 해제하세요.")

        if chosen and st.button("출력 파일 만들기", type="primary", width="stretch"):
            ext, mime = (("pdf", "application/pdf") if fmt == "PDF" else ("docx", DOCX_MIME))
            build = sf.build_pdf if fmt == "PDF" else sf.build_docx
            with st.spinner(f"{len(chosen)}명 조사표를 만드는 중…"):
                if mode == "한 파일로 합치기" or len(chosen) == 1:
                    data = build(chosen, ORG, with_judg)
                    name = (f"{sf.file_stem(chosen[0])}_증상조사표.{ext}" if len(chosen) == 1
                            else f"{year}_근골격계증상조사표_{len(chosen)}명.{ext}")
                else:
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                        used = set()
                        for r in chosen:
                            stem = sf.file_stem(r)
                            n = 2
                            while stem in used:
                                stem = f"{sf.file_stem(r)}_{n}"
                                n += 1
                            used.add(stem)
                            z.writestr(f"{stem}.{ext}", build([r], ORG, with_judg))
                    data, ext, mime = buf.getvalue(), "zip", "application/zip"
                    name = f"{year}_근골격계증상조사표_{len(chosen)}명.zip"
            st.session_state.po_file = (data, name, mime)

        if st.session_state.get("po_file"):
            data, name, mime = st.session_state.po_file
            st.download_button(f"⬇️ {name} 내려받기", data, name, mime, width="stretch")

# ---------------------------------------------------------
# 집계·보관 엑셀
# ---------------------------------------------------------
with tab_xlsx:
    c1, c2 = st.columns(2)
    company_x = c1.selectbox("업체", ["전체 업체"] + sorted({r["_업체"] for r in records}),
                             key="px_company")
    year_x = c2.selectbox("조사연도", years, key="px_year")
    pool = [r for r in records if r["_연도"] == year_x
            and (company_x == "전체 업체" or r["_업체"] == company_x)]
    overall, by_part, by_dept = sf.summary_tables(pool)
    c = st.columns(4)
    o = overall.iloc[0]
    c[0].metric("응답자", f"{o['응답자(명)']}명")
    c[1].metric("증상 응답", f"{o['증상 응답(명)']}명")
    c[2].metric("관리대상자", f"{o['관리대상자(명)']}명")
    c[3].metric("통증호소자", f"{o['통증호소자(명)']}명")
    st.dataframe(by_part, hide_index=True, width="stretch")
    st.dataframe(by_dept, hide_index=True, width="stretch")

    who = company_x if company_x not in ("전체 업체", UNKNOWN_COMPANY) else ORG
    title = f"{year_x}년 {sf.FORM_TITLE} 결과" + (f" ({who})" if who else "")
    stamp = datetime.now().strftime("%Y%m%d")
    c1, c2 = st.columns(2)
    c1.download_button(
        "담당자 보관용 엑셀 (원자료·명단 포함)", sf.build_xlsx(pool, title, True),
        f"{year_x}_{'' if company_x == '전체 업체' else company_x + '_'}근골격계증상조사_보관용_{stamp}.xlsx", XLSX_MIME, width="stretch",
        help="건강정보가 들어 있습니다. 담당자만 열람할 수 있는 곳에 5년간 보관하세요.")
    c2.download_button(
        "보고·공유용 엑셀 (집계만)", sf.build_xlsx(pool, title, False),
        f"{year_x}_{'' if company_x == '전체 업체' else company_x + '_'}근골격계증상조사_집계_{stamp}.xlsx", XLSX_MIME, width="stretch",
        help="개인이 드러나지 않는 숫자 집계만 들어 있습니다.")
    st.info(
        "보존 기간(KOSHA GUIDE E-G-1-2025 10): 유해요인조사 결과(증상 설문조사 결과 포함) 5년. "
        "조사가 끝나면 연도별로 내려받아 보관해 두세요. "
        "또한 유해요인조사 결과와 조사방법을 해당 근로자에게 알려야 합니다(안전보건규칙 제661조 제2항)."
    )

# ---------------------------------------------------------
# 판정 재계산
# ---------------------------------------------------------
with tab_fix:
    diff = [r for r in records if r["_저장판정"] != r["_판정"]]
    st.write(
        "이전 버전에서는 판정 규칙이 KOSHA 기준과 달랐습니다. 저장된 판정과 현행 기준 판정이 "
        "다른 응답을 찾아 저장 값을 고칩니다. (응답 내용은 바뀌지 않습니다.)"
    )
    if not diff:
        st.success("모든 응답이 현행 기준 판정과 일치합니다.")
    else:
        st.dataframe(pd.DataFrame([{
            "제출일시": r.get("제출일시"), "성명": r.get("성명"), "작업부서": r.get("작업부서"),
            "저장된 판정": r["_저장판정"], "현행 기준 판정": r["_판정"]} for r in diff]),
            hide_index=True, width="stretch")
        ok = st.checkbox(f"{len(diff)}건의 저장 판정을 현행 기준으로 바꿉니다.")
        if st.button("판정 업데이트", disabled=not ok, type="primary"):
            client = supabase
            done = 0
            for r in diff:
                data = {k: val for k, val in r.items() if not k.startswith("_")}
                data.update(sf.judge_record(data))
                try:
                    (client.table("survey_results")
                     .update({"final_judgment": data["최종판정"], "survey_data": data})
                     .eq("id", r["_id"]).execute())
                    done += 1
                except Exception as e:
                    st.error(f"{r.get('성명')}: {e}")
            clear_session_query_cache()
            st.success(f"{done}건을 업데이트했습니다.")

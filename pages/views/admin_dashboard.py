import io

import pandas as pd
import streamlit as st

from auth import require_admin, logout_button, get_authenticated_supabase
from session_query_cache import get_cached_query, clear_session_query_cache


UNKNOWN_COMPANY_LABEL = "업체 미분류"


def normalize_symptom_response(value):

    text = "" if value is None else str(value).strip().casefold()
    compact = "".join(text.split())

    if not compact:
        return "미응답"

    if compact in {"아니오", "아니요", "no", "n", "false", "0", "없", "없음", "없다"}:
        return "아니오"

    if compact in {"예", "yes", "y", "true", "1", "있", "있음", "있다"}:
        return "예"

    if "아니" in compact or "없" in compact:
        return "아니오"

    if "있" in compact or compact.startswith("예"):
        return "예"

    return "미응답"


def survey_statistics(records):

    worker_responses = {}
    response_counts = {
        "예": 0,
        "아니오": 0,
        "미응답": 0
    }

    for row in records:
        response = row.get("symptom_exists")

        if response is None or not str(response).strip():
            response = row.get("근골격계증상여부")

        normalized = normalize_symptom_response(response)
        response_counts[normalized] += 1

        name = str(
            row.get("name")
            or row.get("성명")
            or ""
        ).strip().casefold()

        if not name:
            continue

        identity = tuple(
            str(value or "").strip().casefold()
            for value in (
                name,
                row.get("gender") or row.get("성별"),
                row.get("age") or row.get("연령"),
                row.get("department") or row.get("작업부서"),
                row.get("sub_department") or row.get("라인/세부부서"),
            )
        )

        worker_responses[identity] = (
            worker_responses.get(identity, False)
            or normalized == "예"
        )

    worker_count = len(worker_responses)
    symptomatic_workers = sum(worker_responses.values())

    return {
        "response_count": sum(response_counts.values()),
        "worker_count": worker_count,
        "symptom_responses": response_counts["예"],
        "no_symptom_responses": response_counts["아니오"],
        "unanswered_responses": response_counts["미응답"],
        "symptomatic_workers": symptomatic_workers,
        "symptom_rate": (
            symptomatic_workers / worker_count * 100
            if worker_count
            else 0
        ),
    }


def resolve_company_name(row, allow_department_prefix=False):

    for key in ("company", "company_name", "업체명", "사업장명"):
        value = str(row.get(key) or "").strip()

        if value:
            return value

    if allow_department_prefix:
        department = str(row.get("department") or "").strip()

        if " / " in department:
            return department.split(" / ", 1)[0].strip()

    return ""


def filter_company_records(records, selected_company, allow_department_prefix=False):

    if selected_company == "전체 업체":
        return list(records)

    if selected_company == UNKNOWN_COMPANY_LABEL:
        return [
            row
            for row in records
            if not resolve_company_name(
                row,
                allow_department_prefix
            )
        ]

    return [
        row
        for row in records
        if resolve_company_name(
            row,
            allow_department_prefix
        ) == selected_company
    ]


# =========================================================
# 관리자 인증
# =========================================================

require_admin()


# =========================================================
# Supabase 연결
# =========================================================

supabase = get_authenticated_supabase()


# =========================================================
# 데이터 불러오기
# =========================================================

def load_survey_data():

    try:
        rows = get_cached_query(
            "survey_results",
            lambda: (
                supabase
                .table("survey_results")
                .select("*")
                .order("created_at", desc=True)
                .execute()
                .data
                or []
            )
        )

    except Exception:
        rows = []

    merged_rows = []

    for row in rows:

        survey_json = row.get(
            "survey_data",
            {}
        ) or {}

        if not isinstance(survey_json, dict):
            survey_json = {}

        merged = dict(survey_json)

        merged["id"] = row.get("id")
        merged["created_at"] = row.get(
            "created_at"
        )

        merged["name"] = row.get(
            "name"
        )

        merged["gender"] = row.get(
            "gender"
        )

        merged["age"] = row.get(
            "age"
        )

        merged["marriage"] = row.get(
            "marriage"
        )

        merged["department"] = row.get(
            "department"
        )

        merged["sub_department"] = row.get(
            "sub_department"
        )

        merged["current_work"] = row.get(
            "current_work"
        )

        merged["symptom_exists"] = row.get(
            "symptom_exists"
        )

        merged["final_judgment"] = row.get(
            "final_judgment"
        )

        merged["company"] = (
            row.get("company")
            or row.get("company_name")
            or merged.get("company")
            or merged.get("company_name")
            or merged.get("업체명")
            or merged.get("사업장명")
            or ""
        )

        merged_rows.append(
            merged
        )

    return pd.DataFrame(
        merged_rows
    )


def load_reba_data():

    try:
        rows = get_cached_query(
            "reba_results",
            lambda: (
                supabase
                .table("reba_results")
                .select("*")
                .order("created_at", desc=True)
                .execute()
                .data
                or []
            )
        )

    except Exception:
        rows = []

    return pd.DataFrame(
        rows
    )


def load_improvement_data():

    try:
        rows = get_cached_query(
            "reba_improvements",
            lambda: (
                supabase
                .table("reba_improvements")
                .select("*")
                .order("created_at", desc=True)
                .execute()
                .data
                or []
            )
        )

    except Exception:
        rows = []

    return pd.DataFrame(rows)


def load_capture_queue():

    try:
        rows = get_cached_query(
            "reba_capture_queue",
            lambda: (
                supabase
                .table("reba_capture_queue")
                .select("*")
                .execute()
                .data
                or []
            )
        )
    except Exception:
        rows = []

    return pd.DataFrame(rows)


# =========================================================
# Excel 다운로드
# =========================================================

def make_excel(
    survey_df,
    reba_df,
    improvement_df=None
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        if not survey_df.empty:

            survey_excel = (
                survey_df.copy()
            )

            for column in (
                survey_excel.columns
            ):

                survey_excel[column] = (
                    survey_excel[column]
                    .apply(
                        lambda x:
                            str(x)
                            if isinstance(
                                x,
                                (
                                    dict,
                                    list
                                )
                            )
                            else x
                    )
                )

            survey_excel.to_excel(
                writer,
                sheet_name="근골격계 증상조사",
                index=False
            )


        if not reba_df.empty:

            reba_excel = (
                reba_df.copy()
            )

            for column in (
                reba_excel.columns
            ):

                reba_excel[column] = (
                    reba_excel[column]
                    .apply(
                        lambda x:
                            str(x)
                            if isinstance(
                                x,
                                (
                                    dict,
                                    list
                                )
                            )
                            else x
                    )
                )

            reba_excel.to_excel(
                writer,
                sheet_name="REBA 자세평가",
                index=False
            )


        if improvement_df is not None and not improvement_df.empty:

            improvement_excel = improvement_df.copy()

            for column in improvement_excel.columns:
                improvement_excel[column] = improvement_excel[column].apply(
                    lambda value: (
                        str(value)
                        if isinstance(value, (dict, list))
                        else value
                    )
                )

            improvement_excel.to_excel(
                writer,
                sheet_name="REBA 개선조치",
                index=False
            )

    output.seek(0)

    return output


# =========================================================
# 날짜 표시 함수
# =========================================================

def format_datetime_column(
    dataframe
):

    df = dataframe.copy()

    if (
        not df.empty
        and "created_at"
        in df.columns
    ):

        df["created_at"] = (
            pd.to_datetime(
                df["created_at"],
                errors="coerce"
            )
            .dt.strftime(
                "%Y-%m-%d %H:%M"
            )
        )

    return df


# =========================================================
# 페이지 시작
# =========================================================

st.title("관리자 통합 대시보드")

logout_button()

st.caption("업체별 조사 응답, REBA 평가와 개선조치 현황")


# =========================================================
# 데이터 로딩
# =========================================================

survey_df = load_survey_data()
reba_df = load_reba_data()
improvement_df = load_improvement_data()
capture_queue_df = load_capture_queue()

survey_records = survey_df.to_dict(orient="records")
reba_records = reba_df.to_dict(orient="records")
improvement_records = improvement_df.to_dict(orient="records")
capture_queue_records = capture_queue_df.to_dict(orient="records")

known_companies = {
    company
    for records, allow_department_prefix in (
        (survey_records, False),
        (reba_records, True),
        (improvement_records, True),
        (capture_queue_records, False),
    )
    for row in records
    if (company := resolve_company_name(row, allow_department_prefix))
}

has_unclassified_records = any(
    not resolve_company_name(row, allow_department_prefix)
    for records, allow_department_prefix in (
        (survey_records, False),
        (reba_records, True),
        (improvement_records, True),
        (capture_queue_records, False),
    )
    for row in records
)

company_filter_options = [
    "전체 업체",
    *sorted(known_companies),
]

if has_unclassified_records:
    company_filter_options.append(UNKNOWN_COMPANY_LABEL)

selected_company = st.selectbox(
    "업체별 조사 현황",
    company_filter_options,
    key="admin_company_filter"
)

survey_df = pd.DataFrame(
    filter_company_records(survey_records, selected_company),
    columns=survey_df.columns
)
reba_df = pd.DataFrame(
    filter_company_records(
        reba_records,
        selected_company,
        allow_department_prefix=True
    ),
    columns=reba_df.columns
)
improvement_df = pd.DataFrame(
    filter_company_records(
        improvement_records,
        selected_company,
        allow_department_prefix=True
    ),
    columns=improvement_df.columns
)
capture_queue_df = pd.DataFrame(
    filter_company_records(
        capture_queue_records,
        selected_company
    ),
    columns=capture_queue_df.columns
)

if selected_company != "전체 업체" and survey_df.empty:
    st.caption(
        "선택 업체로 식별할 수 있는 증상조사 자료가 없습니다. "
        "업체 정보가 없는 과거 설문은 업체별 통계에 포함하지 않습니다."
    )


# =========================================================
# 새로고침 버튼
# =========================================================

col_refresh, col_download = (
    st.columns(
        [1, 2]
    )
)


with col_refresh:

    if st.button(
        "🔄 데이터 새로고침",
        width="stretch"
    ):

        clear_session_query_cache()

        st.rerun()


with col_download:

    excel_file = make_excel(
        survey_df,
        reba_df,
        improvement_df
    )

    st.download_button(
        f"📥 {selected_company} 범위 Excel 다운로드",
        data=excel_file,
        file_name=(
            "근골격계_REBA_선택업체_통합관리.xlsx"
        ),
        mime=(
            "application/"
            "vnd.openxmlformats-"
            "officedocument."
            "spreadsheetml.sheet"
        ),
        width="stretch"
    )


st.divider()


# =========================================================
# 통합 요약
# =========================================================

st.subheader(
    "📌 전체 현황"
)


survey_summary = survey_statistics(
    survey_df.to_dict(orient="records")
)

total_survey = survey_summary["response_count"]
total_workers = survey_summary["worker_count"]


total_reba = len(
    reba_df
)


if (
    not reba_df.empty
    and "final_reba"
    in reba_df.columns
):

    reba_numeric = pd.to_numeric(
        reba_df[
            "final_reba"
        ],
        errors="coerce"
    )

    average_reba = (
        reba_numeric.mean()
    )

    high_risk_count = (
        reba_numeric >= 8
    ).sum()

else:

    average_reba = 0

    high_risk_count = 0

pending_review_count = int(
    capture_queue_df.get(
        "status",
        pd.Series(dtype=str)
    )
    .fillna("")
    .eq("대기")
    .sum()
)

if not reba_df.empty and "final_reba" in reba_df.columns:
    high_risk_rows = reba_df.loc[reba_numeric >= 8]

    def work_key(row):
        return (
            str(row.get("department") or "").strip().casefold(),
            str(row.get("task_name") or "").strip().casefold(),
        )

    improved_work_keys = {
        work_key(row)
        for row in improvement_df.to_dict(orient="records")
    }
    unaddressed_work_keys = {
        work_key(row)
        for row in high_risk_rows.to_dict(orient="records")
        if work_key(row) not in improved_work_keys
    }
    needs_supplement_count = len(high_risk_rows)
    unaddressed_count = len(unaddressed_work_keys)
else:
    needs_supplement_count = 0
    unaddressed_count = 0


m1, m2, m3, m4, m5 = (
    st.columns(5)
)


with m1:

    st.metric(
        "증상조사 응답",
        f"{total_survey}건"
    )


with m2:

    st.metric(
        "확인된 고유 근로자",
        f"{total_workers}명"
    )


with m3:

    st.metric(
        "REBA 평가",
        f"{total_reba}건"
    )

with m4:

    st.metric(
        "REBA 8점 이상",
        f"{high_risk_count}건"
    )

with m5:

    st.metric(
        "개선조치 기록",
        f"{len(improvement_df)}건"
    )


st.subheader("주요 업무 처리")
status_columns = st.columns(3)
status_columns[0].metric(
    "검토 대기",
    f"{pending_review_count}건",
    help="촬영 대기함에서 관리자 검토를 기다리는 항목입니다."
)
status_columns[1].metric(
    "보완 필요",
    f"{needs_supplement_count}건",
    help="REBA 8점 이상으로 개선 검토가 필요한 평가입니다."
)
status_columns[2].metric(
    "미조치 고위험 작업",
    f"{unaddressed_count}건",
    help="REBA 8점 이상이며 같은 공종·작업의 개선 이력이 없는 건수입니다."
)


st.divider()


# =========================================================
# TAB
# =========================================================

survey_tab, reba_tab = (
    st.tabs(
        [
            "🩺 근골격계 증상조사",
            "🤖 AI REBA 자세평가"
        ]
    )
)


# =========================================================
# 근골격계 증상조사
# =========================================================

with survey_tab:

    st.subheader(
        "근골격계 증상조사 현황"
    )


    if survey_df.empty:

        st.info(
            "저장된 근골격계 "
            "증상조사 결과가 없습니다."
        )

    else:

        # =================================================
        # 요약
        # =================================================

        total = survey_summary["response_count"]
        worker_count = survey_summary["worker_count"]
        symptom_count = survey_summary["symptomatic_workers"]
        symptom_responses = survey_summary["symptom_responses"]
        no_symptom_responses = survey_summary["no_symptom_responses"]
        unanswered_responses = survey_summary["unanswered_responses"]
        symptom_rate = survey_summary["symptom_rate"]


        judgment_series = (
            survey_df.get(
                "final_judgment",
                pd.Series(
                    dtype=str
                )
            )
            .fillna("")
            .astype(str)
        )


        normal_count = (
            judgment_series
            .str.contains(
                "정상",
                na=False
            )
            .sum()
        )


        management_count = (
            judgment_series
            .str.contains(
                "관리",
                na=False
            )
            .sum()
        )


        pain_count = (
            judgment_series
            .str.contains(
                "통증",
                na=False
            )
            .sum()
        )


        a, b, c, d = (
            st.columns(4)
        )


        with a:

            st.metric(
                "설문 응답 건수",
                f"{total}건"
            )


        with b:

            st.metric(
                "추정 고유 근로자",
                f"{worker_count}명"
            )


        with c:

            st.metric(
                "증상 경험 근로자",
                f"{symptom_count}명"
            )


        with d:

            st.metric(
                "증상 경험률",
                f"{symptom_rate:.1f}%"
            )


        st.caption(
            "고유 근로자는 성명·성별·연령·부서·세부부서가 같은 응답을 묶은 추정치입니다. "
            "이름 미입력 응답은 응답 건수에는 포함하고 고유 인원 계산에서는 제외합니다."
        )

        response_a, response_b, response_c, response_d, response_e = st.columns(5)

        with response_a:

            st.metric(
                "예 응답",
                f"{symptom_responses}건"
            )


        with response_b:

            st.metric(
                "아니오 응답",
                f"{no_symptom_responses}건"
            )


        with response_c:

            st.metric(
                "빈 값/미분류",
                f"{unanswered_responses}건"
            )


        with response_d:

            st.metric(
                "관리대상자 응답",
                f"{management_count}건"
            )


        with response_e:

            st.metric(
                "통증호소자 응답",
                f"{pain_count}건"
            )


        st.divider()


        # =================================================
        # 필터
        # =================================================

        st.subheader(
            "🔎 조사결과 조회"
        )


        filtered_survey = (
            survey_df.copy()
        )


        f1, f2, f3 = (
            st.columns(3)
        )


        with f1:

            if (
                "department"
                in survey_df.columns
            ):

                department_options = [
                    x
                    for x in (
                        survey_df[
                            "department"
                        ]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    if x.strip()
                ]

            else:

                department_options = []


            selected_department = (
                st.selectbox(
                    "작업부서",
                    [
                        "전체"
                    ]
                    + sorted(
                        department_options
                    )
                )
            )


        with f2:

            judgment_options = [
                x
                for x in (
                    judgment_series
                    .unique()
                    .tolist()
                )
                if x.strip()
            ]


            selected_judgment = (
                st.selectbox(
                    "최종판정",
                    [
                        "전체"
                    ]
                    + sorted(
                        judgment_options
                    )
                )
            )


        with f3:

            search_name = (
                st.text_input(
                    "성명 검색"
                )
            )


        if (
            selected_department
            != "전체"
        ):

            filtered_survey = (
                filtered_survey[
                    filtered_survey[
                        "department"
                    ]
                    .astype(str)
                    == selected_department
                ]
            )


        if (
            selected_judgment
            != "전체"
        ):

            filtered_survey = (
                filtered_survey[
                    filtered_survey[
                        "final_judgment"
                    ]
                    .astype(str)
                    == selected_judgment
                ]
            )


        if (
            search_name
            and "name"
            in filtered_survey.columns
        ):

            filtered_survey = (
                filtered_survey[
                    filtered_survey[
                        "name"
                    ]
                    .fillna("")
                    .astype(str)
                    .str.contains(
                        search_name,
                        case=False,
                        na=False
                    )
                ]
            )


        display_survey = (
            format_datetime_column(
                filtered_survey
            )
        )


        preferred_columns = [
            "created_at",
            "name",
            "gender",
            "age",
            "department",
            "sub_department",
            "current_work",
            "symptom_exists",
            "final_judgment"
        ]


        existing_columns = [
            c
            for c in preferred_columns
            if c
            in display_survey.columns
        ]


        st.dataframe(
            display_survey[
                existing_columns
            ],
            hide_index=True,
            width="stretch"
        )


        # =================================================
        # 판정 분포
        # =================================================

        st.subheader(
            "📊 최종판정 분포"
        )


        if (
            "final_judgment"
            in survey_df.columns
        ):

            judgment_chart = (
                survey_df[
                    "final_judgment"
                ]
                .fillna(
                    "미입력"
                )
                .value_counts()
            )


            st.bar_chart(
                judgment_chart
            )


        # =================================================
        # 부서별 현황
        # =================================================

        st.subheader(
            "🏗️ 부서별 조사 현황"
        )


        if (
            "department"
            in survey_df.columns
        ):

            department_summary = (
                survey_df
                .groupby(
                    "department",
                    dropna=False
                )
                .size()
                .reset_index(
                    name="응답자수"
                )
            )


            department_summary[
                "department"
            ] = (
                department_summary[
                    "department"
                ]
                .fillna(
                    "미입력"
                )
            )


            department_summary = (
                department_summary
                .rename(
                    columns={
                        "department":
                            "작업부서"
                    }
                )
            )


            st.dataframe(
                department_summary,
                hide_index=True,
                width="stretch"
            )


        # =================================================
        # 사후관리 대상
        # =================================================

        st.subheader(
            "🚨 사후관리 대상자"
        )


        if (
            "final_judgment"
            in survey_df.columns
        ):

            target_df = (
                survey_df[
                    ~survey_df[
                        "final_judgment"
                    ]
                    .fillna("")
                    .astype(str)
                    .str.contains(
                        "정상",
                        na=False
                    )
                ]
                .copy()
            )


            target_cols = [
                c
                for c in [
                    "name",
                    "department",
                    "sub_department",
                    "current_work",
                    "symptom_exists",
                    "final_judgment"
                ]
                if c
                in target_df.columns
            ]


            if target_df.empty:

                st.success(
                    "현재 사후관리 대상자가 "
                    "없습니다."
                )

            else:

                st.dataframe(
                    target_df[
                        target_cols
                    ],
                    hide_index=True,
                    width="stretch"
                )


        # =================================================
        # 전체 데이터
        # =================================================

        with st.expander(
            "📋 근골격계 전체 응답 데이터"
        ):

            st.dataframe(
                display_survey,
                hide_index=True,
                width="stretch"
            )


# =========================================================
# REBA 자세평가
# =========================================================

with reba_tab:

    st.subheader(
        "🤖 AI REBA 작업자세 평가 현황"
    )


    if reba_df.empty:

        st.info(
            "저장된 REBA 평가결과가 없습니다. "
            "AI 자세·REBA 평가에서 결과를 "
            "저장하면 이곳에 표시됩니다."
        )

    else:

        reba_work = (
            reba_df.copy()
        )


        reba_work[
            "final_reba"
        ] = pd.to_numeric(
            reba_work[
                "final_reba"
            ],
            errors="coerce"
        )


        # =================================================
        # REBA 요약
        # =================================================

        total_reba = len(
            reba_work
        )


        avg_reba = (
            reba_work[
                "final_reba"
            ]
            .mean()
        )


        high_reba = (
            reba_work[
                "final_reba"
            ]
            >= 8
        ).sum()


        very_high_reba = (
            reba_work[
                "final_reba"
            ]
            >= 11
        ).sum()


        r1, r2, r3, r4 = (
            st.columns(4)
        )


        with r1:

            st.metric(
                "총 평가건수",
                f"{total_reba}건"
            )


        with r2:

            st.metric(
                "평균 REBA",
                f"{avg_reba:.1f}점"
            )


        with r3:

            st.metric(
                "높은 위험 이상",
                f"{high_reba}건"
            )


        with r4:

            st.metric(
                "매우 높은 위험",
                f"{very_high_reba}건"
            )


        st.divider()


        # =================================================
        # REBA 필터
        # =================================================

        st.subheader(
            "🔎 REBA 평가 조회"
        )


        filtered_reba = (
            reba_work.copy()
        )


        f1, f2, f3 = (
            st.columns(3)
        )


        with f1:

            department_options = [
                x
                for x in (
                    reba_work[
                        "department"
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
                if x.strip()
            ]


            reba_department = (
                st.selectbox(
                    "공종/부서",
                    [
                        "전체"
                    ]
                    + sorted(
                        department_options
                    ),
                    key=(
                        "reba_department_filter"
                    )
                )
            )


        with f2:

            risk_options = [
                x
                for x in (
                    reba_work[
                        "risk_level"
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
                if x.strip()
            ]


            risk_filter = (
                st.selectbox(
                    "위험수준",
                    [
                        "전체"
                    ]
                    + sorted(
                        risk_options
                    )
                )
            )


        with f3:

            task_search = (
                st.text_input(
                    "작업명 검색"
                )
            )


        if (
            reba_department
            != "전체"
        ):

            filtered_reba = (
                filtered_reba[
                    filtered_reba[
                        "department"
                    ]
                    .astype(str)
                    == reba_department
                ]
            )


        if (
            risk_filter
            != "전체"
        ):

            filtered_reba = (
                filtered_reba[
                    filtered_reba[
                        "risk_level"
                    ]
                    .astype(str)
                    == risk_filter
                ]
            )


        if task_search:

            filtered_reba = (
                filtered_reba[
                    filtered_reba[
                        "task_name"
                    ]
                    .fillna("")
                    .astype(str)
                    .str.contains(
                        task_search,
                        case=False,
                        na=False
                    )
                ]
            )


        display_reba = (
            format_datetime_column(
                filtered_reba
            )
        )


        reba_columns = [
            c
            for c in [
                "created_at",
                "worker",
                "department",
                "task_name",
                "evaluator",
                "final_reba",
                "risk_level",
                "action_level",
                "action_text"
            ]
            if c
            in display_reba.columns
        ]


        st.dataframe(
            display_reba[
                reba_columns
            ],
            hide_index=True,
            width="stretch"
        )


        st.divider()


        # =================================================
        # 위험수준 분포
        # =================================================

        st.subheader(
            "📊 REBA 위험수준 분포"
        )


        risk_counts = (
            reba_work[
                "risk_level"
            ]
            .fillna(
                "미입력"
            )
            .value_counts()
        )


        st.bar_chart(
            risk_counts
        )


        # =================================================
        # 공종별 평균 REBA
        # =================================================

        st.subheader(
            "🏗️ 공종별 평균 REBA"
        )


        department_reba = (
            reba_work
            .groupby(
                "department",
                dropna=False
            )
            .agg(
                평가건수=(
                    "id",
                    "count"
                ),
                평균_REBA=(
                    "final_reba",
                    "mean"
                ),
                최고_REBA=(
                    "final_reba",
                    "max"
                )
            )
            .reset_index()
        )


        department_reba[
            "department"
        ] = (
            department_reba[
                "department"
            ]
            .fillna(
                "미입력"
            )
        )


        department_reba[
            "평균_REBA"
        ] = (
            department_reba[
                "평균_REBA"
            ]
            .round(1)
        )


        department_reba = (
            department_reba
            .rename(
                columns={
                    "department":
                        "공종/부서"
                }
            )
        )


        st.dataframe(
            department_reba,
            hide_index=True,
            width="stretch"
        )


        if (
            not department_reba.empty
        ):

            chart_df = (
                department_reba
                .set_index(
                    "공종/부서"
                )[
                    "평균_REBA"
                ]
            )


            st.bar_chart(
                chart_df
            )


        # =================================================
        # 작업별 평균
        # =================================================

        st.subheader(
            "🛠️ 작업별 REBA 현황"
        )


        task_reba = (
            reba_work
            .groupby(
                "task_name",
                dropna=False
            )
            .agg(
                평가건수=(
                    "id",
                    "count"
                ),
                평균_REBA=(
                    "final_reba",
                    "mean"
                ),
                최고_REBA=(
                    "final_reba",
                    "max"
                )
            )
            .reset_index()
        )


        task_reba[
            "task_name"
        ] = (
            task_reba[
                "task_name"
            ]
            .fillna(
                "미입력"
            )
        )


        task_reba[
            "평균_REBA"
        ] = (
            task_reba[
                "평균_REBA"
            ]
            .round(1)
        )


        task_reba = (
            task_reba
            .rename(
                columns={
                    "task_name":
                        "작업명"
                }
            )
        )


        task_reba = (
            task_reba
            .sort_values(
                "평균_REBA",
                ascending=False
            )
        )


        st.dataframe(
            task_reba,
            hide_index=True,
            width="stretch"
        )


        # =================================================
        # 고위험 작업
        # =================================================

        st.subheader(
            "🚨 고위험 작업 자동목록"
        )


        high_risk_df = (
            reba_work[
                reba_work[
                    "final_reba"
                ]
                >= 8
            ]
            .copy()
        )


        high_risk_df = (
            high_risk_df
            .sort_values(
                "final_reba",
                ascending=False
            )
        )


        high_display = (
            format_datetime_column(
                high_risk_df
            )
        )


        high_columns = [
            c
            for c in [
                "created_at",
                "worker",
                "department",
                "task_name",
                "final_reba",
                "risk_level",
                "action_text"
            ]
            if c
            in high_display.columns
        ]


        if high_risk_df.empty:

            st.success(
                "현재 REBA 8점 이상의 "
                "고위험 평가가 없습니다."
            )

        else:

            st.error(
                f"REBA 8점 이상 평가가 "
                f"{len(high_risk_df)}건 있습니다."
            )

            st.dataframe(
                high_display[
                    high_columns
                ],
                hide_index=True,
                width="stretch"
            )


        # =================================================
        # 개별 평가 상세
        # =================================================

        st.subheader(
            "👤 REBA 평가 상세"
        )


        detail_options = []

        for _, row in (
            reba_work.iterrows()
        ):

            option = (
                f"#{row.get('id', '')} | "
                f"{row.get('worker', '')} | "
                f"{row.get('task_name', '')} | "
                f"REBA {row.get('final_reba', '')}"
            )

            detail_options.append(
                option
            )


        if detail_options:

            selected_detail = (
                st.selectbox(
                    "상세조회할 평가 선택",
                    detail_options
                )
            )


            selected_index = (
                detail_options
                .index(
                    selected_detail
                )
            )


            detail_row = (
                reba_work
                .iloc[
                    selected_index
                ]
            )


            d1, d2, d3, d4 = (
                st.columns(4)
            )


            with d1:

                st.metric(
                    "최종 REBA",
                    detail_row.get(
                        "final_reba",
                        "-"
                    )
                )


            with d2:

                st.metric(
                    "Score A",
                    detail_row.get(
                        "score_a",
                        "-"
                    )
                )


            with d3:

                st.metric(
                    "Score B",
                    detail_row.get(
                        "score_b",
                        "-"
                    )
                )


            with d4:

                st.metric(
                    "Action Level",
                    detail_row.get(
                        "action_level",
                        "-"
                    )
                )


            st.write(
                f"**작업자/대상자:** "
                f"{detail_row.get('worker', '')}"
            )

            st.write(
                f"**공종/부서:** "
                f"{detail_row.get('department', '')}"
            )

            st.write(
                f"**작업명:** "
                f"{detail_row.get('task_name', '')}"
            )

            st.write(
                f"**평가자:** "
                f"{detail_row.get('evaluator', '')}"
            )

            st.write(
                f"**위험수준:** "
                f"{detail_row.get('risk_level', '')}"
            )

            st.write(
                f"**조치사항:** "
                f"{detail_row.get('action_text', '')}"
            )


            # =============================================
            # AI 관절각
            # =============================================

            pose_angles = (
                detail_row.get(
                    "pose_angles",
                    {}
                )
            )


            if isinstance(
                pose_angles,
                dict
            ) and pose_angles:

                st.write(
                    "#### AI 측정 관절각"
                )


                pose_df = (
                    pd.DataFrame(
                        [
                            {
                                "부위":
                                    key,

                                "각도":
                                    (
                                        f"{value}°"
                                        if value
                                        is not None
                                        else "-"
                                    )
                            }

                            for key, value
                            in pose_angles.items()
                        ]
                    )
                )


                st.dataframe(
                    pose_df,
                    hide_index=True,
                    width="stretch"
                )


            # =============================================
            # AI 추천
            # =============================================

            ai_rec = (
                detail_row.get(
                    "ai_recommendation",
                    {}
                )
            )


            if isinstance(
                ai_rec,
                dict
            ) and ai_rec:

                st.write(
                    "#### AI 추천점수"
                )


                ai_table = (
                    pd.DataFrame(
                        [
                            {
                                "항목":
                                    "몸통",

                                "추천점수":
                                    ai_rec.get(
                                        "trunk"
                                    )
                            },

                            {
                                "항목":
                                    "상완",

                                "추천점수":
                                    ai_rec.get(
                                        "upper_arm"
                                    )
                            },

                            {
                                "항목":
                                    "전완",

                                "추천점수":
                                    ai_rec.get(
                                        "lower_arm"
                                    )
                            },

                            {
                                "항목":
                                    "다리",

                                "추천점수":
                                    ai_rec.get(
                                        "legs"
                                    )
                            }
                        ]
                    )
                )


                st.dataframe(
                    ai_table,
                    hide_index=True,
                    width="stretch"
                )


        # =================================================
        # 전체 REBA 원본 데이터
        # =================================================

        with st.expander(
            "📋 전체 REBA 저장 데이터"
        ):

            st.dataframe(
                format_datetime_column(
                    reba_work
                ),
                hide_index=True,
                width="stretch"
            )

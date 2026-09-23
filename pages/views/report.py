import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from io import BytesIO
from datetime import datetime

from supabase import create_client

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from auth import require_admin, logout_button


# =========================================================
# 관리자 인증
# =========================================================

require_admin()

st.title("📄 근골격계 · REBA 통합 결과보고서")
logout_button()

st.write(
    "Supabase DB에 저장된 근골격계 증상조사 및 "
    "REBA 작업자세 평가 결과를 이용하여 "
    "통합 Word 결과보고서를 자동 생성합니다."
)

st.divider()


# =========================================================
# 한글 폰트
# =========================================================

font_candidates = [
    f.name
    for f in fm.fontManager.ttflist
    if "Nanum" in f.name
]

if font_candidates:
    plt.rcParams["font.family"] = font_candidates[0]
else:
    plt.rcParams["font.family"] = "DejaVu Sans"

plt.rcParams["axes.unicode_minus"] = False


# =========================================================
# Supabase 연결
# =========================================================

try:

    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

except Exception as e:

    st.error(
        f"Supabase 연결 오류: {e}"
    )

    st.stop()


# =========================================================
# 근골격계 데이터 불러오기
# =========================================================

try:

    survey_response = (
        supabase
        .table("survey_results")
        .select("*")
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    survey_rows = (
        survey_response.data
        or []
    )

except Exception as e:

    st.error(
        f"근골격계 조사 데이터 조회 오류: {e}"
    )

    survey_rows = []


# =========================================================
# REBA 데이터 불러오기
# =========================================================

try:

    reba_response = (
        supabase
        .table("reba_results")
        .select("*")
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    reba_rows = (
        reba_response.data
        or []
    )

except Exception as e:

    st.error(
        f"REBA 데이터 조회 오류: {e}"
    )

    reba_rows = []


# =========================================================
# 데이터 자체가 하나도 없으면 중지
# =========================================================

if (
    not survey_rows
    and not reba_rows
):

    st.warning(
        "저장된 근골격계 조사 또는 REBA 평가 결과가 없습니다."
    )

    st.stop()


# =========================================================
# 근골격계 DB 데이터 변환
# =========================================================

converted_rows = []

for db_row in survey_rows:

    survey_data = db_row.get(
        "survey_data",
        {}
    )

    if not isinstance(
        survey_data,
        dict
    ):
        survey_data = {}

    row = survey_data.copy()

    row["DB_ID"] = db_row.get(
        "id",
        ""
    )

    row["제출일시"] = db_row.get(
        "created_at",
        ""
    )

    row["성명"] = db_row.get(
        "name",
        row.get(
            "성명",
            ""
        )
    )

    row["성별"] = db_row.get(
        "gender",
        row.get(
            "성별",
            ""
        )
    )

    row["연령"] = db_row.get(
        "age",
        row.get(
            "연령",
            ""
        )
    )

    row["결혼여부"] = db_row.get(
        "marriage",
        row.get(
            "결혼여부",
            ""
        )
    )

    row["작업부서"] = db_row.get(
        "department",
        row.get(
            "작업부서",
            ""
        )
    )

    row["라인/세부부서"] = db_row.get(
        "sub_department",
        row.get(
            "라인/세부부서",
            ""
        )
    )

    row["현재작업"] = db_row.get(
        "current_work",
        row.get(
            "현재작업",
            ""
        )
    )

    row["근골격계증상여부"] = (
        db_row.get(
            "symptom_exists",
            row.get(
                "근골격계증상여부",
                ""
            )
        )
    )

    row["최종판정"] = (
        db_row.get(
            "final_judgment",
            row.get(
                "최종판정",
                ""
            )
        )
    )

    converted_rows.append(
        row
    )


df = pd.DataFrame(
    converted_rows
)


# =========================================================
# REBA DataFrame
# =========================================================

reba_df = pd.DataFrame(
    reba_rows
)


# =========================================================
# 근골격계 기본 컬럼
# =========================================================

body_parts = [
    "목",
    "어깨",
    "팔/팔꿈치",
    "손/손목/손가락",
    "허리",
    "다리/발"
]


for col in [
    "성명",
    "작업부서",
    "현재작업",
    "근골격계증상여부",
    "최종판정"
]:

    if col not in df.columns:
        df[col] = ""


# =========================================================
# 근골격계 기본 통계
# =========================================================

total_count = len(
    df
)


normal_count = (
    df["최종판정"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("정상")
    .sum()
)


manage_count = (
    df["최종판정"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("관리대상자")
    .sum()
)


pain_count = (
    df["최종판정"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("통증호소자")
    .sum()
)


unclassified_count = (
    total_count
    - normal_count
    - manage_count
    - pain_count
)


symptom_count = (
    df["근골격계증상여부"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("예")
    .sum()
)


symptom_rate = (
    symptom_count
    / total_count
    * 100

    if total_count > 0

    else 0
)


# =========================================================
# 신체부위별 판정
# =========================================================

part_summary = []

for part in body_parts:

    col = f"{part}_판정"

    if col in df.columns:

        series = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        normal = (
            series == "정상"
        ).sum()

        manage = (
            series == "관리대상자"
        ).sum()

        pain = (
            series == "통증호소자"
        ).sum()

    else:

        normal = 0
        manage = 0
        pain = 0


    abnormal = (
        manage
        + pain
    )


    abnormal_rate = (
        abnormal
        / total_count
        * 100

        if total_count > 0

        else 0
    )


    part_summary.append(
        {
            "신체부위": part,
            "정상": int(normal),
            "관리대상자": int(manage),
            "통증호소자": int(pain),
            "유소견계": int(abnormal),
            "유소견율(%)": round(
                abnormal_rate,
                1
            )
        }
    )


part_summary_df = pd.DataFrame(
    part_summary
)


# =========================================================
# 부서별 근골격계 판정
# =========================================================

department_summary = []


valid_dept_df = df[
    df["작업부서"].notna()
].copy()


valid_dept_df = valid_dept_df[
    valid_dept_df[
        "작업부서"
    ]
    .astype(str)
    .str.strip()
    != ""
]


for dept in (
    valid_dept_df[
        "작업부서"
    ]
    .unique()
):

    dept_df = (
        valid_dept_df[
            valid_dept_df[
                "작업부서"
            ]
            == dept
        ]
    )


    dept_total = len(
        dept_df
    )


    dept_normal = (
        dept_df[
            "최종판정"
        ]
        == "정상"
    ).sum()


    dept_manage = (
        dept_df[
            "최종판정"
        ]
        == "관리대상자"
    ).sum()


    dept_pain = (
        dept_df[
            "최종판정"
        ]
        == "통증호소자"
    ).sum()


    abnormal = (
        dept_manage
        + dept_pain
    )


    abnormal_rate = (
        abnormal
        / dept_total
        * 100

        if dept_total > 0

        else 0
    )


    department_summary.append(
        {
            "부서": dept,
            "응답자수": int(
                dept_total
            ),
            "정상": int(
                dept_normal
            ),
            "관리대상자": int(
                dept_manage
            ),
            "통증호소자": int(
                dept_pain
            ),
            "유소견계": int(
                abnormal
            ),
            "유소견율(%)": round(
                abnormal_rate,
                1
            )
        }
    )


department_summary_df = (
    pd.DataFrame(
        department_summary
    )
)


if not department_summary_df.empty:

    department_summary_df = (
        department_summary_df
        .sort_values(
            by="유소견율(%)",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )


# =========================================================
# 근골격계 사후관리 대상
# =========================================================

target_df = df[
    df["최종판정"].isin(
        [
            "관리대상자",
            "통증호소자"
        ]
    )
].copy()


# =========================================================
# 근골격계 자동분석
# =========================================================

abnormal_total = (
    manage_count
    + pain_count
)


abnormal_rate = (
    abnormal_total
    / total_count
    * 100

    if total_count > 0

    else 0
)


abnormal_parts_df = (
    part_summary_df[
        part_summary_df[
            "유소견계"
        ]
        > 0
    ]
    .copy()
)


if not abnormal_parts_df.empty:

    abnormal_parts_df = (
        abnormal_parts_df
        .sort_values(
            by="유소견율(%)",
            ascending=False
        )
    )

    top_part_row = (
        abnormal_parts_df
        .iloc[0]
    )

    top_part = (
        top_part_row[
            "신체부위"
        ]
    )

    top_count = int(
        top_part_row[
            "유소견계"
        ]
    )

    top_rate = float(
        top_part_row[
            "유소견율(%)"
        ]
    )


    auto_analysis = (
        f"총 {total_count}명을 대상으로 근골격계 증상조사를 실시한 결과, "
        f"근골격계 증상 경험자는 {symptom_count}명"
        f"({symptom_rate:.1f}%)으로 확인되었습니다. "
        f"최종판정 기준 관리대상자 및 통증호소자는 총 "
        f"{abnormal_total}명({abnormal_rate:.1f}%)이었습니다. "
        f"신체부위별로는 {top_part} 부위의 유소견자가 "
        f"{top_count}명({top_rate:.1f}%)으로 가장 높게 나타났습니다. "
        "해당 결과는 증상조사 응답을 기반으로 한 관리 참고자료이며, "
        "실제 작업자세, 작업강도, 반복성 및 작업환경을 함께 확인하여 "
        "사후관리 및 작업개선 우선순위를 결정할 필요가 있습니다."
    )

else:

    auto_analysis = (
        f"총 {total_count}명을 대상으로 근골격계 증상조사를 실시한 결과, "
        f"근골격계 증상 경험자는 {symptom_count}명"
        f"({symptom_rate:.1f}%)으로 확인되었습니다. "
        "현재 관리대상자 또는 통증호소자로 판정된 신체부위는 "
        "확인되지 않았습니다. "
        "다만 정기적인 증상 확인과 작업조건 점검을 통해 "
        "근골격계질환 예방관리를 지속할 필요가 있습니다."
    )


# =========================================================
# 근골격계 관리계획
# =========================================================

if abnormal_total == 0:

    auto_plan = (
        "1. 정기적인 근골격계 증상조사를 통해 증상 발생 여부를 지속 확인한다.\n"
        "2. 반복작업, 부적절한 작업자세, 중량물 취급 등 근골격계 부담요인을 주기적으로 확인한다.\n"
        "3. 작업 전 스트레칭 및 근골격계질환 예방교육을 지속 실시한다.\n"
        "4. 작업환경 또는 작업방법 변경 시 유해요인 변화를 재확인한다."
    )

else:

    auto_plan = (
        "1. 관리대상자 및 통증호소자를 대상으로 증상 정도와 작업 관련성을 추가 확인한다.\n"
        "2. 유소견율이 높은 신체부위와 관련된 작업자세, 반복성, 힘의 사용 및 작업시간을 우선 점검한다.\n"
        "3. 필요 시 작업방법 개선, 작업대 높이 조정, 보조도구 적용 및 작업순환 등을 검토한다.\n"
        "4. 증상 지속 또는 악화 근로자는 보건상담 및 의료기관 진료 등 적절한 사후관리를 실시한다.\n"
        "5. 작업개선 실시 후 증상 변화 및 개선 효과를 재평가한다."
    )


# =========================================================
# REBA 기본 통계
# =========================================================

if not reba_df.empty:

    if (
        "final_reba"
        not in reba_df.columns
    ):
        reba_df[
            "final_reba"
        ] = 0


    reba_df[
        "final_reba"
    ] = pd.to_numeric(
        reba_df[
            "final_reba"
        ],
        errors="coerce"
    )


    total_reba = len(
        reba_df
    )


    average_reba = (
        reba_df[
            "final_reba"
        ]
        .mean()
    )


    max_reba = (
        reba_df[
            "final_reba"
        ]
        .max()
    )


    high_reba_count = (
        reba_df[
            "final_reba"
        ]
        >= 8
    ).sum()


    very_high_reba_count = (
        reba_df[
            "final_reba"
        ]
        >= 11
    ).sum()


else:

    total_reba = 0
    average_reba = 0
    max_reba = 0
    high_reba_count = 0
    very_high_reba_count = 0


# =========================================================
# REBA 위험수준 분포
# =========================================================

if (
    not reba_df.empty
    and "risk_level"
    in reba_df.columns
):

    risk_summary_df = (
        reba_df[
            "risk_level"
        ]
        .fillna(
            "미분류"
        )
        .value_counts()
        .rename_axis(
            "위험수준"
        )
        .reset_index(
            name="평가건수"
        )
    )

else:

    risk_summary_df = (
        pd.DataFrame(
            columns=[
                "위험수준",
                "평가건수"
            ]
        )
    )


# =========================================================
# REBA 공종별 통계
# =========================================================

if (
    not reba_df.empty
    and "department"
    in reba_df.columns
):

    reba_department_df = (
        reba_df
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


    reba_department_df[
        "department"
    ] = (
        reba_department_df[
            "department"
        ]
        .fillna(
            "미입력"
        )
    )


    reba_department_df[
        "평균_REBA"
    ] = (
        reba_department_df[
            "평균_REBA"
        ]
        .round(1)
    )


    reba_department_df = (
        reba_department_df
        .rename(
            columns={
                "department":
                    "공종/부서"
            }
        )
    )


    reba_department_df = (
        reba_department_df
        .sort_values(
            "평균_REBA",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

else:

    reba_department_df = (
        pd.DataFrame(
            columns=[
                "공종/부서",
                "평가건수",
                "평균_REBA",
                "최고_REBA"
            ]
        )
    )


# =========================================================
# REBA 작업별 통계
# =========================================================

if (
    not reba_df.empty
    and "task_name"
    in reba_df.columns
):

    reba_task_df = (
        reba_df
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


    reba_task_df[
        "task_name"
    ] = (
        reba_task_df[
            "task_name"
        ]
        .fillna(
            "미입력"
        )
    )


    reba_task_df[
        "평균_REBA"
    ] = (
        reba_task_df[
            "평균_REBA"
        ]
        .round(1)
    )


    reba_task_df = (
        reba_task_df
        .rename(
            columns={
                "task_name":
                    "작업명"
            }
        )
    )


    reba_task_df = (
        reba_task_df
        .sort_values(
            "평균_REBA",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

else:

    reba_task_df = (
        pd.DataFrame(
            columns=[
                "작업명",
                "평가건수",
                "평균_REBA",
                "최고_REBA"
            ]
        )
    )


# =========================================================
# REBA 고위험 작업
# =========================================================

if not reba_df.empty:

    high_risk_reba_df = (
        reba_df[
            reba_df[
                "final_reba"
            ]
            >= 8
        ]
        .copy()
    )


    high_risk_reba_df = (
        high_risk_reba_df
        .sort_values(
            "final_reba",
            ascending=False
        )
    )

else:

    high_risk_reba_df = (
        pd.DataFrame()
    )


# =========================================================
# REBA 자동분석
# =========================================================

if total_reba == 0:

    auto_reba_analysis = (
        "현재 저장된 REBA 작업자세 평가 결과가 없습니다."
    )


    auto_reba_plan = (
        "1. 근골격계 부담작업 또는 부적절한 작업자세가 확인되는 작업을 대상으로 REBA 평가를 실시한다.\n"
        "2. 평가 시 실제 작업조건과 반복성, 하중 및 작업시간을 함께 확인한다.\n"
        "3. 작업방법 또는 설비 변경 후 재평가를 실시한다."
    )

else:

    if not reba_task_df.empty:

        top_task = (
            reba_task_df
            .iloc[0]
        )

        top_task_name = (
            top_task[
                "작업명"
            ]
        )

        top_task_avg = (
            top_task[
                "평균_REBA"
            ]
        )

    else:

        top_task_name = "-"
        top_task_avg = 0


    auto_reba_analysis = (
        f"총 {total_reba}건의 REBA 작업자세 평가를 실시한 결과, "
        f"평균 REBA 점수는 {average_reba:.1f}점이며 "
        f"최고점수는 {max_reba:.0f}점으로 확인되었습니다. "
        f"REBA 8점 이상의 높은 위험 이상 평가건수는 "
        f"{high_reba_count}건이며, 이 중 11점 이상의 매우 높은 위험은 "
        f"{very_high_reba_count}건입니다. "
        f"작업별 평균 REBA가 가장 높은 작업은 "
        f"'{top_task_name}'으로 평균 {top_task_avg:.1f}점입니다. "
        "REBA 결과는 특정 작업자세에 대한 평가결과이므로 "
        "실제 작업빈도, 지속시간, 중량물 취급, 반복성 및 "
        "작업환경을 함께 검토하여 개선 우선순위를 결정할 필요가 있습니다."
    )


    if high_reba_count > 0:

        auto_reba_plan = (
            "1. REBA 8점 이상의 작업은 작업방법, 작업높이, 작업거리 및 작업자세를 우선적으로 점검한다.\n"
            "2. 가능한 경우 작업공구, 보조설비, 작업대 또는 장비를 활용하여 불필요한 굴곡 및 과도한 상지 동작을 감소시킨다.\n"
            "3. 반복작업은 작업순환, 휴식시간 조정 및 작업분담을 검토한다.\n"
            "4. 중량물 취급 시 중량 감소, 운반보조기구 및 2인 취급 등 개선대책을 검토한다.\n"
            "5. 개선조치 후 동일 작업을 재평가하여 REBA 위험도 감소 여부를 확인한다."
        )

    else:

        auto_reba_plan = (
            "1. 현재 작업자세 수준을 유지하되 정기적인 자세평가를 실시한다.\n"
            "2. 작업방법이나 설비 변경 시 REBA 재평가를 실시한다.\n"
            "3. 반복성, 하중 및 작업시간 증가 여부를 지속 확인한다.\n"
            "4. 작업자 의견 및 근골격계 증상조사 결과와 연계하여 예방관리를 실시한다."
        )


# =========================================================
# 웹 화면
# =========================================================

st.subheader(
    "통합 현황"
)


c1, c2, c3, c4 = st.columns(
    4
)


with c1:

    st.metric(
        "근골격계 조사",
        f"{total_count}명"
    )


with c2:

    st.metric(
        "근골격계 유소견",
        f"{abnormal_total}명"
    )


with c3:

    st.metric(
        "REBA 평가",
        f"{total_reba}건"
    )


with c4:

    st.metric(
        "REBA 8점 이상",
        f"{high_reba_count}건"
    )


st.divider()


# =========================================================
# 보고서 기본정보
# =========================================================

st.subheader(
    "보고서 기본정보"
)


report_title = st.text_input(
    "보고서 제목",
    value=(
        "근골격계 증상조사 및 "
        "REBA 작업자세 평가 결과보고서"
    )
)


company_name = st.text_input(
    "사업장명",
    placeholder="예: OO 건설현장"
)


survey_period = st.text_input(
    "조사 및 평가기간",
    placeholder=(
        "예: 2026.09.01 ~ 2026.09.30"
    )
)


writer = st.text_input(
    "작성자",
    placeholder="예: 보건관리자 홍길동"
)


st.divider()


# =========================================================
# 화면 탭
# =========================================================

survey_tab, reba_tab = st.tabs(
    [
        "🩺 근골격계 증상조사",
        "🤖 REBA 작업자세 평가"
    ]
)


# =========================================================
# 근골격계 탭
# =========================================================

with survey_tab:

    st.subheader(
        "신체부위별 판정 현황"
    )


    st.dataframe(
        part_summary_df,
        width="stretch",
        hide_index=True
    )


    st.subheader(
        "근골격계 종합분석"
    )


    edited_analysis = st.text_area(
        "보고서 근골격계 종합분석",
        value=auto_analysis,
        height=200
    )


    st.subheader(
        "근골격계 향후 관리계획"
    )


    edited_plan = st.text_area(
        "보고서 근골격계 관리계획",
        value=auto_plan,
        height=220
    )


# =========================================================
# REBA 탭
# =========================================================

with reba_tab:

    if total_reba == 0:

        st.info(
            "저장된 REBA 평가결과가 없습니다."
        )

    else:

        r1, r2, r3, r4 = st.columns(
            4
        )


        with r1:

            st.metric(
                "총 평가건수",
                f"{total_reba}건"
            )


        with r2:

            st.metric(
                "평균 REBA",
                f"{average_reba:.1f}점"
            )


        with r3:

            st.metric(
                "최고 REBA",
                f"{max_reba:.0f}점"
            )


        with r4:

            st.metric(
                "높은 위험 이상",
                f"{high_reba_count}건"
            )


        st.subheader(
            "공종별 REBA 현황"
        )


        st.dataframe(
            reba_department_df,
            hide_index=True,
            width="stretch"
        )


        st.subheader(
            "작업별 REBA 현황"
        )


        st.dataframe(
            reba_task_df,
            hide_index=True,
            width="stretch"
        )


        st.subheader(
            "고위험 작업"
        )


        if high_risk_reba_df.empty:

            st.success(
                "REBA 8점 이상 평가가 없습니다."
            )

        else:

            high_cols = [
                c
                for c in [
                    "worker",
                    "department",
                    "task_name",
                    "final_reba",
                    "risk_level",
                    "action_text"
                ]
                if c
                in high_risk_reba_df.columns
            ]


            st.dataframe(
                high_risk_reba_df[
                    high_cols
                ],
                hide_index=True,
                width="stretch"
            )


    st.subheader(
        "REBA 종합분석"
    )


    edited_reba_analysis = (
        st.text_area(
            "보고서 REBA 종합분석",
            value=auto_reba_analysis,
            height=200
        )
    )


    st.subheader(
        "REBA 향후 관리계획"
    )


    edited_reba_plan = (
        st.text_area(
            "보고서 REBA 관리계획",
            value=auto_reba_plan,
            height=220
        )
    )


st.divider()


# =========================================================
# 그래프 - 신체부위
# =========================================================

def create_bodypart_chart():

    chart_data = (
        part_summary_df.copy()
    )


    fig, ax = plt.subplots(
        figsize=(
            8,
            4.2
        )
    )


    bars = ax.bar(
        chart_data[
            "신체부위"
        ],
        chart_data[
            "유소견율(%)"
        ]
    )


    ax.set_title(
        "신체부위별 유소견율"
    )


    ax.set_ylabel(
        "유소견율(%)"
    )


    ax.set_xlabel(
        "신체부위"
    )


    max_value = (
        chart_data[
            "유소견율(%)"
        ]
        .max()
        if not chart_data.empty
        else 0
    )


    ax.set_ylim(
        0,
        max(
            20,
            max_value + 10
        )
    )


    for bar, value in zip(
        bars,
        chart_data[
            "유소견율(%)"
        ]
    ):

        ax.text(
            bar.get_x()
            + bar.get_width()
            / 2,

            bar.get_height()
            + 0.5,

            f"{value:.1f}%",

            ha="center",
            va="bottom"
        )


    plt.xticks(
        rotation=15
    )


    plt.tight_layout()


    output = BytesIO()


    plt.savefig(
        output,
        format="png",
        dpi=160,
        bbox_inches="tight"
    )


    plt.close(
        fig
    )


    output.seek(0)


    return output


# =========================================================
# 그래프 - 근골격계 부서
# =========================================================

def create_department_chart():

    if department_summary_df.empty:
        return None


    chart_df = (
        department_summary_df[
            [
                "부서",
                "정상",
                "관리대상자",
                "통증호소자"
            ]
        ]
        .set_index(
            "부서"
        )
    )


    fig, ax = plt.subplots(
        figsize=(
            8,
            4.2
        )
    )


    chart_df.plot(
        kind="bar",
        ax=ax
    )


    ax.set_title(
        "부서별 판정 분포"
    )


    ax.set_ylabel(
        "인원"
    )


    ax.set_xlabel(
        "부서"
    )


    plt.xticks(
        rotation=20,
        ha="right"
    )


    plt.tight_layout()


    output = BytesIO()


    plt.savefig(
        output,
        format="png",
        dpi=160,
        bbox_inches="tight"
    )


    plt.close(
        fig
    )


    output.seek(0)


    return output


# =========================================================
# 그래프 - REBA 위험수준
# =========================================================

def create_reba_risk_chart():

    if risk_summary_df.empty:
        return None


    fig, ax = plt.subplots(
        figsize=(
            7.5,
            4.2
        )
    )


    bars = ax.bar(
        risk_summary_df[
            "위험수준"
        ],
        risk_summary_df[
            "평가건수"
        ]
    )


    ax.set_title(
        "REBA 위험수준별 평가건수"
    )


    ax.set_ylabel(
        "평가건수"
    )


    ax.set_xlabel(
        "위험수준"
    )


    for bar, value in zip(
        bars,
        risk_summary_df[
            "평가건수"
        ]
    ):

        ax.text(
            bar.get_x()
            + bar.get_width()
            / 2,

            bar.get_height()
            + 0.05,

            str(
                int(value)
            ),

            ha="center",
            va="bottom"
        )


    plt.tight_layout()


    output = BytesIO()


    plt.savefig(
        output,
        format="png",
        dpi=160,
        bbox_inches="tight"
    )


    plt.close(
        fig
    )


    output.seek(0)


    return output


# =========================================================
# 그래프 - 공종별 평균 REBA
# =========================================================

def create_reba_department_chart():

    if reba_department_df.empty:
        return None


    chart_df = (
        reba_department_df
        .set_index(
            "공종/부서"
        )[
            "평균_REBA"
        ]
    )


    fig, ax = plt.subplots(
        figsize=(
            8,
            4.2
        )
    )


    bars = ax.bar(
        chart_df.index,
        chart_df.values
    )


    ax.set_title(
        "공종별 평균 REBA 점수"
    )


    ax.set_ylabel(
        "평균 REBA"
    )


    ax.set_xlabel(
        "공종/부서"
    )


    ax.set_ylim(
        0,
        max(
            15,
            chart_df.max()
            + 2
        )
    )


    for bar, value in zip(
        bars,
        chart_df.values
    ):

        ax.text(
            bar.get_x()
            + bar.get_width()
            / 2,

            bar.get_height()
            + 0.15,

            f"{value:.1f}",

            ha="center",
            va="bottom"
        )


    plt.xticks(
        rotation=20,
        ha="right"
    )


    plt.tight_layout()


    output = BytesIO()


    plt.savefig(
        output,
        format="png",
        dpi=160,
        bbox_inches="tight"
    )


    plt.close(
        fig
    )


    output.seek(0)


    return output


# =========================================================
# Word 유틸
# =========================================================

def set_cell_text(
    cell,
    text,
    bold=False
):

    cell.text = ""

    p = cell.paragraphs[0]

    run = p.add_run(
        str(text)
    )

    run.bold = bold

    run.font.name = (
        "Malgun Gothic"
    )

    run._element.rPr.rFonts.set(
        qn(
            "w:eastAsia"
        ),
        "맑은 고딕"
    )

    run.font.size = Pt(
        9
    )


def add_section_heading(
    document,
    text
):

    p = (
        document.add_paragraph()
    )

    run = p.add_run(
        text
    )

    run.bold = True

    run.font.size = Pt(
        14
    )

    run.font.name = (
        "Malgun Gothic"
    )

    run._element.rPr.rFonts.set(
        qn(
            "w:eastAsia"
        ),
        "맑은 고딕"
    )

    return p


def add_body_paragraph(
    document,
    text
):

    p = document.add_paragraph()

    run = p.add_run(
        str(text)
    )

    run.font.name = (
        "Malgun Gothic"
    )

    run.font.size = Pt(
        10
    )

    run._element.rPr.rFonts.set(
        qn(
            "w:eastAsia"
        ),
        "맑은 고딕"
    )

    return p


# =========================================================
# Word 생성
# =========================================================

def create_word_report():

    document = Document()


    section = (
        document.sections[0]
    )


    section.top_margin = (
        Inches(0.65)
    )

    section.bottom_margin = (
        Inches(0.65)
    )

    section.left_margin = (
        Inches(0.7)
    )

    section.right_margin = (
        Inches(0.7)
    )


    normal_style = (
        document.styles[
            "Normal"
        ]
    )


    normal_style.font.name = (
        "Malgun Gothic"
    )

    normal_style.font.size = (
        Pt(10)
    )


    normal_style._element.rPr.rFonts.set(
        qn(
            "w:eastAsia"
        ),
        "맑은 고딕"
    )


    # =====================================================
    # 제목
    # =====================================================

    p = (
        document.add_paragraph()
    )


    p.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )


    run = p.add_run(
        report_title
    )


    run.bold = True

    run.font.size = Pt(
        21
    )

    run.font.name = (
        "Malgun Gothic"
    )


    run._element.rPr.rFonts.set(
        qn(
            "w:eastAsia"
        ),
        "맑은 고딕"
    )


    document.add_paragraph("")


    # =====================================================
    # 1. 조사 및 평가 개요
    # =====================================================

    add_section_heading(
        document,
        "1. 조사 및 평가 개요"
    )


    overview_table = (
        document.add_table(
            rows=7,
            cols=2
        )
    )


    overview_table.style = (
        "Table Grid"
    )


    overview_data = [
        [
            "사업장명",
            company_name
        ],
        [
            "조사·평가기간",
            survey_period
        ],
        [
            "작성자",
            writer
        ],
        [
            "근골격계 조사인원",
            f"{total_count}명"
        ],
        [
            "증상 경험자",
            (
                f"{symptom_count}명 "
                f"({symptom_rate:.1f}%)"
            )
        ],
        [
            "REBA 평가건수",
            f"{total_reba}건"
        ],
        [
            "보고서 작성일",
            datetime.now().strftime(
                "%Y-%m-%d"
            )
        ]
    ]


    for i, item in enumerate(
        overview_data
    ):

        set_cell_text(
            overview_table.cell(
                i,
                0
            ),
            item[0],
            bold=True
        )

        set_cell_text(
            overview_table.cell(
                i,
                1
            ),
            item[1]
        )


    document.add_paragraph("")


    # =====================================================
    # 2. 근골격계 조사 결과 요약
    # =====================================================

    add_section_heading(
        document,
        "2. 근골격계 조사 결과 요약"
    )


    summary_table = (
        document.add_table(
            rows=2,
            cols=5
        )
    )


    summary_table.style = (
        "Table Grid"
    )


    headers = [
        "총 조사자",
        "정상",
        "관리대상자",
        "통증호소자",
        "미분류"
    ]


    values = [
        total_count,
        normal_count,
        manage_count,
        pain_count,
        unclassified_count
    ]


    for i, header in enumerate(
        headers
    ):

        set_cell_text(
            summary_table.cell(
                0,
                i
            ),
            header,
            bold=True
        )

        set_cell_text(
            summary_table.cell(
                1,
                i
            ),
            f"{values[i]}명"
        )


    document.add_paragraph("")


    # =====================================================
    # 3. 신체부위별 판정
    # =====================================================

    add_section_heading(
        document,
        "3. 신체부위별 판정 현황"
    )


    part_table = (
        document.add_table(
            rows=1,
            cols=6
        )
    )


    part_table.style = (
        "Table Grid"
    )


    part_headers = [
        "신체부위",
        "정상",
        "관리대상자",
        "통증호소자",
        "유소견계",
        "유소견율(%)"
    ]


    for i, header in enumerate(
        part_headers
    ):

        set_cell_text(
            part_table.cell(
                0,
                i
            ),
            header,
            bold=True
        )


    for _, row in (
        part_summary_df
        .iterrows()
    ):

        cells = (
            part_table
            .add_row()
            .cells
        )


        values = [
            row[
                "신체부위"
            ],
            row[
                "정상"
            ],
            row[
                "관리대상자"
            ],
            row[
                "통증호소자"
            ],
            row[
                "유소견계"
            ],
            (
                f'{row["유소견율(%)"]}%'
            )
        ]


        for i, value in enumerate(
            values
        ):

            set_cell_text(
                cells[i],
                value
            )


    document.add_paragraph("")


    if total_count > 0:

        body_chart = (
            create_bodypart_chart()
        )


        document.add_picture(
            body_chart,
            width=Inches(
                6.4
            )
        )


        document.paragraphs[
            -1
        ].alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )


    document.add_paragraph("")


    # =====================================================
    # 4. 부서별 판정
    # =====================================================

    add_section_heading(
        document,
        "4. 부서별 근골격계 판정 현황"
    )


    if department_summary_df.empty:

        add_body_paragraph(
            document,
            "부서별 분석 가능한 데이터가 없습니다."
        )

    else:

        dept_table = (
            document.add_table(
                rows=1,
                cols=6
            )
        )


        dept_table.style = (
            "Table Grid"
        )


        dept_headers = [
            "부서",
            "응답자수",
            "정상",
            "관리대상자",
            "통증호소자",
            "유소견율(%)"
        ]


        for i, header in enumerate(
            dept_headers
        ):

            set_cell_text(
                dept_table.cell(
                    0,
                    i
                ),
                header,
                bold=True
            )


        for _, row in (
            department_summary_df
            .iterrows()
        ):

            cells = (
                dept_table
                .add_row()
                .cells
            )


            values = [
                row[
                    "부서"
                ],
                row[
                    "응답자수"
                ],
                row[
                    "정상"
                ],
                row[
                    "관리대상자"
                ],
                row[
                    "통증호소자"
                ],
                (
                    f'{row["유소견율(%)"]}%'
                )
            ]


            for i, value in enumerate(
                values
            ):

                set_cell_text(
                    cells[i],
                    value
                )


        document.add_paragraph("")


        dept_chart = (
            create_department_chart()
        )


        if dept_chart is not None:

            document.add_picture(
                dept_chart,
                width=Inches(
                    6.4
                )
            )


            document.paragraphs[
                -1
            ].alignment = (
                WD_ALIGN_PARAGRAPH.CENTER
            )


    document.add_paragraph("")


    # =====================================================
    # 5. 사후관리 대상자
    # =====================================================

    add_section_heading(
        document,
        "5. 근골격계 사후관리 대상자"
    )


    if target_df.empty:

        add_body_paragraph(
            document,
            "현재 관리대상자 또는 통증호소자로 분류된 근로자는 없습니다."
        )

    else:

        target_table = (
            document.add_table(
                rows=1,
                cols=5
            )
        )


        target_table.style = (
            "Table Grid"
        )


        headers = [
            "성명",
            "부서",
            "현재작업",
            "증상부위",
            "최종판정"
        ]


        for i, header in enumerate(
            headers
        ):

            set_cell_text(
                target_table.cell(
                    0,
                    i
                ),
                header,
                bold=True
            )


        for _, row in (
            target_df
            .iterrows()
        ):

            abnormal_parts = []


            for part in body_parts:

                judgment = (
                    row.get(
                        f"{part}_판정",
                        ""
                    )
                )


                if judgment in [
                    "관리대상자",
                    "통증호소자"
                ]:

                    abnormal_parts.append(
                        f"{part}({judgment})"
                    )


            cells = (
                target_table
                .add_row()
                .cells
            )


            values = [
                row.get(
                    "성명",
                    ""
                ),
                row.get(
                    "작업부서",
                    ""
                ),
                row.get(
                    "현재작업",
                    ""
                ),
                ", ".join(
                    abnormal_parts
                ),
                row.get(
                    "최종판정",
                    ""
                )
            ]


            for i, value in enumerate(
                values
            ):

                set_cell_text(
                    cells[i],
                    value
                )


    document.add_paragraph("")


    # =====================================================
    # 6. 근골격계 종합분석
    # =====================================================

    add_section_heading(
        document,
        "6. 근골격계 종합 분석"
    )


    add_body_paragraph(
        document,
        edited_analysis
    )


    document.add_paragraph("")


    # =====================================================
    # 7. 근골격계 관리계획
    # =====================================================

    add_section_heading(
        document,
        "7. 근골격계 향후 관리계획"
    )


    for line in (
        edited_plan
        .split("\n")
    ):

        if line.strip():

            add_body_paragraph(
                document,
                line.strip()
            )


    document.add_paragraph("")


    # =====================================================
    # 8. REBA 평가 결과 요약
    # =====================================================

    add_section_heading(
        document,
        "8. REBA 작업자세 평가 결과 요약"
    )


    if total_reba == 0:

        add_body_paragraph(
            document,
            "현재 저장된 REBA 작업자세 평가 결과가 없습니다."
        )

    else:

        reba_summary_table = (
            document.add_table(
                rows=2,
                cols=5
            )
        )


        reba_summary_table.style = (
            "Table Grid"
        )


        reba_headers = [
            "총 평가건수",
            "평균 REBA",
            "최고 REBA",
            "8점 이상",
            "11점 이상"
        ]


        reba_values = [
            f"{total_reba}건",
            f"{average_reba:.1f}점",
            f"{max_reba:.0f}점",
            f"{high_reba_count}건",
            f"{very_high_reba_count}건"
        ]


        for i, header in enumerate(
            reba_headers
        ):

            set_cell_text(
                reba_summary_table.cell(
                    0,
                    i
                ),
                header,
                bold=True
            )

            set_cell_text(
                reba_summary_table.cell(
                    1,
                    i
                ),
                reba_values[i]
            )


        document.add_paragraph("")


        risk_chart = (
            create_reba_risk_chart()
        )


        if risk_chart is not None:

            document.add_picture(
                risk_chart,
                width=Inches(
                    6.0
                )
            )


            document.paragraphs[
                -1
            ].alignment = (
                WD_ALIGN_PARAGRAPH.CENTER
            )


    document.add_paragraph("")


    # =====================================================
    # 9. 공종별 REBA
    # =====================================================

    add_section_heading(
        document,
        "9. 공종별 REBA 평가 현황"
    )


    if reba_department_df.empty:

        add_body_paragraph(
            document,
            "공종별 REBA 분석 가능한 데이터가 없습니다."
        )

    else:

        table = (
            document.add_table(
                rows=1,
                cols=4
            )
        )


        table.style = (
            "Table Grid"
        )


        headers = [
            "공종/부서",
            "평가건수",
            "평균 REBA",
            "최고 REBA"
        ]


        for i, header in enumerate(
            headers
        ):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                header,
                bold=True
            )


        for _, row in (
            reba_department_df
            .iterrows()
        ):

            cells = (
                table
                .add_row()
                .cells
            )


            values = [
                row[
                    "공종/부서"
                ],
                row[
                    "평가건수"
                ],
                row[
                    "평균_REBA"
                ],
                row[
                    "최고_REBA"
                ]
            ]


            for i, value in enumerate(
                values
            ):

                set_cell_text(
                    cells[i],
                    value
                )


        document.add_paragraph("")


        chart = (
            create_reba_department_chart()
        )


        if chart is not None:

            document.add_picture(
                chart,
                width=Inches(
                    6.4
                )
            )


            document.paragraphs[
                -1
            ].alignment = (
                WD_ALIGN_PARAGRAPH.CENTER
            )


    document.add_paragraph("")


    # =====================================================
    # 10. 작업별 REBA
    # =====================================================

    add_section_heading(
        document,
        "10. 작업별 REBA 평가 현황"
    )


    if reba_task_df.empty:

        add_body_paragraph(
            document,
            "작업별 REBA 분석 가능한 데이터가 없습니다."
        )

    else:

        table = (
            document.add_table(
                rows=1,
                cols=4
            )
        )


        table.style = (
            "Table Grid"
        )


        headers = [
            "작업명",
            "평가건수",
            "평균 REBA",
            "최고 REBA"
        ]


        for i, header in enumerate(
            headers
        ):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                header,
                bold=True
            )


        for _, row in (
            reba_task_df
            .iterrows()
        ):

            cells = (
                table
                .add_row()
                .cells
            )


            values = [
                row[
                    "작업명"
                ],
                row[
                    "평가건수"
                ],
                row[
                    "평균_REBA"
                ],
                row[
                    "최고_REBA"
                ]
            ]


            for i, value in enumerate(
                values
            ):

                set_cell_text(
                    cells[i],
                    value
                )


    document.add_paragraph("")


    # =====================================================
    # 11. REBA 고위험 작업
    # =====================================================

    add_section_heading(
        document,
        "11. REBA 고위험 작업 관리대상"
    )


    if high_risk_reba_df.empty:

        add_body_paragraph(
            document,
            "현재 REBA 8점 이상의 높은 위험 작업은 없습니다."
        )

    else:

        table = (
            document.add_table(
                rows=1,
                cols=6
            )
        )


        table.style = (
            "Table Grid"
        )


        headers = [
            "대상자",
            "공종/부서",
            "작업명",
            "REBA",
            "위험수준",
            "조치방향"
        ]


        for i, header in enumerate(
            headers
        ):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                header,
                bold=True
            )


        for _, row in (
            high_risk_reba_df
            .iterrows()
        ):

            cells = (
                table
                .add_row()
                .cells
            )


            values = [
                row.get(
                    "worker",
                    ""
                ),
                row.get(
                    "department",
                    ""
                ),
                row.get(
                    "task_name",
                    ""
                ),
                row.get(
                    "final_reba",
                    ""
                ),
                row.get(
                    "risk_level",
                    ""
                ),
                row.get(
                    "action_text",
                    ""
                )
            ]


            for i, value in enumerate(
                values
            ):

                set_cell_text(
                    cells[i],
                    value
                )


    document.add_paragraph("")


    # =====================================================
    # 12. REBA 종합분석
    # =====================================================

    add_section_heading(
        document,
        "12. REBA 종합 분석"
    )


    add_body_paragraph(
        document,
        edited_reba_analysis
    )


    document.add_paragraph("")


    # =====================================================
    # 13. REBA 관리계획
    # =====================================================

    add_section_heading(
        document,
        "13. REBA 향후 관리계획"
    )


    for line in (
        edited_reba_plan
        .split("\n")
    ):

        if line.strip():

            add_body_paragraph(
                document,
                line.strip()
            )


    document.add_paragraph("")


    # =====================================================
    # 14. 종합 결론
    # =====================================================

    add_section_heading(
        document,
        "14. 종합 결론"
    )


    if (
        abnormal_total > 0
        and high_reba_count > 0
    ):

        final_summary = (
            "근골격계 증상조사에서 관리대상자 또는 통증호소자가 확인되었으며, "
            "REBA 평가에서도 높은 위험 이상의 작업자세가 확인되었습니다. "
            "근로자 증상과 작업자세 평가결과를 연계하여 "
            "유소견자가 수행하는 작업 및 고위험 작업을 우선적으로 점검하고, "
            "작업방법·설비·보조도구·작업순환 등의 개선을 실시한 후 "
            "증상 및 REBA 위험도를 재평가할 필요가 있습니다."
        )

    elif abnormal_total > 0:

        final_summary = (
            "근골격계 증상조사에서 관리대상자 또는 통증호소자가 확인되었습니다. "
            "해당 근로자의 작업내용과 작업자세를 추가 확인하고, "
            "증상부위와 관련된 근골격계 부담요인을 중심으로 "
            "사후관리 및 작업개선을 실시할 필요가 있습니다."
        )

    elif high_reba_count > 0:

        final_summary = (
            "현재 근골격계 증상조사상 주요 유소견은 제한적이나, "
            "REBA 평가에서 높은 위험 이상의 작업자세가 확인되었습니다. "
            "증상 발생 이전 단계에서 작업방법 및 작업자세 개선을 실시하고 "
            "개선 후 재평가를 통해 예방적 관리를 강화할 필요가 있습니다."
        )

    else:

        final_summary = (
            "근골격계 증상조사 및 REBA 작업자세 평가 결과를 종합할 때 "
            "현재 즉각적인 고위험 관리대상은 제한적인 것으로 확인됩니다. "
            "다만 작업조건 변화 및 반복작업 증가 등에 따라 위험도가 달라질 수 있으므로 "
            "정기적인 증상조사와 작업자세 평가를 지속 실시할 필요가 있습니다."
        )


    add_body_paragraph(
        document,
        final_summary
    )


    # =====================================================
    # 파일 저장
    # =====================================================

    output = BytesIO()


    document.save(
        output
    )


    output.seek(0)


    return output


# =========================================================
# 보고서 생성
# =========================================================

st.subheader(
    "통합 보고서 생성"
)


st.write(
    "현재 Supabase DB에 저장된 근골격계 증상조사 및 "
    "REBA 작업자세 평가 결과를 기준으로 "
    "제출용 Word 보고서를 생성합니다."
)


try:

    word_file = (
        create_word_report()
    )


    st.download_button(
        label=(
            "📄 근골격계 · REBA "
            "통합 Word 보고서 다운로드"
        ),
        data=word_file,
        file_name=(
            "근골격계_REBA_통합_결과보고서.docx"
        ),
        mime=(
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        ),
        width="stretch"
    )


except Exception as e:

    st.error(
        f"보고서 생성 중 오류가 발생했습니다: {e}"
    )

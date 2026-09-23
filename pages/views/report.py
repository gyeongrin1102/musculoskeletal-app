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

st.title("📄 근골격계 · REBA · 개선효과 통합 결과보고서")

logout_button()

st.write(
    "근골격계 증상조사, REBA 작업자세 평가 및 "
    "개선 전·후 비교결과를 통합하여 Word 보고서를 생성합니다."
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
# Supabase
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
# 근골격계 조사 조회
# =========================================================

try:

    survey_response = (
        supabase
        .table("survey_results")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    survey_rows = (
        survey_response.data
        or []
    )

except Exception as e:

    st.error(
        f"근골격계 조사 조회 오류: {e}"
    )

    survey_rows = []


# =========================================================
# REBA 결과 조회
# =========================================================

try:

    reba_response = (
        supabase
        .table("reba_results")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    reba_rows = (
        reba_response.data
        or []
    )

except Exception as e:

    st.error(
        f"REBA 결과 조회 오류: {e}"
    )

    reba_rows = []


# =========================================================
# 개선 전후 결과 조회
# =========================================================

try:

    improvement_response = (
        supabase
        .table("reba_improvements")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    improvement_rows = (
        improvement_response.data
        or []
    )

except Exception as e:

    st.error(
        f"개선 전·후 결과 조회 오류: {e}"
    )

    improvement_rows = []


if (
    not survey_rows
    and not reba_rows
    and not improvement_rows
):

    st.warning(
        "현재 저장된 결과 데이터가 없습니다."
    )

    st.stop()


# =========================================================
# 근골격계 DB 변환
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
        row.get("성명", "")
    )

    row["성별"] = db_row.get(
        "gender",
        row.get("성별", "")
    )

    row["연령"] = db_row.get(
        "age",
        row.get("연령", "")
    )

    row["결혼여부"] = db_row.get(
        "marriage",
        row.get("결혼여부", "")
    )

    row["작업부서"] = db_row.get(
        "department",
        row.get("작업부서", "")
    )

    row["라인/세부부서"] = db_row.get(
        "sub_department",
        row.get("라인/세부부서", "")
    )

    row["현재작업"] = db_row.get(
        "current_work",
        row.get("현재작업", "")
    )

    row["근골격계증상여부"] = db_row.get(
        "symptom_exists",
        row.get(
            "근골격계증상여부",
            ""
        )
    )

    row["최종판정"] = db_row.get(
        "final_judgment",
        row.get(
            "최종판정",
            ""
        )
    )

    converted_rows.append(
        row
    )


df = pd.DataFrame(
    converted_rows
)

reba_df = pd.DataFrame(
    reba_rows
)

improvement_df = pd.DataFrame(
    improvement_rows
)


# =========================================================
# 기본 컬럼
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
# 근골격계 통계
# =========================================================

total_count = len(df)


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
            series
            == "관리대상자"
        ).sum()

        pain = (
            series
            == "통증호소자"
        ).sum()

    else:

        normal = 0
        manage = 0
        pain = 0


    abnormal = (
        manage
        + pain
    )


    rate = (
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
                rate,
                1
            )
        }
    )


part_summary_df = pd.DataFrame(
    part_summary
)


# =========================================================
# 부서별 근골격계
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


    dept_abnormal = (
        dept_manage
        + dept_pain
    )


    dept_rate = (
        dept_abnormal
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
                dept_abnormal
            ),
            "유소견율(%)": round(
                dept_rate,
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
            "유소견율(%)",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )


# =========================================================
# 사후관리 대상
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
# 근골격계 자동 분석
# =========================================================

abnormal_parts_df = part_summary_df[
    part_summary_df[
        "유소견계"
    ]
    > 0
].copy()


if not abnormal_parts_df.empty:

    abnormal_parts_df = (
        abnormal_parts_df
        .sort_values(
            "유소견율(%)",
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
        f"증상 경험자는 {symptom_count}명"
        f"({symptom_rate:.1f}%)으로 확인되었습니다. "
        f"관리대상자 및 통증호소자는 총 {abnormal_total}명"
        f"({abnormal_rate:.1f}%)입니다. "
        f"신체부위별로는 {top_part} 부위의 유소견자가 "
        f"{top_count}명({top_rate:.1f}%)으로 가장 높았습니다. "
        "증상 결과와 실제 작업자세 및 작업강도를 함께 확인하여 "
        "사후관리와 작업개선 우선순위를 결정할 필요가 있습니다."
    )

else:

    auto_analysis = (
        f"총 {total_count}명을 대상으로 근골격계 증상조사를 실시한 결과, "
        f"증상 경험자는 {symptom_count}명"
        f"({symptom_rate:.1f}%)으로 확인되었습니다. "
        "현재 주요 유소견 부위는 확인되지 않았으나 "
        "정기적인 증상 확인과 작업조건 점검을 지속할 필요가 있습니다."
    )


if abnormal_total == 0:

    auto_plan = (
        "1. 정기적인 근골격계 증상조사를 지속 실시한다.\n"
        "2. 반복작업 및 부적절한 작업자세를 주기적으로 점검한다.\n"
        "3. 작업 전 스트레칭과 예방교육을 실시한다.\n"
        "4. 작업조건 변경 시 근골격계 부담요인을 재확인한다."
    )

else:

    auto_plan = (
        "1. 관리대상자 및 통증호소자의 증상과 작업 관련성을 추가 확인한다.\n"
        "2. 유소견 부위와 관련된 작업자세와 반복성을 우선 점검한다.\n"
        "3. 작업방법, 작업높이, 보조도구 및 작업순환 개선을 검토한다.\n"
        "4. 증상 지속 근로자는 상담 및 의료기관 진료 등 사후관리를 실시한다.\n"
        "5. 개선조치 후 증상 변화를 재평가한다."
    )


# =========================================================
# REBA 통계
# =========================================================

if not reba_df.empty:

    if "final_reba" not in reba_df.columns:
        reba_df["final_reba"] = 0


    reba_df["final_reba"] = (
        pd.to_numeric(
            reba_df[
                "final_reba"
            ],
            errors="coerce"
        )
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
# REBA 위험수준
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

    risk_summary_df = pd.DataFrame(
        columns=[
            "위험수준",
            "평가건수"
        ]
    )


# =========================================================
# REBA 공종별
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
# REBA 작업별
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
# REBA 고위험
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

else:

    high_risk_reba_df = (
        pd.DataFrame()
    )


# =========================================================
# REBA 분석
# =========================================================

if total_reba == 0:

    auto_reba_analysis = (
        "현재 저장된 REBA 평가결과가 없습니다."
    )


    auto_reba_plan = (
        "1. 근골격계 부담작업을 대상으로 REBA 평가를 실시한다.\n"
        "2. 작업자세, 하중, 반복성 및 지속시간을 함께 확인한다.\n"
        "3. 작업방법 변경 후 재평가를 실시한다."
    )

else:

    auto_reba_analysis = (
        f"총 {total_reba}건의 REBA 작업자세 평가를 실시한 결과, "
        f"평균 REBA는 {average_reba:.1f}점이며 "
        f"최고점수는 {max_reba:.0f}점입니다. "
        f"REBA 8점 이상 높은 위험 평가건수는 "
        f"{high_reba_count}건이며, "
        f"11점 이상 매우 높은 위험은 "
        f"{very_high_reba_count}건입니다. "
        "고위험 작업은 작업방법, 작업높이, 작업거리 및 "
        "보조도구 적용 가능성을 우선 검토할 필요가 있습니다."
    )


    auto_reba_plan = (
        "1. REBA 8점 이상의 작업을 우선 개선대상으로 관리한다.\n"
        "2. 작업높이, 작업거리 및 부적절한 작업자세를 개선한다.\n"
        "3. 보조도구 및 장비 활용을 검토한다.\n"
        "4. 반복작업은 작업순환 및 휴식시간 조정을 검토한다.\n"
        "5. 개선 후 동일 작업을 다시 REBA 평가한다."
    )


# =========================================================
# 개선 전후 통계
# =========================================================

if not improvement_df.empty:

    for col in [
        "before_reba",
        "after_reba",
        "score_reduction"
    ]:

        if col in improvement_df.columns:

            improvement_df[col] = (
                pd.to_numeric(
                    improvement_df[col],
                    errors="coerce"
                )
            )


    total_improvement = len(
        improvement_df
    )


    avg_reduction = (
        improvement_df[
            "score_reduction"
        ]
        .mean()
        if "score_reduction"
        in improvement_df.columns
        else 0
    )


    improved_count = (
        (
            improvement_df[
                "score_reduction"
            ]
            > 0
        )
        .sum()
        if "score_reduction"
        in improvement_df.columns
        else 0
    )


    unchanged_count = (
        (
            improvement_df[
                "score_reduction"
            ]
            == 0
        )
        .sum()
        if "score_reduction"
        in improvement_df.columns
        else 0
    )


    worsened_count = (
        (
            improvement_df[
                "score_reduction"
            ]
            < 0
        )
        .sum()
        if "score_reduction"
        in improvement_df.columns
        else 0
    )


    remaining_high_count = (
        (
            improvement_df[
                "after_reba"
            ]
            >= 8
        )
        .sum()
        if "after_reba"
        in improvement_df.columns
        else 0
    )

else:

    total_improvement = 0
    avg_reduction = 0
    improved_count = 0
    unchanged_count = 0
    worsened_count = 0
    remaining_high_count = 0


# =========================================================
# 개선 자동분석
# =========================================================

if total_improvement == 0:

    auto_improvement_analysis = (
        "현재 저장된 REBA 개선 전·후 비교결과가 없습니다."
    )


    auto_improvement_plan = (
        "1. 고위험 REBA 작업에 대해 개선조치를 실시한다.\n"
        "2. 동일 작업을 개선 후 재평가한다.\n"
        "3. 점수 감소 여부와 위험수준 변화를 확인한다."
    )

else:

    improvement_rate = (
        improved_count
        / total_improvement
        * 100
        if total_improvement > 0
        else 0
    )


    auto_improvement_analysis = (
        f"총 {total_improvement}건의 개선 전·후 비교 결과, "
        f"{improved_count}건({improvement_rate:.1f}%)에서 "
        f"REBA 점수가 감소하였습니다. "
        f"평균 점수 감소폭은 {avg_reduction:.1f}점입니다. "
        f"변화가 없는 평가는 {unchanged_count}건, "
        f"오히려 점수가 증가한 평가는 {worsened_count}건입니다. "
        f"개선 후에도 REBA 8점 이상인 작업은 "
        f"{remaining_high_count}건으로 확인되었습니다."
    )


    auto_improvement_plan = (
        "1. 개선 후에도 REBA 8점 이상인 작업은 추가 개선조치를 실시한다.\n"
        "2. 점수 감소 효과가 확인된 개선방법은 유사 공종에 확대 적용을 검토한다.\n"
        "3. 점수가 감소하지 않은 작업은 작업조건과 개선대책을 재검토한다.\n"
        "4. 개선조치 후 일정기간 경과 후 작업자 의견과 증상 변화를 추가 확인한다.\n"
        "5. 개선 전·후 평가결과를 지속적으로 기록하여 예방활동의 효과를 관리한다."
    )


# =========================================================
# 화면 요약
# =========================================================

st.subheader(
    "통합 현황"
)


c1, c2, c3, c4, c5 = (
    st.columns(5)
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


with c5:

    st.metric(
        "개선 전후 비교",
        f"{total_improvement}건"
    )


st.divider()


# =========================================================
# 보고서 정보
# =========================================================

st.subheader(
    "보고서 기본정보"
)


report_title = st.text_input(
    "보고서 제목",
    value=(
        "근골격계 증상조사 · "
        "REBA 작업자세 평가 및 "
        "개선효과 결과보고서"
    )
)


company_name = st.text_input(
    "사업장명",
    placeholder="예: OO 건설현장"
)


survey_period = st.text_input(
    "조사 및 평가기간",
    placeholder=(
        "예: 2026.09.01 ~ "
        "2026.09.30"
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

tab1, tab2, tab3 = (
    st.tabs(
        [
            "🩺 근골격계",
            "🤖 REBA 평가",
            "🔄 개선 전·후"
        ]
    )
)


with tab1:

    st.subheader(
        "신체부위별 판정"
    )


    st.dataframe(
        part_summary_df,
        hide_index=True,
        width="stretch"
    )


    edited_analysis = st.text_area(
        "근골격계 종합분석",
        value=auto_analysis,
        height=200
    )


    edited_plan = st.text_area(
        "근골격계 관리계획",
        value=auto_plan,
        height=220
    )


with tab2:

    if total_reba > 0:

        r1, r2, r3, r4 = (
            st.columns(4)
        )


        with r1:

            st.metric(
                "총 평가",
                f"{total_reba}건"
            )


        with r2:

            st.metric(
                "평균 REBA",
                f"{average_reba:.1f}"
            )


        with r3:

            st.metric(
                "최고 REBA",
                f"{max_reba:.0f}"
            )


        with r4:

            st.metric(
                "8점 이상",
                f"{high_reba_count}건"
            )


        st.dataframe(
            reba_task_df,
            hide_index=True,
            width="stretch"
        )


    edited_reba_analysis = (
        st.text_area(
            "REBA 종합분석",
            value=auto_reba_analysis,
            height=200
        )
    )


    edited_reba_plan = (
        st.text_area(
            "REBA 관리계획",
            value=auto_reba_plan,
            height=220
        )
    )


with tab3:

    if total_improvement > 0:

        i1, i2, i3, i4 = (
            st.columns(4)
        )


        with i1:

            st.metric(
                "비교건수",
                f"{total_improvement}건"
            )


        with i2:

            st.metric(
                "평균 감소",
                f"{avg_reduction:.1f}점"
            )


        with i3:

            st.metric(
                "개선 성공",
                f"{improved_count}건"
            )


        with i4:

            st.metric(
                "개선 후 8점 이상",
                f"{remaining_high_count}건"
            )


        display_cols = [
            c
            for c in [
                "department",
                "task_name",
                "before_reba",
                "after_reba",
                "score_reduction",
                "improvement_action"
            ]
            if c
            in improvement_df.columns
        ]


        st.dataframe(
            improvement_df[
                display_cols
            ],
            hide_index=True,
            width="stretch"
        )


    else:

        st.info(
            "저장된 개선 전·후 비교결과가 없습니다."
        )


    edited_improvement_analysis = (
        st.text_area(
            "개선효과 종합분석",
            value=auto_improvement_analysis,
            height=200
        )
    )


    edited_improvement_plan = (
        st.text_area(
            "추가 관리계획",
            value=auto_improvement_plan,
            height=220
        )
    )


st.divider()


# =========================================================
# 차트
# =========================================================

def create_bodypart_chart():

    fig, ax = plt.subplots(
        figsize=(8, 4.2)
    )


    bars = ax.bar(
        part_summary_df[
            "신체부위"
        ],
        part_summary_df[
            "유소견율(%)"
        ]
    )


    ax.set_title(
        "신체부위별 유소견율"
    )

    ax.set_ylabel(
        "유소견율(%)"
    )


    for bar, value in zip(
        bars,
        part_summary_df[
            "유소견율(%)"
        ]
    ):

        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            bar.get_height()
            + 0.3,
            f"{value:.1f}%",
            ha="center"
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


def create_improvement_chart():

    if improvement_df.empty:
        return None


    chart_df = (
        improvement_df[
            [
                "before_reba",
                "after_reba"
            ]
        ]
        .mean()
    )


    fig, ax = plt.subplots(
        figsize=(6, 4)
    )


    bars = ax.bar(
        [
            "개선 전",
            "개선 후"
        ],
        [
            chart_df[
                "before_reba"
            ],
            chart_df[
                "after_reba"
            ]
        ]
    )


    ax.set_title(
        "REBA 개선 전·후 평균점수"
    )


    ax.set_ylabel(
        "REBA 점수"
    )


    ax.set_ylim(
        0,
        15
    )


    for bar in bars:

        value = (
            bar.get_height()
        )

        ax.text(
            bar.get_x()
            + bar.get_width()
            / 2,
            value + 0.2,
            f"{value:.1f}",
            ha="center"
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

    run.font.size = Pt(
        9
    )

    run._element.rPr.rFonts.set(
        qn("w:eastAsia"),
        "맑은 고딕"
    )


def add_heading(
    document,
    text
):

    p = document.add_paragraph()

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
        qn("w:eastAsia"),
        "맑은 고딕"
    )


def add_text(
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
        qn("w:eastAsia"),
        "맑은 고딕"
    )


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

    normal_style.font.size = Pt(
        10
    )

    normal_style._element.rPr.rFonts.set(
        qn("w:eastAsia"),
        "맑은 고딕"
    )


    # =====================================================
    # 제목
    # =====================================================

    p = document.add_paragraph()

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
        qn("w:eastAsia"),
        "맑은 고딕"
    )


    document.add_paragraph("")


    # =====================================================
    # 1. 개요
    # =====================================================

    add_heading(
        document,
        "1. 조사 및 평가 개요"
    )


    table = document.add_table(
        rows=8,
        cols=2
    )

    table.style = (
        "Table Grid"
    )


    overview = [
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
            "근골격계 유소견",
            f"{abnormal_total}명"
        ],
        [
            "REBA 평가건수",
            f"{total_reba}건"
        ],
        [
            "개선 전·후 비교",
            f"{total_improvement}건"
        ],
        [
            "보고서 작성일",
            datetime.now().strftime(
                "%Y-%m-%d"
            )
        ]
    ]


    for i, item in enumerate(
        overview
    ):

        set_cell_text(
            table.cell(
                i,
                0
            ),
            item[0],
            True
        )

        set_cell_text(
            table.cell(
                i,
                1
            ),
            item[1]
        )


    document.add_paragraph("")


    # =====================================================
    # 2. 근골격계 결과
    # =====================================================

    add_heading(
        document,
        "2. 근골격계 조사 결과 요약"
    )


    table = document.add_table(
        rows=2,
        cols=5
    )

    table.style = (
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


    for i in range(5):

        set_cell_text(
            table.cell(
                0,
                i
            ),
            headers[i],
            True
        )

        set_cell_text(
            table.cell(
                1,
                i
            ),
            f"{values[i]}명"
        )


    document.add_paragraph("")


    # =====================================================
    # 3. 신체부위
    # =====================================================

    add_heading(
        document,
        "3. 신체부위별 판정 현황"
    )


    table = document.add_table(
        rows=1,
        cols=6
    )

    table.style = (
        "Table Grid"
    )


    headers = [
        "신체부위",
        "정상",
        "관리대상자",
        "통증호소자",
        "유소견계",
        "유소견율"
    ]


    for i, h in enumerate(
        headers
    ):

        set_cell_text(
            table.cell(
                0,
                i
            ),
            h,
            True
        )


    for _, row in (
        part_summary_df
        .iterrows()
    ):

        cells = (
            table.add_row().cells
        )


        vals = [
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
            f'{row["유소견율(%)"]}%'
        ]


        for i, value in enumerate(
            vals
        ):

            set_cell_text(
                cells[i],
                value
            )


    if total_count > 0:

        document.add_paragraph("")

        chart = (
            create_bodypart_chart()
        )

        document.add_picture(
            chart,
            width=Inches(6.3)
        )


    document.add_paragraph("")


    # =====================================================
    # 4. 부서별 근골격계
    # =====================================================

    add_heading(
        document,
        "4. 부서별 근골격계 판정 현황"
    )


    if department_summary_df.empty:

        add_text(
            document,
            "부서별 분석 가능한 데이터가 없습니다."
        )

    else:

        table = document.add_table(
            rows=1,
            cols=6
        )

        table.style = (
            "Table Grid"
        )


        headers = [
            "부서",
            "응답자수",
            "정상",
            "관리대상자",
            "통증호소자",
            "유소견율"
        ]


        for i, h in enumerate(
            headers
        ):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                h,
                True
            )


        for _, row in (
            department_summary_df
            .iterrows()
        ):

            cells = (
                table.add_row().cells
            )


            vals = [
                row["부서"],
                row["응답자수"],
                row["정상"],
                row["관리대상자"],
                row["통증호소자"],
                f'{row["유소견율(%)"]}%'
            ]


            for i, value in enumerate(
                vals
            ):

                set_cell_text(
                    cells[i],
                    value
                )


    document.add_paragraph("")


    # =====================================================
    # 5. 사후관리
    # =====================================================

    add_heading(
        document,
        "5. 근골격계 사후관리 대상자"
    )


    if target_df.empty:

        add_text(
            document,
            "현재 관리대상자 또는 통증호소자는 없습니다."
        )

    else:

        table = document.add_table(
            rows=1,
            cols=4
        )

        table.style = (
            "Table Grid"
        )


        headers = [
            "성명",
            "부서",
            "현재작업",
            "최종판정"
        ]


        for i, h in enumerate(
            headers
        ):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                h,
                True
            )


        for _, row in (
            target_df.iterrows()
        ):

            cells = (
                table.add_row().cells
            )


            vals = [
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
                row.get(
                    "최종판정",
                    ""
                )
            ]


            for i, value in enumerate(
                vals
            ):

                set_cell_text(
                    cells[i],
                    value
                )


    document.add_paragraph("")


    # =====================================================
    # 6~7 근골격계 분석
    # =====================================================

    add_heading(
        document,
        "6. 근골격계 종합 분석"
    )

    add_text(
        document,
        edited_analysis
    )


    add_heading(
        document,
        "7. 근골격계 향후 관리계획"
    )


    for line in (
        edited_plan.split("\n")
    ):

        if line.strip():

            add_text(
                document,
                line.strip()
            )


    document.add_paragraph("")


    # =====================================================
    # 8. REBA 요약
    # =====================================================

    add_heading(
        document,
        "8. REBA 작업자세 평가 결과 요약"
    )


    if total_reba == 0:

        add_text(
            document,
            "저장된 REBA 평가결과가 없습니다."
        )

    else:

        table = document.add_table(
            rows=2,
            cols=5
        )

        table.style = (
            "Table Grid"
        )


        headers = [
            "총 평가",
            "평균 REBA",
            "최고 REBA",
            "8점 이상",
            "11점 이상"
        ]


        values = [
            f"{total_reba}건",
            f"{average_reba:.1f}점",
            f"{max_reba:.0f}점",
            f"{high_reba_count}건",
            f"{very_high_reba_count}건"
        ]


        for i in range(5):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                headers[i],
                True
            )

            set_cell_text(
                table.cell(
                    1,
                    i
                ),
                values[i]
            )


    document.add_paragraph("")


    # =====================================================
    # 9. 공종별 REBA
    # =====================================================

    add_heading(
        document,
        "9. 공종별 REBA 평가 현황"
    )


    if reba_department_df.empty:

        add_text(
            document,
            "공종별 REBA 데이터가 없습니다."
        )

    else:

        table = document.add_table(
            rows=1,
            cols=4
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


        for i, h in enumerate(
            headers
        ):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                h,
                True
            )


        for _, row in (
            reba_department_df
            .iterrows()
        ):

            cells = (
                table.add_row().cells
            )


            vals = [
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
                vals
            ):

                set_cell_text(
                    cells[i],
                    value
                )


    document.add_paragraph("")


    # =====================================================
    # 10. 작업별 REBA
    # =====================================================

    add_heading(
        document,
        "10. 작업별 REBA 평가 현황"
    )


    if reba_task_df.empty:

        add_text(
            document,
            "작업별 REBA 데이터가 없습니다."
        )

    else:

        table = document.add_table(
            rows=1,
            cols=4
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


        for i, h in enumerate(
            headers
        ):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                h,
                True
            )


        for _, row in (
            reba_task_df
            .iterrows()
        ):

            cells = (
                table.add_row().cells
            )


            vals = [
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
                vals
            ):

                set_cell_text(
                    cells[i],
                    value
                )


    document.add_paragraph("")


    # =====================================================
    # 11. 고위험 REBA
    # =====================================================

    add_heading(
        document,
        "11. REBA 고위험 작업 관리대상"
    )


    if high_risk_reba_df.empty:

        add_text(
            document,
            "현재 REBA 8점 이상의 작업은 없습니다."
        )

    else:

        table = document.add_table(
            rows=1,
            cols=5
        )

        table.style = (
            "Table Grid"
        )


        headers = [
            "대상자",
            "공종",
            "작업명",
            "REBA",
            "위험수준"
        ]


        for i, h in enumerate(
            headers
        ):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                h,
                True
            )


        for _, row in (
            high_risk_reba_df
            .iterrows()
        ):

            cells = (
                table.add_row().cells
            )


            vals = [
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
                )
            ]


            for i, value in enumerate(
                vals
            ):

                set_cell_text(
                    cells[i],
                    value
                )


    document.add_paragraph("")


    # =====================================================
    # 12~13 REBA 분석
    # =====================================================

    add_heading(
        document,
        "12. REBA 종합 분석"
    )

    add_text(
        document,
        edited_reba_analysis
    )


    add_heading(
        document,
        "13. REBA 향후 관리계획"
    )


    for line in (
        edited_reba_plan
        .split("\n")
    ):

        if line.strip():

            add_text(
                document,
                line.strip()
            )


    document.add_paragraph("")


    # =====================================================
    # 14. 개선 전·후 요약
    # =====================================================

    add_heading(
        document,
        "14. REBA 개선 전·후 비교 결과"
    )


    if total_improvement == 0:

        add_text(
            document,
            "저장된 개선 전·후 비교 결과가 없습니다."
        )

    else:

        table = document.add_table(
            rows=2,
            cols=5
        )

        table.style = (
            "Table Grid"
        )


        headers = [
            "비교건수",
            "개선건수",
            "평균 감소점수",
            "변화없음",
            "개선 후 8점 이상"
        ]


        values = [
            f"{total_improvement}건",
            f"{improved_count}건",
            f"{avg_reduction:.1f}점",
            f"{unchanged_count}건",
            f"{remaining_high_count}건"
        ]


        for i in range(5):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                headers[i],
                True
            )

            set_cell_text(
                table.cell(
                    1,
                    i
                ),
                values[i]
            )


        document.add_paragraph("")


        chart = (
            create_improvement_chart()
        )


        if chart is not None:

            document.add_picture(
                chart,
                width=Inches(5.5)
            )


    document.add_paragraph("")


    # =====================================================
    # 15. 개선 세부내역
    # =====================================================

    add_heading(
        document,
        "15. REBA 개선조치 세부내역"
    )


    if improvement_df.empty:

        add_text(
            document,
            "개선조치 내역이 없습니다."
        )

    else:

        table = document.add_table(
            rows=1,
            cols=6
        )

        table.style = (
            "Table Grid"
        )


        headers = [
            "공종",
            "작업명",
            "개선 전",
            "개선 후",
            "감소점수",
            "개선조치"
        ]


        for i, h in enumerate(
            headers
        ):

            set_cell_text(
                table.cell(
                    0,
                    i
                ),
                h,
                True
            )


        for _, row in (
            improvement_df
            .iterrows()
        ):

            cells = (
                table.add_row().cells
            )


            vals = [
                row.get(
                    "department",
                    ""
                ),
                row.get(
                    "task_name",
                    ""
                ),
                row.get(
                    "before_reba",
                    ""
                ),
                row.get(
                    "after_reba",
                    ""
                ),
                row.get(
                    "score_reduction",
                    ""
                ),
                row.get(
                    "improvement_action",
                    ""
                )
            ]


            for i, value in enumerate(
                vals
            ):

                set_cell_text(
                    cells[i],
                    value
                )


    document.add_paragraph("")


    # =====================================================
    # 16. 개선효과 분석
    # =====================================================

    add_heading(
        document,
        "16. 개선효과 종합 분석"
    )


    add_text(
        document,
        edited_improvement_analysis
    )


    add_heading(
        document,
        "17. 추가 개선 및 관리계획"
    )


    for line in (
        edited_improvement_plan
        .split("\n")
    ):

        if line.strip():

            add_text(
                document,
                line.strip()
            )


    document.add_paragraph("")


    # =====================================================
    # 18. 최종 결론
    # =====================================================

    add_heading(
        document,
        "18. 종합 결론"
    )


    if (
        abnormal_total > 0
        and high_reba_count > 0
    ):

        final_summary = (
            "근골격계 증상조사에서 관리대상자 또는 통증호소자가 확인되었고, "
            "REBA 평가에서도 높은 위험 작업이 확인되었습니다. "
            "근로자 증상과 고위험 작업을 연계하여 개선 우선순위를 결정하고, "
            "개선조치 후 REBA 재평가와 증상 변화를 지속 확인할 필요가 있습니다."
        )

    elif high_reba_count > 0:

        final_summary = (
            "REBA 평가에서 높은 위험 작업이 확인되었습니다. "
            "증상 발생 이전에 작업방법 및 작업자세를 개선하고 "
            "개선 후 위험도 감소 여부를 재평가할 필요가 있습니다."
        )

    elif abnormal_total > 0:

        final_summary = (
            "근골격계 증상조사에서 사후관리 대상자가 확인되었습니다. "
            "관련 작업자세 및 부담요인을 추가 확인하여 "
            "예방관리와 작업개선을 실시할 필요가 있습니다."
        )

    else:

        final_summary = (
            "현재 조사 및 작업자세 평가에서 즉각적인 고위험 대상은 "
            "제한적인 것으로 확인됩니다. "
            "정기적인 증상조사와 작업자세 평가를 지속 실시하고 "
            "작업조건 변경 시 재평가할 필요가 있습니다."
        )


    if (
        total_improvement > 0
        and avg_reduction > 0
    ):

        final_summary += (
            f" 또한 실시된 개선 전·후 비교에서는 "
            f"평균 REBA 점수가 {avg_reduction:.1f}점 감소하여 "
            "일정 수준의 개선효과가 확인되었습니다. "
            "효과가 확인된 개선방법은 유사 작업에 확대 적용하는 방안을 검토합니다."
        )


    add_text(
        document,
        final_summary
    )


    # =====================================================
    # 저장
    # =====================================================

    output = BytesIO()

    document.save(
        output
    )

    output.seek(0)

    return output


# =========================================================
# 다운로드
# =========================================================

st.subheader(
    "통합 보고서 생성"
)


st.write(
    "현재 DB에 저장된 증상조사, REBA 평가 및 "
    "개선 전·후 비교결과를 Word 보고서로 생성합니다."
)


try:

    word_file = (
        create_word_report()
    )


    st.download_button(
        label=(
            "📄 최종 통합 Word "
            "결과보고서 다운로드"
        ),
        data=word_file,
        file_name=(
            "근골격계_REBA_개선효과_통합결과보고서.docx"
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

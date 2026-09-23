import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from io import BytesIO
from datetime import datetime

from supabase import create_client

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


# =========================================================
# 페이지 설정
# =========================================================

st.set_page_config(
    page_title="근골격계 증상조사 결과보고서",
    page_icon="📄",
    layout="wide"
)

st.title("📄 근골격계 증상조사 결과보고서")

st.write(
    "Supabase 데이터베이스에 저장된 증상조사 결과를 이용하여 "
    "Word 결과보고서를 자동으로 생성합니다."
)

st.divider()


# =========================================================
# 한글 그래프 설정
# =========================================================

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# =========================================================
# Supabase 연결
# =========================================================

try:

    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]

    supabase = create_client(
        supabase_url,
        supabase_key
    )

except Exception as e:

    st.error(
        f"Supabase 연결정보를 불러오지 못했습니다: {e}"
    )

    st.stop()


# =========================================================
# DB 데이터 불러오기
# =========================================================

try:

    response = (
        supabase
        .table("survey_results")
        .select("*")
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    db_rows = response.data

except Exception as e:

    st.error(
        f"데이터베이스 조회 중 오류가 발생했습니다: {e}"
    )

    st.stop()


if not db_rows:

    st.warning(
        "아직 저장된 조사 결과가 없습니다."
    )

    st.stop()


# =========================================================
# Supabase 데이터 → 기존 설문 형식으로 변환
# =========================================================

converted_rows = []


for db_row in db_rows:

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
        row.get(
            "제출일시",
            ""
        )
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


# =========================================================
# 기본 설정
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
# 기본 통계
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


classified_count = (
    normal_count
    + manage_count
    + pain_count
)


unclassified_count = (
    total_count
    - classified_count
)


# =========================================================
# 조사 현황
# =========================================================

st.subheader("조사 현황")


col1, col2, col3, col4, col5 = st.columns(5)


with col1:

    st.metric(
        "총 조사자",
        f"{total_count}명"
    )


with col2:

    st.metric(
        "정상",
        f"{normal_count}명"
    )


with col3:

    st.metric(
        "관리대상자",
        f"{manage_count}명"
    )


with col4:

    st.metric(
        "통증호소자",
        f"{pain_count}명"
    )


with col5:

    st.metric(
        "미분류",
        f"{unclassified_count}명"
    )


st.divider()


# =========================================================
# 보고서 기본정보
# =========================================================

st.subheader("보고서 기본정보")


report_title = st.text_input(
    "보고서 제목",
    value="근골격계 증상조사 결과보고서"
)


company_name = st.text_input(
    "사업장명",
    placeholder="예: OO사업장"
)


survey_period = st.text_input(
    "조사기간",
    placeholder="예: 2026.09.01 ~ 2026.09.30"
)


writer = st.text_input(
    "작성자",
    placeholder="예: 보건관리자 홍길동"
)


st.divider()


# =========================================================
# 신체부위별 판정 현황
# =========================================================

part_summary = []


for part in body_parts:

    column_name = (
        f"{part}_판정"
    )


    if column_name in df.columns:

        series = (
            df[column_name]
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


    part_summary.append({
        "신체부위": part,
        "정상": int(normal),
        "관리대상자": int(manage),
        "통증호소자": int(pain),
        "유소견계": int(abnormal),
        "유소견율(%)": round(
            abnormal_rate,
            1
        )
    })


part_summary_df = pd.DataFrame(
    part_summary
)


st.subheader(
    "신체부위별 판정 현황"
)


st.dataframe(
    part_summary_df,
    width="stretch",
    hide_index=True
)


# =========================================================
# 자동 종합의견
# =========================================================

abnormal_total = (
    manage_count
    + pain_count
)


overall_abnormal_rate = (
    abnormal_total
    / total_count
    * 100
    if total_count > 0
    else 0
)


abnormal_parts_df = part_summary_df[
    part_summary_df[
        "유소견계"
    ] > 0
].copy()


if len(
    abnormal_parts_df
) == 0:

    auto_opinion = (
        f"총 {total_count}명을 대상으로 근골격계 증상조사를 실시한 결과, "
        "현재 관리대상자 또는 통증호소자로 분류된 신체부위는 "
        "확인되지 않았습니다. "
        "본 결과는 증상조사 응답을 기반으로 한 참고자료이며, "
        "실제 작업조건과 작업자세를 함께 확인하여 관리할 필요가 있습니다."
    )


else:

    abnormal_parts_df = (
        abnormal_parts_df
        .sort_values(
            by="유소견율(%)",
            ascending=False
        )
    )


    top_row = (
        abnormal_parts_df
        .iloc[0]
    )


    top_part = (
        top_row[
            "신체부위"
        ]
    )


    top_rate = (
        top_row[
            "유소견율(%)"
        ]
    )


    top_count = (
        top_row[
            "유소견계"
        ]
    )


    auto_opinion = (
        f"총 {total_count}명을 대상으로 근골격계 증상조사를 실시한 결과, "
        f"관리대상자 및 통증호소자는 총 {abnormal_total}명으로 "
        f"전체 조사자의 {overall_abnormal_rate:.1f}%에 해당합니다. "
        f"신체부위별로는 {top_part} 부위의 유소견자가 "
        f"{int(top_count)}명({top_rate:.1f}%)으로 가장 높게 나타났습니다. "
        "해당 결과는 증상조사 결과를 기반으로 한 관리 참고자료이며, "
        "실제 작업조건과 작업자세를 함께 확인하여 "
        "사후관리 우선순위를 검토할 필요가 있습니다."
    )


st.subheader(
    "자동 종합의견"
)


edited_opinion = st.text_area(
    "보고서에 들어갈 종합의견",
    value=auto_opinion,
    height=180
)


st.divider()


# =========================================================
# 그래프 1
# 신체부위별 유소견율
# =========================================================

def create_bodypart_chart():

    chart_data = (
        part_summary_df.copy()
    )


    fig, ax = plt.subplots(
        figsize=(8, 4.5)
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
    )


    ax.set_ylim(
        0,
        max(
            100,
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
            + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{value:.1f}%",
            ha="center",
            va="bottom"
        )


    plt.xticks(
        rotation=20
    )


    plt.tight_layout()


    image_stream = BytesIO()


    plt.savefig(
        image_stream,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )


    plt.close(
        fig
    )


    image_stream.seek(
        0
    )


    return image_stream


# =========================================================
# 그래프 2
# 부서별 판정 분포
# =========================================================

def create_department_chart():

    chart_source = df.copy()


    chart_source = chart_source[
        chart_source[
            "작업부서"
        ]
        .notna()
    ]


    chart_source = chart_source[
        chart_source[
            "작업부서"
        ]
        .astype(str)
        .str.strip()
        != ""
    ]


    if len(
        chart_source
    ) == 0:

        return None


    dept_chart_df = pd.crosstab(
        chart_source[
            "작업부서"
        ],
        chart_source[
            "최종판정"
        ]
    )


    for col in [
        "정상",
        "관리대상자",
        "통증호소자"
    ]:

        if col not in (
            dept_chart_df
            .columns
        ):

            dept_chart_df[
                col
            ] = 0


    dept_chart_df = (
        dept_chart_df[
            [
                "정상",
                "관리대상자",
                "통증호소자"
            ]
        ]
    )


    fig, ax = plt.subplots(
        figsize=(8, 4.5)
    )


    dept_chart_df.plot(
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


    image_stream = BytesIO()


    plt.savefig(
        image_stream,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )


    plt.close(
        fig
    )


    image_stream.seek(
        0
    )


    return image_stream


# =========================================================
# Word 보고서 생성 함수
# =========================================================

def create_word_report():

    document = Document()


    # -----------------------------------------------------
    # 기본 글꼴
    # -----------------------------------------------------

    style = (
        document
        .styles[
            "Normal"
        ]
    )


    style.font.name = (
        "Malgun Gothic"
    )


    style.font.size = (
        Pt(10)
    )


    style._element.rPr.rFonts.set(
        qn(
            "w:eastAsia"
        ),
        "맑은 고딕"
    )


    # -----------------------------------------------------
    # 제목
    # -----------------------------------------------------

    title = (
        document
        .add_paragraph()
    )


    title.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )


    title_run = title.add_run(
        report_title
    )


    title_run.bold = True


    title_run.font.size = (
        Pt(20)
    )


    document.add_paragraph(
        ""
    )


    # =====================================================
    # 1. 조사 개요
    # =====================================================

    document.add_heading(
        "1. 조사 개요",
        level=1
    )


    overview_table = (
        document
        .add_table(
            rows=5,
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
            "조사기간",
            survey_period
        ],
        [
            "작성자",
            writer
        ],
        [
            "총 조사인원",
            f"{total_count}명"
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

        overview_table.cell(
            i,
            0
        ).text = str(
            item[0]
        )


        overview_table.cell(
            i,
            1
        ).text = str(
            item[1]
        )


    document.add_paragraph(
        ""
    )


    # =====================================================
    # 2. 최종판정 현황
    # =====================================================

    document.add_heading(
        "2. 최종판정 현황",
        level=1
    )


    judgment_table = (
        document
        .add_table(
            rows=2,
            cols=5
        )
    )


    judgment_table.style = (
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


    for i in range(
        len(headers)
    ):

        judgment_table.cell(
            0,
            i
        ).text = headers[i]


        judgment_table.cell(
            1,
            i
        ).text = (
            f"{values[i]}명"
        )


    document.add_paragraph(
        ""
    )


    # =====================================================
    # 3. 신체부위별 판정 현황
    # =====================================================

    document.add_heading(
        "3. 신체부위별 판정 현황",
        level=1
    )


    part_table = (
        document
        .add_table(
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

        part_table.cell(
            0,
            i
        ).text = header


    for _, row in (
        part_summary_df
        .iterrows()
    ):

        cells = (
            part_table
            .add_row()
            .cells
        )


        cells[0].text = str(
            row[
                "신체부위"
            ]
        )


        cells[1].text = str(
            row[
                "정상"
            ]
        )


        cells[2].text = str(
            row[
                "관리대상자"
            ]
        )


        cells[3].text = str(
            row[
                "통증호소자"
            ]
        )


        cells[4].text = str(
            row[
                "유소견계"
            ]
        )


        cells[5].text = (
            f'{row["유소견율(%)"]}%'
        )


    document.add_paragraph(
        ""
    )


    bodypart_chart = (
        create_bodypart_chart()
    )


    document.add_picture(
        bodypart_chart,
        width=Inches(6.5)
    )


    document.paragraphs[
        -1
    ].alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )


    document.add_paragraph(
        ""
    )


    # =====================================================
    # 4. 부서별 판정 현황
    # =====================================================

    document.add_heading(
        "4. 부서별 판정 현황",
        level=1
    )


    department_summary = []


    valid_df = df[
        df[
            "작업부서"
        ]
        .notna()
    ].copy()


    valid_df = valid_df[
        valid_df[
            "작업부서"
        ]
        .astype(str)
        .str.strip()
        != ""
    ]


    for dept in (
        valid_df[
            "작업부서"
        ]
        .unique()
    ):

        dept_df = (
            valid_df[
                valid_df[
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


        department_summary.append(
            [
                str(
                    dept
                ),
                int(
                    dept_total
                ),
                int(
                    dept_normal
                ),
                int(
                    dept_manage
                ),
                int(
                    dept_pain
                )
            ]
        )


    if len(
        department_summary
    ) > 0:

        dept_table = (
            document
            .add_table(
                rows=1,
                cols=5
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
            "통증호소자"
        ]


        for i, header in enumerate(
            dept_headers
        ):

            dept_table.cell(
                0,
                i
            ).text = header


        for dept_row in (
            department_summary
        ):

            cells = (
                dept_table
                .add_row()
                .cells
            )


            for i, value in enumerate(
                dept_row
            ):

                cells[i].text = str(
                    value
                )


    else:

        document.add_paragraph(
            "부서별 분석 가능한 데이터가 없습니다."
        )


    department_chart = (
        create_department_chart()
    )


    if department_chart is not None:

        document.add_paragraph(
            ""
        )


        document.add_picture(
            department_chart,
            width=Inches(6.5)
        )


        document.paragraphs[
            -1
        ].alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )


    document.add_paragraph(
        ""
    )


    # =====================================================
    # 5. 사후관리 대상자
    # =====================================================

    document.add_heading(
        "5. 사후관리 대상자",
        level=1
    )


    target_df = df[
        df[
            "최종판정"
        ]
        .isin(
            [
                "관리대상자",
                "통증호소자"
            ]
        )
    ].copy()


    if len(
        target_df
    ) == 0:

        document.add_paragraph(
            "사후관리 대상자가 없습니다."
        )


    else:

        target_table = (
            document
            .add_table(
                rows=1,
                cols=5
            )
        )


        target_table.style = (
            "Table Grid"
        )


        target_headers = [
            "성명",
            "부서",
            "현재작업",
            "증상부위",
            "최종판정"
        ]


        for i, header in enumerate(
            target_headers
        ):

            target_table.cell(
                0,
                i
            ).text = header


        for _, row in (
            target_df
            .iterrows()
        ):

            abnormal_parts = []


            for part in body_parts:

                part_judgment = (
                    row.get(
                        f"{part}_판정",
                        ""
                    )
                )


                if part_judgment in [
                    "관리대상자",
                    "통증호소자"
                ]:

                    abnormal_parts.append(
                        f"{part}"
                        f"({part_judgment})"
                    )


            cells = (
                target_table
                .add_row()
                .cells
            )


            cells[0].text = str(
                row.get(
                    "성명",
                    ""
                )
            )


            cells[1].text = str(
                row.get(
                    "작업부서",
                    ""
                )
            )


            cells[2].text = str(
                row.get(
                    "현재작업",
                    ""
                )
            )


            cells[3].text = (
                ", ".join(
                    abnormal_parts
                )
            )


            cells[4].text = str(
                row.get(
                    "최종판정",
                    ""
                )
            )


    document.add_paragraph(
        ""
    )


    # =====================================================
    # 6. 종합의견
    # =====================================================

    document.add_heading(
        "6. 종합의견",
        level=1
    )


    document.add_paragraph(
        edited_opinion
    )


    document.add_paragraph(
        ""
    )


    # =====================================================
    # Word 파일 저장
    # =====================================================

    output = BytesIO()


    document.save(
        output
    )


    output.seek(
        0
    )


    return output


# =========================================================
# Word 다운로드
# =========================================================

st.subheader(
    "보고서 생성"
)


st.write(
    "현재 Supabase DB 데이터를 기준으로 "
    "Word 결과보고서를 생성합니다."
)


try:

    word_file = (
        create_word_report()
    )


    st.download_button(
        label="📄 Word 결과보고서 다운로드",
        data=word_file,
        file_name="근골격계_증상조사_결과보고서.docx",
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
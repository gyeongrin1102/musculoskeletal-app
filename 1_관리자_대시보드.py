from io import BytesIO
import streamlit as st
import pandas as pd
import os

st.set_page_config(
    page_title="관리자 대시보드",
    page_icon="📊",
    layout="wide"
)

st.title("📊 근골격계 증상조사 관리자 대시보드")

file_name = "survey_result.csv"

if not os.path.exists(file_name):
    st.warning("아직 저장된 조사 결과가 없습니다.")
    st.stop()

df = pd.read_csv(file_name)

st.subheader("조사 현황")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("총 응답자", len(df))

with col2:
    symptom_count = (df["근골격계증상여부"] == "예").sum()
    st.metric("증상 경험자", symptom_count)

with col3:
    symptom_rate = (
        symptom_count / len(df) * 100
        if len(df) > 0
        else 0
    )

    st.metric(
        "증상 경험률",
        f"{symptom_rate:.1f}%"
    )

st.divider()

st.subheader("전체 응답 데이터")

st.dataframe(
    df,
    use_container_width=True
)
st.divider()

st.subheader("신체부위별 증상자 현황")

st.divider()

st.subheader("신체부위별 증상자 현황")

body_parts = [
    "목",
    "어깨",
    "팔/팔꿈치",
    "손/손목/손가락",
    "허리",
    "다리/발"
]

summary_data = []

total_count = len(df)

for part in body_parts:

    column_name = f"{part}_증상여부"

    if column_name in df.columns:
        symptom_count = (df[column_name] == "예").sum()
    else:
        symptom_count = 0

    if total_count > 0:
        symptom_rate = symptom_count / total_count * 100
    else:
        symptom_rate = 0

    summary_data.append({
        "신체부위": part,
        "증상자수": int(symptom_count),
        "증상률(%)": round(symptom_rate, 1)
    })


summary_df = pd.DataFrame(summary_data)


st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True
)


st.subheader("신체부위별 증상률")

chart_df = summary_df[
    ["신체부위", "증상률(%)"]
].set_index("신체부위")

st.bar_chart(chart_df)
st.divider()

st.subheader("부서별 증상 현황")

# 작업부서가 비어있는 값은 제외
department_df = df[
    df["작업부서"].notna()
    & (df["작업부서"].astype(str).str.strip() != "")
].copy()

if len(department_df) == 0:

    st.info("부서 정보가 입력된 응답이 없습니다.")

else:

    department_summary = []

    for dept in department_df["작업부서"].unique():

        dept_data = department_df[
            department_df["작업부서"] == dept
        ]

        total = len(dept_data)

        symptom_count = (
            dept_data["근골격계증상여부"] == "예"
        ).sum()

        if total > 0:
            symptom_rate = symptom_count / total * 100
        else:
            symptom_rate = 0

        department_summary.append({
            "부서": dept,
            "응답자수": total,
            "증상경험자수": int(symptom_count),
            "증상경험률(%)": round(symptom_rate, 1)
        })


    department_summary_df = pd.DataFrame(
        department_summary
    )

    # 증상경험률 높은 순으로 정렬
    department_summary_df = (
        department_summary_df
        .sort_values(
            by="증상경험률(%)",
            ascending=False
        )
        .reset_index(drop=True)
    )

    st.dataframe(
        department_summary_df,
        use_container_width=True,
        hide_index=True
    )


    st.subheader("부서별 증상 경험률")

    department_chart = (
        department_summary_df[
            ["부서", "증상경험률(%)"]
        ]
        .set_index("부서")
    )

    st.bar_chart(
        department_chart
    )
    st.divider()

st.subheader("최종 판정 현황")

normal_count = (df["최종판정"] == "정상").sum()
manage_count = (df["최종판정"] == "관리대상자").sum()
pain_count = (df["최종판정"] == "통증호소자").sum()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "정상",
        f"{normal_count}명"
    )

with col2:
    st.metric(
        "관리대상자",
        f"{manage_count}명"
    )

with col3:
    st.metric(
        "통증호소자",
        f"{pain_count}명"
    )
    st.divider()

st.subheader("신체부위별 판정 현황")

body_parts = [
    "목",
    "어깨",
    "팔/팔꿈치",
    "손/손목/손가락",
    "허리",
    "다리/발"
]

part_summary = []

for part in body_parts:

    column_name = f"{part}_판정"

    if column_name in df.columns:

        normal = (df[column_name] == "정상").sum()
        manage = (df[column_name] == "관리대상자").sum()
        pain = (df[column_name] == "통증호소자").sum()

    else:

        normal = 0
        manage = 0
        pain = 0

    total_abnormal = manage + pain

    abnormal_rate = (
        total_abnormal / len(df) * 100
        if len(df) > 0
        else 0
    )

    part_summary.append({
        "신체부위": part,
        "정상": int(normal),
        "관리대상자": int(manage),
        "통증호소자": int(pain),
        "유소견계": int(total_abnormal),
        "유소견율(%)": round(abnormal_rate, 1)
    })


part_summary_df = pd.DataFrame(part_summary)

st.dataframe(
    part_summary_df,
    use_container_width=True,
    hide_index=True
)
st.subheader("신체부위별 판정 분포")

chart_df = part_summary_df[
    [
        "신체부위",
        "관리대상자",
        "통증호소자"
    ]
].set_index("신체부위")

st.bar_chart(chart_df)
st.divider()

st.subheader("부서별 판정 현황")

if "작업부서" in df.columns and "최종판정" in df.columns:

    department_df = df[
        df["작업부서"].notna()
        & (df["작업부서"].astype(str).str.strip() != "")
    ].copy()

    if len(department_df) == 0:

        st.info("부서 정보가 입력된 응답이 없습니다.")

    else:

        department_summary = []

        for dept in department_df["작업부서"].unique():

            dept_data = department_df[
                department_df["작업부서"] == dept
            ]

            total = len(dept_data)

            normal = (
                dept_data["최종판정"] == "정상"
            ).sum()

            manage = (
                dept_data["최종판정"] == "관리대상자"
            ).sum()

            pain = (
                dept_data["최종판정"] == "통증호소자"
            ).sum()

            abnormal = manage + pain

            abnormal_rate = (
                abnormal / total * 100
                if total > 0
                else 0
            )

            department_summary.append({
                "부서": dept,
                "응답자수": total,
                "정상": int(normal),
                "관리대상자": int(manage),
                "통증호소자": int(pain),
                "유소견계": int(abnormal),
                "유소견율(%)": round(abnormal_rate, 1)
            })


        department_summary_df = pd.DataFrame(
            department_summary
        )

        department_summary_df = (
            department_summary_df
            .sort_values(
                by="유소견율(%)",
                ascending=False
            )
            .reset_index(drop=True)
        )

        st.dataframe(
            department_summary_df,
            use_container_width=True,
            hide_index=True
        )


        st.subheader("부서별 판정 분포")

        department_chart_df = (
            department_summary_df[
                [
                    "부서",
                    "정상",
                    "관리대상자",
                    "통증호소자"
                ]
            ]
            .set_index("부서")
        )

        st.bar_chart(
            department_chart_df
        )

else:

    st.warning(
        "작업부서 또는 최종판정 데이터가 없습니다."
    )
    st.divider()

st.subheader("관리 대상 근로자 명단")

if "최종판정" in df.columns:

    target_df = df[
        df["최종판정"].isin([
            "관리대상자",
            "통증호소자"
        ])
    ].copy()

    if len(target_df) == 0:

        st.success(
            "현재 관리대상자 또는 통증호소자가 없습니다."
        )

    else:

        display_columns = []

        for col in [
            "성명",
            "작업부서",
            "라인/세부부서",
            "현재작업",
            "최종판정"
        ]:
            if col in target_df.columns:
                display_columns.append(col)

        target_display_df = target_df[
            display_columns
        ].copy()

        st.dataframe(
            target_display_df,
            use_container_width=True,
            hide_index=True
        )

else:

    st.warning(
        "최종판정 데이터가 없습니다."
    )
    st.subheader("관리 대상자별 증상부위")

target_detail = []

body_parts = [
    "목",
    "어깨",
    "팔/팔꿈치",
    "손/손목/손가락",
    "허리",
    "다리/발"
]

for _, row in target_df.iterrows():

    abnormal_parts = []

    for part in body_parts:

        judgment_col = f"{part}_판정"

        if judgment_col in df.columns:

            judgment = row.get(
                judgment_col,
                "정상"
            )

            if judgment in [
                "관리대상자",
                "통증호소자"
            ]:

                abnormal_parts.append(
                    f"{part}({judgment})"
                )

    target_detail.append({
        "성명": row.get("성명", ""),
        "부서": row.get("작업부서", ""),
        "현재작업": row.get("현재작업", ""),
        "증상부위": ", ".join(abnormal_parts),
        "최종판정": row.get("최종판정", "")
    })


target_detail_df = pd.DataFrame(
    target_detail
)

st.dataframe(
    target_detail_df,
    use_container_width=True,
    hide_index=True
)
st.divider()

st.subheader("개인별 상세조회")

if "성명" in df.columns and len(df) > 0:

    names = df["성명"].dropna().astype(str).tolist()

    selected_name = st.selectbox(
        "근로자를 선택하세요.",
        names
    )

    selected_rows = df[
        df["성명"].astype(str) == selected_name
    ]

    if len(selected_rows) > 0:

        row = selected_rows.iloc[-1]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**성명**")
            st.write(row.get("성명", ""))

        with col2:
            st.write("**부서**")
            st.write(row.get("작업부서", ""))

        with col3:
            st.write("**최종판정**")
            st.write(row.get("최종판정", ""))

        st.write("**현재 작업**")
        st.write(row.get("현재작업", ""))

        st.divider()

        st.write("### 신체부위별 판정")

        body_parts = [
            "목",
            "어깨",
            "팔/팔꿈치",
            "손/손목/손가락",
            "허리",
            "다리/발"
        ]

        detail_data = []

        for part in body_parts:

            detail_data.append({
                "신체부위": part,
                "판정": row.get(
                    f"{part}_판정",
                    "정상"
                ),
                "지속기간": row.get(
                    f"{part}_지속기간",
                    ""
                ),
                "증상정도": row.get(
                    f"{part}_증상정도",
                    ""
                ),
                "빈도": row.get(
                    f"{part}_빈도",
                    ""
                ),
                "최근1주증상": row.get(
                    f"{part}_최근1주증상",
                    ""
                ),
                "치료경험": row.get(
                    f"{part}_치료경험",
                    ""
                )
            })

        detail_df = pd.DataFrame(detail_data)

        st.dataframe(
            detail_df,
            use_container_width=True,
            hide_index=True
        )
        st.write("### 증상 상세")

        for part in body_parts:

            judgment = row.get(
                f"{part}_판정",
                "정상"
            )

            with st.expander(
                f"{part} - {judgment}"
            ):

                if judgment == "정상":

                    st.success("특이 증상 없음")

                else:

                    st.write(
                        "**지속기간:**",
                        row.get(
                            f"{part}_지속기간",
                            ""
                        )
                    )

                    st.write(
                        "**증상정도:**",
                        row.get(
                            f"{part}_증상정도",
                            ""
                        )
                    )

                    st.write(
                        "**발생빈도:**",
                        row.get(
                            f"{part}_빈도",
                            ""
                        )
                    )

                    st.write(
                        "**최근 1주 증상:**",
                        row.get(
                            f"{part}_최근1주증상",
                            ""
                        )
                    )

                    st.write(
                        "**치료경험:**",
                        row.get(
                            f"{part}_치료경험",
                            ""
                        )
                    )

else:

    st.info("조회할 근로자 데이터가 없습니다.")
    st.divider()

st.subheader("📥 Excel 보고자료 다운로드")


def make_excel_file():

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        # 전체 응답
        df.to_excel(
            writer,
            sheet_name="전체응답",
            index=False
        )

        # 신체부위별 판정 현황
        if "part_summary_df" in globals():

            part_summary_df.to_excel(
                writer,
                sheet_name="신체부위별현황",
                index=False
            )

        # 부서별 판정 현황
        if "department_summary_df" in globals():

            department_summary_df.to_excel(
                writer,
                sheet_name="부서별현황",
                index=False
            )

        # 관리 대상자
        if "target_detail_df" in globals():

            target_detail_df.to_excel(
                writer,
                sheet_name="관리대상자",
                index=False
            )

    output.seek(0)

    return output


excel_file = make_excel_file()


st.download_button(
    label="📊 Excel 결과보고서 다운로드",
    data=excel_file,
    file_name="근골격계_증상조사_결과.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)
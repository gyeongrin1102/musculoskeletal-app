import streamlit as st
import pandas as pd
import os
from datetime import datetime
def classify_body_part(
    symptom,
    duration,
    severity,
    frequency,
    recent,
    treatment
):

    # 증상이 없으면 정상
    if symptom != "예":
        return "정상"

    # 매우 심한 증상
    if severity in [
        "심한 통증",
        "매우 심한 통증"
    ]:
        return "통증호소자"

    # 중간 이상의 통증 + 반복적으로 발생
    if (
        severity == "중간 통증"
        and frequency in [
            "1주일에 1번 정도",
            "매일"
        ]
    ):
        return "통증호소자"

    # 최근에도 증상이 있고 치료 경험도 있음
    if (
        recent == "예"
        and treatment == "예"
    ):
        return "통증호소자"

    # 그 외 증상이 있는 경우
    return "관리대상자"
# -----------------------------
# 페이지 설정
# -----------------------------


st.title("근골격계 증상조사표")
st.caption("근로자의 근골격계 증상 및 작업 관련 특성을 확인하기 위한 조사입니다.")

st.divider()


# =========================================================
# I. 일반사항
# =========================================================

st.header("Ⅰ. 일반사항")
st.write("아래 사항을 직접 기입하여 주시기 바랍니다.")

col1, col2 = st.columns(2)

with col1:
    name = st.text_input("성명")

    gender = st.radio(
        "성별",
        ["남", "여"],
        horizontal=True,
        index=None
    )

with col2:
    age = st.number_input(
        "연령 (만 나이)",
        min_value=18,
        max_value=100,
        value=None,
        step=1
    )

    marriage = st.radio(
        "결혼 여부",
        ["기혼", "미혼"],
        horizontal=True,
        index=None
    )


st.subheader("근무 정보")

col1, col2 = st.columns(2)

with col1:
    department = st.text_input(
        "작업부서",
        placeholder="예: 정형외과병동"
    )

with col2:
    line = st.text_input(
        "라인 / 세부부서",
        placeholder="해당하는 경우 입력"
    )


col1, col2 = st.columns(2)

with col1:
    career_year = st.number_input(
        "현 직장 근무경력 - 년",
        min_value=0,
        max_value=60,
        step=1
    )

with col2:
    career_month = st.number_input(
        "현 직장 근무경력 - 개월",
        min_value=0,
        max_value=11,
        step=1
    )


st.subheader("현재 하고 있는 작업")

current_work = st.text_input(
    "현재 작업내용",
    placeholder="예: 환자 병동침대 이동"
)

col1, col2 = st.columns(2)

with col1:
    current_work_year = st.number_input(
        "현재 작업 수행기간 - 년",
        min_value=0,
        max_value=60,
        step=1
    )

with col2:
    current_work_month = st.number_input(
        "현재 작업 수행기간 - 개월",
        min_value=0,
        max_value=11,
        step=1
    )


col1, col2, col3 = st.columns(3)

with col1:
    work_hours = st.number_input(
        "1일 근무시간",
        min_value=0.0,
        max_value=24.0,
        step=0.5
    )

with col2:
    rest_minutes = st.number_input(
        "근무 중 1회 휴식시간(분)",
        min_value=0,
        max_value=300,
        step=5
    )

with col3:
    rest_count = st.number_input(
        "1일 휴식 횟수",
        min_value=0,
        max_value=20,
        step=1
    )


st.subheader("현재까지 했던 작업")

past_work = st.text_input(
    "이전에 수행했던 작업내용",
    placeholder="없으면 '없음' 입력"
)

col1, col2 = st.columns(2)

with col1:
    past_work_year = st.number_input(
        "이전 작업 수행기간 - 년",
        min_value=0,
        max_value=60,
        step=1
    )

with col2:
    past_work_month = st.number_input(
        "이전 작업 수행기간 - 개월",
        min_value=0,
        max_value=11,
        step=1
    )


st.divider()


# =========================================================
# I-1. 여가 및 취미활동
# =========================================================

st.subheader("1. 여가 및 취미활동")

st.write(
    "규칙적인 여가 및 취미활동을 하고 계십니까? "
    "(한 번에 30분 이상, 1주일에 적어도 2~3회 이상)"
)

hobbies = st.multiselect(
    "해당되는 항목을 선택하세요.",
    [
        "컴퓨터 관련 활동",
        "악기 연주",
        "뜨개질/자수/붓글씨",
        "테니스/배드민턴/스쿼시",
        "축구/족구/농구/스키 등",
        "해당사항 없음"
    ]
)


# =========================================================
# I-2. 가사노동
# =========================================================

st.subheader("2. 하루 평균 가사노동 시간")

housework = st.radio(
    "빨래하기, 청소하기, 어린아이 돌보기 등을 포함한 하루 평균 가사노동 시간은?",
    [
        "거의 하지 않는다",
        "1시간 미만",
        "1~2시간",
        "2~3시간",
        "3시간 이상"
    ],
    index=None
)


# =========================================================
# I-3. 질병력
# =========================================================

st.subheader("3. 질병 진단 여부")

disease = st.radio(
    "의사로부터 다음과 같은 질병을 진단받은 적이 있습니까?",
    ["아니오", "예"],
    horizontal=True,
    index=None
)

disease_list = []

if disease == "예":

    disease_list = st.multiselect(
        "진단받은 질병을 선택하세요.",
        [
            "류마티스 관절염",
            "당뇨병",
            "루프스병",
            "통풍",
            "기타"
        ]
    )


# =========================================================
# I-4. 과거 손상 경험
# =========================================================

st.subheader("4. 과거 손상 경험")

injury = st.radio(
    "운동 중 사고, 교통사고, 넘어짐, 추락 등으로 신체부위를 다친 적이 있습니까?",
    ["아니오", "예"],
    horizontal=True,
    index=None
)

injury_parts = []

if injury == "예":

    injury_parts = st.multiselect(
        "다친 부위를 선택하세요.",
        [
            "목",
            "어깨",
            "팔/팔꿈치",
            "손/손목/손가락",
            "허리",
            "다리/발"
        ]
    )


# =========================================================
# I-5. 육체적 부담 정도
# =========================================================

st.subheader("5. 현재 작업의 육체적 부담 정도")

physical_load = st.radio(
    "현재 하고 계시는 일의 육체적 부담 정도는 어느 정도라고 생각합니까?",
    [
        "전혀 힘들지 않음",
        "견딜만 함",
        "약간 힘듦",
        "매우 힘듦"
    ],
    horizontal=True,
    index=None
)


st.divider()


# =========================================================
# II. 근골격계 증상조사
# =========================================================

st.header("Ⅱ. 근골격계 증상조사")

st.write(
    """
지난 1년 동안 목, 어깨, 팔/팔꿈치, 손/손목/손가락, 허리, 다리/발 중
어느 한 부위에서라도 작업과 관련하여 통증이나 불편함을 느낀 적이 있습니까?

예: 통증, 쑤시는 느낌, 뻣뻣함, 화끈거리는 느낌,
무감각 또는 찌릿찌릿한 느낌 등
"""
)

has_symptom = st.radio(
    "지난 1년 동안 근골격계 증상이 있었습니까?",
    ["아니오", "예"],
    horizontal=True,
    index=None
)


# =========================================================
# 증상이 있는 경우만 표시
# =========================================================

if has_symptom == "예":

    st.info(
        "증상이 있었던 신체부위를 선택하고, "
        "각 부위별 증상에 답변해 주세요."
    )

    symptom_parts = st.multiselect(
        "증상이 있었던 신체부위",
        [
            "목",
            "어깨",
            "팔/팔꿈치",
            "손/손목/손가락",
            "허리",
            "다리/발"
        ]
    )


    # -----------------------------------------------------
    # 신체부위별 조사 함수
    # -----------------------------------------------------

    def symptom_questionnaire(part):

        st.markdown(f"### {part}")

        duration = st.radio(
            f"{part} - 한 번 아프기 시작하면 증상이 얼마나 지속됩니까?",
            [
                "1일 미만",
                "1일 이상 ~ 1주일 미만",
                "1주일 이상 ~ 1개월 미만",
                "1개월 이상 ~ 6개월 미만",
                "6개월 이상"
            ],
            key=f"{part}_duration",
            index=None
        )


        severity = st.radio(
            f"{part} - 증상의 정도는 어느 정도입니까?",
            [
                "약한 통증",
                "중간 통증",
                "심한 통증",
                "매우 심한 통증"
            ],
            key=f"{part}_severity",
            index=None
        )


        frequency = st.radio(
            f"{part} - 지난 1년 동안 이러한 증상을 얼마나 자주 경험했습니까?",
            [
                "6개월에 1번 정도",
                "2~3개월에 1번 정도",
                "1개월에 1번 정도",
                "1주일에 1번 정도",
                "매일"
            ],
            key=f"{part}_frequency",
            index=None
        )


        recent = st.radio(
            f"{part} - 지난 1주일 동안에도 이러한 증상이 있었습니까?",
            ["아니오", "예"],
            horizontal=True,
            key=f"{part}_recent",
            index=None
        )


        treatment = st.radio(
            f"{part} - 지난 1년 동안 증상으로 병원·한의원 등에서 치료를 받은 적이 있습니까?",
            ["아니오", "예"],
            horizontal=True,
            key=f"{part}_treatment",
            index=None
        )


        return {
            "duration": duration,
            "severity": severity,
            "frequency": frequency,
            "recent": recent,
            "treatment": treatment
        }


    symptom_results = {}

    for part in symptom_parts:

        with st.expander(
            f"📌 {part} 증상 입력",
            expanded=True
        ):
            symptom_results[part] = symptom_questionnaire(part)


elif has_symptom == "아니오":

    st.success(
        "지난 1년 동안 작업과 관련된 근골격계 증상이 없는 것으로 응답하셨습니다."
    )


st.divider()


# =========================================================
# 제출
# =========================================================

agree = st.checkbox(
    "입력한 내용이 사실과 같음을 확인합니다."
)

if st.button(
    "조사 제출",
    type="primary",
    use_container_width=True
):

    if not agree:
        st.error("내용 확인 후 체크박스를 선택해 주세요.")

    elif not name:
        st.error("성명을 입력해 주세요.")

    elif has_symptom is None:
        st.error("근골격계 증상 여부를 선택해 주세요.")

    else:

        # -----------------------------
        # 기본정보 저장
        # -----------------------------

        data = {
        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "성명": name,
        "성별": gender,
        "연령": age,
        "결혼여부": marriage,
        "작업부서": department,
        "라인/세부부서": line,
        "현직장_근무년": career_year,
        "현직장_근무개월": career_month,
        "현재작업": current_work,
        "현재작업_수행년": current_work_year,
        "현재작업_수행개월": current_work_month,
        "1일근무시간": work_hours,
        "휴식시간_분": rest_minutes,
        "휴식횟수": rest_count,
        "이전작업": past_work,
        "이전작업_수행년": past_work_year,
        "이전작업_수행개월": past_work_month,
        "취미활동": ", ".join(hobbies),
        "가사노동": housework,
        "질병진단여부": disease,
        "진단질병": ", ".join(disease_list),
        "과거손상여부": injury,
        "과거손상부위": ", ".join(injury_parts),
        "육체적부담": physical_load,
        "근골격계증상여부": has_symptom
        }

        # -----------------------------
        # 모든 신체부위 열을 고정 생성
        # -----------------------------
        body_parts = [
            "목",
            "어깨",
            "팔/팔꿈치",
            "손/손목/손가락",
            "허리",
            "다리/발"
        ]

        for part in body_parts:

            if (
                has_symptom == "예"
                and part in symptom_results
            ):

                result = symptom_results[part]

                data[f"{part}_증상여부"] = "예"
                data[f"{part}_지속기간"] = result["duration"]
                data[f"{part}_증상정도"] = result["severity"]
                data[f"{part}_빈도"] = result["frequency"]
                data[f"{part}_최근1주증상"] = result["recent"]
                data[f"{part}_치료경험"] = result["treatment"]

                judgment = classify_body_part(
                    symptom="예",
                    duration=result["duration"],
                    severity=result["severity"],
                    frequency=result["frequency"],
                    recent=result["recent"],
                    treatment=result["treatment"]
                )

                data[f"{part}_판정"] = judgment

            else:

                data[f"{part}_증상여부"] = "아니오"
                data[f"{part}_지속기간"] = ""
                data[f"{part}_증상정도"] = ""
                data[f"{part}_빈도"] = ""
                data[f"{part}_최근1주증상"] = ""
                data[f"{part}_치료경험"] = ""
                data[f"{part}_판정"] = "정상"
        part_judgments = []

        for part in body_parts:

            judgment = data.get(
                f"{part}_판정",
                "정상"
            )

            part_judgments.append(judgment)

        if "통증호소자" in part_judgments:
            final_judgment = "통증호소자"

        elif "관리대상자" in part_judgments:
            final_judgment = "관리대상자"

        else:
            final_judgment = "정상"

        data["최종판정"] = final_judgment



        # =====================================================
        # Supabase DB 저장
        # =====================================================

        try:
            from supabase import create_client

            supabase_url = st.secrets["SUPABASE_URL"]
            supabase_key = st.secrets["SUPABASE_KEY"]

            supabase = create_client(
                supabase_url,
                supabase_key
            )

            db_data = {
                "name": str(data.get("성명", "")),
                "gender": str(data.get("성별", "")),
                "age": int(data.get("연령", 0))
                if str(data.get("연령", "")).strip() not in ["", "None"]
                else None,

                "marriage": str(
                    data.get("결혼여부", "")
                ),

                "department": str(
                    data.get("작업부서", "")
                ),

                "sub_department": str(
                    data.get("라인/세부부서", "")
                ),

                "current_work": str(
                    data.get("현재작업", "")
                ),

                "symptom_exists": str(
                    data.get("근골격계증상여부", "")
                ),

                "final_judgment": str(
                    data.get("최종판정", "")
                ),

                # 전체 설문 원본 데이터 저장
                "survey_data": data
            }

            response = (
                supabase
                .table("survey_results")
                .insert(db_data)
                .execute()
            )

            st.success(
                "근골격계 증상조사가 정상적으로 저장되었습니다."
            )

        except Exception as e:

            st.error(
                f"저장 중 오류가 발생했습니다: {e}"
            )

import streamlit as st

from auth import require_admin, logout_button


# =========================================================
# 관리자 인증
# =========================================================

require_admin()


# =========================================================
# REBA TABLE A
# trunk × neck × legs
# =========================================================

TABLE_A = {
    1: {
        1: [1, 2, 3, 4],
        2: [1, 2, 3, 4],
        3: [3, 3, 5, 6],
    },
    2: {
        1: [2, 3, 4, 5],
        2: [3, 4, 5, 6],
        3: [4, 5, 6, 7],
    },
    3: {
        1: [2, 4, 5, 6],
        2: [4, 5, 6, 7],
        3: [5, 6, 7, 8],
    },
    4: {
        1: [3, 5, 6, 7],
        2: [5, 6, 7, 8],
        3: [6, 7, 8, 9],
    },
    5: {
        1: [4, 6, 7, 8],
        2: [6, 7, 8, 9],
        3: [7, 8, 9, 9],
    },
}


# =========================================================
# REBA TABLE B
# upper arm × lower arm × wrist
# =========================================================

TABLE_B = {
    1: {
        1: [1, 2, 2],
        2: [1, 2, 3],
    },
    2: {
        1: [1, 2, 3],
        2: [2, 3, 4],
    },
    3: {
        1: [3, 4, 5],
        2: [4, 5, 5],
    },
    4: {
        1: [4, 5, 5],
        2: [5, 6, 7],
    },
    5: {
        1: [6, 7, 8],
        2: [7, 8, 8],
    },
    6: {
        1: [7, 8, 8],
        2: [8, 9, 9],
    },
}


# =========================================================
# REBA TABLE C
# Score A × Score B
# =========================================================

TABLE_C = [
    [1, 1, 1, 2, 3, 3, 4, 5, 6, 7, 7, 7],
    [1, 2, 2, 3, 4, 4, 5, 6, 6, 7, 7, 8],
    [2, 3, 3, 3, 4, 5, 6, 7, 7, 8, 8, 8],
    [3, 4, 4, 4, 5, 6, 7, 8, 8, 9, 9, 9],
    [4, 4, 4, 5, 6, 7, 8, 8, 9, 9, 9, 9],
    [6, 6, 6, 7, 8, 8, 9, 9, 10, 10, 10, 10],
    [7, 7, 7, 8, 9, 9, 9, 10, 10, 11, 11, 11],
    [8, 8, 8, 9, 10, 10, 10, 10, 10, 11, 11, 11],
    [9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12],
    [10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 12],
    [11, 11, 11, 11, 12, 12, 12, 12, 12, 12, 12, 12],
    [12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12],
]


# =========================================================
# 위험수준 판정
# =========================================================

def classify_reba(score):

    if score <= 1:
        return {
            "level": "무시 가능",
            "action": "별도 조치가 일반적으로 필요하지 않음",
            "action_level": 0,
        }

    elif score <= 3:
        return {
            "level": "낮음",
            "action": "개선 필요 여부 검토",
            "action_level": 1,
        }

    elif score <= 7:
        return {
            "level": "중간",
            "action": "작업 개선 필요",
            "action_level": 2,
        }

    elif score <= 10:
        return {
            "level": "높음",
            "action": "빠른 시일 내 개선 필요",
            "action_level": 3,
        }

    else:
        return {
            "level": "매우 높음",
            "action": "즉각적인 개선 검토 필요",
            "action_level": 4,
        }


# =========================================================
# 페이지
# =========================================================

st.title("🤖 작업자세 REBA 보조평가")

logout_button()

st.write(
    "작업사진을 확인하면서 각 신체부위의 REBA 자세점수를 입력하면 "
    "최종 REBA 위험도를 자동 계산합니다."
)

st.info(
    "현재 버전은 '사진 확인 + REBA 자동 계산' 단계입니다. "
    "다음 단계에서 관절 위치와 각도를 사진에서 자동 추정하도록 연결합니다."
)

st.divider()


# =========================================================
# 작업 기본정보
# =========================================================

st.subheader("1. 작업 기본정보")

col1, col2 = st.columns(2)

with col1:
    worker = st.text_input(
        "작업자/대상자",
        placeholder="예: 파일공 보조작업자"
    )

    department = st.text_input(
        "부서/공종",
        placeholder="예: 토공 / 파일공"
    )

with col2:
    task_name = st.text_input(
        "작업명",
        placeholder="예: 파일 항타 보조작업"
    )

    evaluator = st.text_input(
        "평가자",
        placeholder="예: 보건관리자"
    )


# =========================================================
# 사진
# =========================================================

st.subheader("2. 작업사진")

uploaded_file = st.file_uploader(
    "평가할 작업사진을 업로드하세요.",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:

    st.image(
        uploaded_file,
        caption="REBA 평가 대상 작업사진",
        width="stretch"
    )

else:

    st.caption(
        "사진이 없어도 REBA 계산은 가능합니다."
    )


st.divider()


# =========================================================
# GROUP A
# =========================================================

st.subheader("3. Group A — 목 · 몸통 · 다리")

st.caption(
    "사진을 확인한 후 REBA 평가표에 해당하는 자세점수를 선택합니다."
)

c1, c2, c3 = st.columns(3)

with c1:

    neck = st.selectbox(
        "목 점수",
        [1, 2, 3],
        format_func=lambda x: {
            1: "1점 — 거의 중립 자세",
            2: "2점 — 굴곡/신전 자세",
            3: "3점 — 비틀림·측굴 등 보정 포함"
        }[x]
    )

with c2:

    trunk = st.selectbox(
        "몸통 점수",
        [1, 2, 3, 4, 5],
        format_func=lambda x: {
            1: "1점 — 중립",
            2: "2점 — 경미한 굴곡/신전",
            3: "3점 — 중등도 굴곡",
            4: "4점 — 큰 굴곡",
            5: "5점 — 비틀림·측굴 등을 포함한 높은 점수"
        }[x]
    )

with c3:

    legs = st.selectbox(
        "다리 점수",
        [1, 2, 3, 4],
        format_func=lambda x: {
            1: "1점 — 양발 안정 지지",
            2: "2점 — 한쪽 지지/불안정",
            3: "3점 — 무릎 굴곡 등 보정",
            4: "4점 — 큰 무릎 굴곡 등"
        }[x]
    )


st.write("#### 하중/힘")

load_score = st.selectbox(
    "하중·힘 점수",
    [0, 1, 2, 3],
    format_func=lambda x: {
        0: "0점 — 5 kg 미만",
        1: "1점 — 5~10 kg",
        2: "2점 — 10 kg 초과",
        3: "3점 — 높은 하중 + 충격/급격한 힘 발생 고려"
    }[x]
)


# =========================================================
# GROUP B
# =========================================================

st.subheader("4. Group B — 상완 · 전완 · 손목")

c1, c2, c3 = st.columns(3)

with c1:

    upper_arm = st.selectbox(
        "상완 점수",
        [1, 2, 3, 4, 5, 6],
        format_func=lambda x: f"{x}점"
    )

with c2:

    lower_arm = st.selectbox(
        "전완 점수",
        [1, 2],
        format_func=lambda x: {
            1: "1점 — 대체로 60~100°",
            2: "2점 — 그 외 자세"
        }[x]
    )

with c3:

    wrist = st.selectbox(
        "손목 점수",
        [1, 2, 3],
        format_func=lambda x: {
            1: "1점 — 중립에 가까움",
            2: "2점 — 15° 초과 굴곡/신전",
            3: "3점 — 편위·비틀림 보정 포함"
        }[x]
    )


st.write("#### 커플링(손잡이/잡기 상태)")

coupling = st.selectbox(
    "커플링 점수",
    [0, 1, 2, 3],
    format_func=lambda x: {
        0: "0점 — Good : 잡기 좋음",
        1: "1점 — Fair : 보통",
        2: "2점 — Poor : 잡기 불편",
        3: "3점 — Unacceptable : 매우 불량"
    }[x]
)


# =========================================================
# 활동 점수
# =========================================================

st.subheader("5. 활동요인")

static_posture = st.checkbox(
    "1분 이상 정적인 자세를 유지함 (+1)"
)

repetition = st.checkbox(
    "분당 4회 이상 작은 범위의 반복동작이 있음 (+1)"
)

rapid_change = st.checkbox(
    "큰 자세변화가 빠르게 발생하거나 지지기반이 불안정함 (+1)"
)


activity_score = (
    int(static_posture)
    + int(repetition)
    + int(rapid_change)
)


# =========================================================
# 계산
# =========================================================

st.divider()

if st.button(
    "🧮 REBA 점수 계산",
    type="primary",
    width="stretch"
):

    # -----------------------------
    # Table A
    # -----------------------------

    table_a_score = TABLE_A[
        trunk
    ][
        neck
    ][
        legs - 1
    ]

    score_a = min(
        table_a_score + load_score,
        12
    )


    # -----------------------------
    # Table B
    # -----------------------------

    table_b_score = TABLE_B[
        upper_arm
    ][
        lower_arm
    ][
        wrist - 1
    ]

    score_b = min(
        table_b_score + coupling,
        12
    )


    # -----------------------------
    # Table C
    # -----------------------------

    score_c = TABLE_C[
        score_a - 1
    ][
        score_b - 1
    ]


    final_score = min(
        score_c + activity_score,
        15
    )


    result = classify_reba(
        final_score
    )


    # =====================================================
    # 결과
    # =====================================================

    st.subheader("6. REBA 평가결과")

    a, b, c, d = st.columns(4)

    with a:
        st.metric(
            "Score A",
            score_a
        )

    with b:
        st.metric(
            "Score B",
            score_b
        )

    with c:
        st.metric(
            "Activity",
            activity_score
        )

    with d:
        st.metric(
            "최종 REBA",
            final_score
        )


    st.write("### 위험수준")

    if final_score <= 3:

        st.success(
            f"{result['level']} — {result['action']}"
        )

    elif final_score <= 7:

        st.warning(
            f"{result['level']} — {result['action']}"
        )

    else:

        st.error(
            f"{result['level']} — {result['action']}"
        )


    st.write(
        f"**Action Level:** {result['action_level']}"
    )


    st.write("### 평가내역")

    st.dataframe(
        {
            "항목": [
                "목",
                "몸통",
                "다리",
                "하중/힘",
                "상완",
                "전완",
                "손목",
                "커플링",
                "활동요인"
            ],
            "점수": [
                neck,
                trunk,
                legs,
                load_score,
                upper_arm,
                lower_arm,
                wrist,
                coupling,
                activity_score
            ]
        },
        hide_index=True,
        width="stretch"
    )


    st.info(
        "REBA는 관찰 기반 위험도 선별도구입니다. "
        "자동 또는 사진 기반 결과는 현장 작업조건과 실제 자세를 확인하여 "
        "평가자가 최종 검토하는 방식으로 사용하는 것이 적절합니다."
    )

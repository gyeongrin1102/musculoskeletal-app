import streamlit as st
import pandas as pd

from supabase import create_client

from auth import require_admin, logout_button
from session_query_cache import clear_session_query_cache


# =========================================================
# 관리자 인증 / 화면
# =========================================================

require_admin()

st.title("촬영 대기자료 검토")

logout_button()

st.caption("원본·AI 사진을 확인하고 수동 REBA 점수를 확정합니다.")

st.divider()


# =========================================================
# Supabase
# =========================================================

@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


supabase = get_supabase()


# =========================================================
# Private Storage 사진용 Signed URL
# =========================================================

def get_signed_url(path, expires_in=3600):
    if not path:
        return None

    try:
        response = (
            supabase
            .storage
            .from_("reba-images")
            .create_signed_url(
                path,
                expires_in
            )
        )

        signed_url = None

        if isinstance(response, str):
            signed_url = response

        elif isinstance(response, dict):
            signed_url = (
                response.get("signedURL")
                or response.get("signedUrl")
                or response.get("signed_url")
            )

        elif hasattr(response, "signedURL"):
            signed_url = response.signedURL

        elif hasattr(response, "signed_url"):
            signed_url = response.signed_url


        if not signed_url:
            return None


        # Supabase가 상대주소로 반환하는 경우
        if signed_url.startswith("/"):
            base_url = st.secrets["SUPABASE_URL"].rstrip("/")

            signed_url = (
                base_url
                + signed_url
            )


        return signed_url


    except Exception as e:
        st.warning(
            f"사진 불러오기 오류: {e}"
        )

        return None


# =========================================================
# REBA 계산표
# =========================================================

TABLE_A = {
    1: {
        1: [1, 2, 3, 4],
        2: [1, 2, 3, 4],
        3: [3, 3, 5, 6],
    },
    2: {
        1: [2, 3, 4, 5],
        2: [2, 3, 4, 5],
        3: [4, 4, 5, 6],
    },
    3: {
        1: [2, 4, 5, 6],
        2: [3, 4, 5, 6],
        3: [4, 5, 6, 7],
    },
    4: {
        1: [3, 5, 6, 7],
        2: [4, 5, 6, 7],
        3: [5, 6, 7, 8],
    },
    5: {
        1: [4, 6, 7, 8],
        2: [5, 6, 7, 8],
        3: [6, 7, 8, 9],
    },
}


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


def clamp(value, low, high):
    try:
        value = int(value)
    except Exception:
        value = low

    return max(
        low,
        min(
            value,
            high
        )
    )


def get_score_a(
    trunk_score,
    neck_score,
    legs_score,
    load_score
):
    base_score = (
        TABLE_A[
            trunk_score
        ][
            neck_score
        ][
            legs_score - 1
        ]
    )

    return min(
        base_score
        + load_score,
        12
    )


def get_score_b(
    upper_arm_score,
    lower_arm_score,
    wrist_score,
    coupling_score
):
    base_score = (
        TABLE_B[
            upper_arm_score
        ][
            lower_arm_score
        ][
            wrist_score - 1
        ]
    )

    return min(
        base_score
        + coupling_score,
        12
    )


def get_table_c_score(
    score_a,
    score_b
):
    a_index = min(
        max(score_a, 1),
        12
    ) - 1

    b_index = min(
        max(score_b, 1),
        12
    ) - 1

    return TABLE_C[
        a_index
    ][
        b_index
    ]


def classify_reba(score):
    if score <= 1:
        return (
            "무시 가능 (Negligible)",
            0,
            "개선 불필요"
        )

    elif score <= 3:
        return (
            "낮음 (Low)",
            1,
            "개선 필요 가능성 있음"
        )

    elif score <= 7:
        return (
            "보통 (Medium)",
            2,
            "개선 필요"
        )

    elif score <= 10:
        return (
            "높음 (High)",
            3,
            "빠른 시일 내 개선 필요"
        )

    else:
        return (
            "매우 높음 (Very High)",
            4,
            "즉각적 조치 필요"
        )


# =========================================================
# 대기자료 조회
# =========================================================

try:
    response = (
        supabase
        .table("reba_capture_queue")
        .select("*")
        .eq(
            "status",
            "대기"
        )
        .order(
            "created_at",
            desc=False
        )
        .execute()
    )

    rows = response.data or []

except Exception as e:
    st.error(
        f"촬영 대기자료 조회 오류: {e}"
    )
    st.stop()


if not rows:
    st.success(
        "현재 검토 대기 중인 촬영자료가 없습니다."
    )
    st.stop()


# =========================================================
# 촬영자료 선택
# =========================================================

st.subheader(
    "1. 검토할 촬영자료 선택"
)

options = {}

for row in rows:
    company = (
        row.get("company")
        or "업체미입력"
    )

    department = (
        row.get("department")
        or ""
    )

    task_name = (
        row.get("task_name")
        or "작업미입력"
    )

    worker = (
        row.get("worker")
        or "이름없음"
    )

    label = (
        f"#{row.get('id', '')} | "
        f"{company} | "
        f"{department} | "
        f"{task_name} | "
        f"{worker}"
    )

    options[label] = row


selected_label = st.selectbox(
    "자료를 선택하세요.",
    list(options.keys())
)

selected = options[selected_label]


# =========================================================
# 기본정보
# =========================================================

company = str(
    selected.get(
        "company",
        ""
    )
    or ""
)

department = str(
    selected.get(
        "department",
        ""
    )
    or ""
)

task_name = str(
    selected.get(
        "task_name",
        ""
    )
    or ""
)

worker = str(
    selected.get(
        "worker",
        ""
    )
    or ""
)

pose_angles = (
    selected.get(
        "pose_angles"
    )
    or {}
)

ai_recommendation = (
    selected.get(
        "ai_recommendation"
    )
    or {}
)


st.write(
    f"**업체명:** {company or '-'}"
)

st.write(
    f"**공종 / 부서:** {department or '-'}"
)

st.write(
    f"**작업명:** {task_name or '-'}"
)

st.write(
    f"**근로자:** {worker or '-'}"
)


# =========================================================
# 사진 표시 - Signed URL 사용
# =========================================================

original_path = (
    selected.get(
        "original_image_path"
    )
)

analyzed_path = (
    selected.get(
        "analyzed_image_path"
    )
)

original_url = get_signed_url(
    original_path
)

analyzed_url = get_signed_url(
    analyzed_path
)


st.write(
    "#### 작업사진"
)


c1, c2 = st.columns(2)


with c1:
    if original_url:
        st.image(
            original_url,
            caption="원본 작업사진",
            width="stretch"
        )
    else:
        st.warning(
            "원본사진을 불러오지 못했습니다."
        )

        if original_path:
            st.caption(
                f"저장경로: {original_path}"
            )


with c2:
    if analyzed_url:
        st.image(
            analyzed_url,
            caption="AI 관절선 분석사진",
            width="stretch"
        )
    else:
        st.warning(
            "AI 분석사진을 불러오지 못했습니다."
        )

        if analyzed_path:
            st.caption(
                f"저장경로: {analyzed_path}"
            )


# =========================================================
# AI 초안
# =========================================================

if pose_angles:
    st.write(
        "#### AI 관절각도"
    )

    angle_df = pd.DataFrame(
        [
            [
                "왼쪽 팔꿈치",
                pose_angles.get(
                    "left_elbow",
                    ""
                )
            ],
            [
                "오른쪽 팔꿈치",
                pose_angles.get(
                    "right_elbow",
                    ""
                )
            ],
            [
                "왼쪽 무릎",
                pose_angles.get(
                    "left_knee",
                    ""
                )
            ],
            [
                "오른쪽 무릎",
                pose_angles.get(
                    "right_knee",
                    ""
                )
            ],
            [
                "왼쪽 위팔",
                pose_angles.get(
                    "left_upper_arm",
                    ""
                )
            ],
            [
                "오른쪽 위팔",
                pose_angles.get(
                    "right_upper_arm",
                    ""
                )
            ],
            [
                "몸통 기울기",
                pose_angles.get(
                    "trunk_angle",
                    ""
                )
            ],
        ],
        columns=[
            "관절/부위",
            "각도(°)"
        ]
    )

    st.dataframe(
        angle_df,
        hide_index=True,
        width="stretch"
    )


st.divider()


# =========================================================
# 최종 REBA 평가
# =========================================================

st.subheader(
    "2. REBA 최종점수 확정"
)

st.info(
    "몸통·다리·위팔·아래팔은 AI 초안을 불러옵니다. "
    "목·손목·하중·결합도·활동점수는 실제 작업조건을 확인해 입력해주세요."
)


default_trunk = clamp(
    ai_recommendation.get(
        "trunk_score",
        1
    ),
    1,
    5
)

default_legs = clamp(
    ai_recommendation.get(
        "legs_score",
        1
    ),
    1,
    4
)

default_upper = clamp(
    ai_recommendation.get(
        "upper_arm_score",
        1
    ),
    1,
    6
)

default_lower = clamp(
    ai_recommendation.get(
        "lower_arm_score",
        1
    ),
    1,
    2
)


c1, c2, c3 = st.columns(3)


with c1:
    neck_score = st.selectbox(
        "목(Neck)",
        [1, 2, 3],
        index=0
    )

    trunk_values = [
        1, 2, 3, 4, 5
    ]

    trunk_score = st.selectbox(
        "몸통(Trunk)",
        trunk_values,
        index=(
            trunk_values.index(
                default_trunk
            )
        )
    )

    legs_values = [
        1, 2, 3, 4
    ]

    legs_score = st.selectbox(
        "다리(Legs)",
        legs_values,
        index=(
            legs_values.index(
                default_legs
            )
        )
    )


with c2:
    upper_values = [
        1, 2, 3, 4, 5, 6
    ]

    upper_arm_score = (
        st.selectbox(
            "위팔(Upper Arm)",
            upper_values,
            index=(
                upper_values.index(
                    default_upper
                )
            )
        )
    )

    lower_values = [
        1, 2
    ]

    lower_arm_score = (
        st.selectbox(
            "아래팔(Lower Arm)",
            lower_values,
            index=(
                lower_values.index(
                    default_lower
                )
            )
        )
    )

    wrist_score = st.selectbox(
        "손목(Wrist)",
        [1, 2, 3],
        index=0
    )


with c3:
    load_score = st.selectbox(
        "하중/힘(Load)",
        [0, 1, 2, 3],
        index=0
    )

    coupling_score = st.selectbox(
        "결합도(Coupling)",
        [0, 1, 2, 3],
        index=0
    )

    activity_score = st.selectbox(
        "활동점수(Activity)",
        [0, 1, 2, 3],
        index=0
    )


score_a = get_score_a(
    trunk_score,
    neck_score,
    legs_score,
    load_score
)


score_b = get_score_b(
    upper_arm_score,
    lower_arm_score,
    wrist_score,
    coupling_score
)


table_c_score = (
    get_table_c_score(
        score_a,
        score_b
    )
)


final_reba = min(
    table_c_score
    + activity_score,
    15
)


(
    risk_level,
    action_level,
    action_text
) = classify_reba(
    final_reba
)


r1, r2, r3, r4 = (
    st.columns(4)
)


with r1:
    st.metric(
        "Score A",
        score_a
    )


with r2:
    st.metric(
        "Score B",
        score_b
    )


with r3:
    st.metric(
        "Table C",
        table_c_score
    )


with r4:
    st.metric(
        "최종 REBA",
        final_reba
    )


st.write(
    f"**위험등급:** {risk_level}"
)

st.write(
    f"**조치권고:** {action_text}"
)


evaluator = st.text_input(
    "평가자",
    placeholder="예: 보건관리자"
)


# =========================================================
# 최종 저장
# =========================================================

st.divider()

st.subheader(
    "3. 최종 확정"
)


if st.button(
    "✅ REBA 최종 확정 및 저장",
    type="primary",
    width="stretch"
):
    try:
        save_department = (
            f"{company} / {department}"
            if (
                company
                and department
            )
            else (
                company
                or department
            )
        )

        insert_data = {
            "worker":
                worker,

            "department":
                save_department,

            "task_name":
                task_name,

            "evaluator":
                evaluator,

            "pose_angles":
                pose_angles,

            "ai_recommendation":
                ai_recommendation,

            "neck_score":
                neck_score,

            "trunk_score":
                trunk_score,

            "legs_score":
                legs_score,

            "load_score":
                load_score,

            "upper_arm_score":
                upper_arm_score,

            "lower_arm_score":
                lower_arm_score,

            "wrist_score":
                wrist_score,

            "coupling_score":
                coupling_score,

            "activity_score":
                activity_score,

            "score_a":
                score_a,

            "score_b":
                score_b,

            "final_reba":
                final_reba,

            "risk_level":
                risk_level,

            "action_level":
                action_level,

            "action_text":
                action_text,

            "original_image_path":
                original_path,

            "analyzed_image_path":
                analyzed_path,
        }

        (
            supabase
            .table(
                "reba_results"
            )
            .insert(
                insert_data
            )
            .execute()
        )

        (
            supabase
            .table(
                "reba_capture_queue"
            )
            .update(
                {
                    "status":
                        "완료"
                }
            )
            .eq(
                "id",
                selected[
                    "id"
                ]
            )
            .execute()
        )
        clear_session_query_cache()

        st.success(
            "✅ 최종 REBA 평가가 저장되었습니다. "
            "촬영자료는 '완료' 처리되었습니다."
        )

        st.rerun()

    except Exception as e:
        st.error(
            f"최종 저장 오류: {e}"
        )

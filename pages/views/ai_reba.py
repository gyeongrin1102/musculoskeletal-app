import streamlit as st
import os
import math
import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from auth import require_admin, logout_button


# =========================================================
# 관리자 인증
# =========================================================

require_admin()
# =========================================================
# AI 자세분석 기본 설정
# =========================================================

MODEL_PATH = "models/pose_landmarker.task"


POSE_CONNECTIONS = [
    (11, 12),  # 어깨
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),

    (11, 23),
    (12, 24),
    (23, 24),

    (23, 25),
    (25, 27),
    (24, 26),
    (26, 28),

    (27, 29),
    (29, 31),
    (28, 30),
    (30, 32),
]


def calculate_angle(a, b, c):
    """
    b점을 중심으로 a-b-c 사이 각도를 계산
    """

    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    denominator = (
        np.linalg.norm(ba)
        * np.linalg.norm(bc)
    )

    if denominator == 0:
        return None

    cosine_angle = (
        np.dot(ba, bc)
        / denominator
    )

    cosine_angle = np.clip(
        cosine_angle,
        -1.0,
        1.0
    )

    angle = np.degrees(
        np.arccos(cosine_angle)
    )

    return round(float(angle), 1)


def landmark_xy(
    landmarks,
    index,
    width,
    height
):

    lm = landmarks[index]

    return (
        int(lm.x * width),
        int(lm.y * height)
    )


def analyze_pose(image_rgb):

    if not os.path.exists(MODEL_PATH):

        return None, None, (
            "pose_landmarker.task 모델 파일을 "
            "찾을 수 없습니다."
        )

    base_options = python.BaseOptions(
        model_asset_path=MODEL_PATH
    )

    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5
    )

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=image_rgb
    )

    with vision.PoseLandmarker.create_from_options(
        options
    ) as landmarker:

        result = landmarker.detect(
            mp_image
        )

    if not result.pose_landmarks:

        return None, None, (
            "사진에서 작업자의 자세를 "
            "인식하지 못했습니다."
        )

    landmarks = result.pose_landmarks[0]

    return landmarks, result, None


def draw_pose(
    image_rgb,
    landmarks
):

    output = image_rgb.copy()

    height, width = output.shape[:2]

    # 관절 연결선
    for start_idx, end_idx in POSE_CONNECTIONS:

        p1 = landmark_xy(
            landmarks,
            start_idx,
            width,
            height
        )

        p2 = landmark_xy(
            landmarks,
            end_idx,
            width,
            height
        )

        cv2.line(
            output,
            p1,
            p2,
            (0, 255, 0),
            3
        )

    # 관절점
    important_points = [
        11, 12,
        13, 14,
        15, 16,
        23, 24,
        25, 26,
        27, 28
    ]

    for idx in important_points:

        point = landmark_xy(
            landmarks,
            idx,
            width,
            height
        )

        cv2.circle(
            output,
            point,
            6,
            (255, 0, 0),
            -1
        )

    return output


def get_pose_angles(
    landmarks,
    width,
    height
):

    def pt(i):

        return landmark_xy(
            landmarks,
            i,
            width,
            height
        )

    left_shoulder = pt(11)
    right_shoulder = pt(12)

    left_elbow = pt(13)
    right_elbow = pt(14)

    left_wrist = pt(15)
    right_wrist = pt(16)

    left_hip = pt(23)
    right_hip = pt(24)

    left_knee = pt(25)
    right_knee = pt(26)

    left_ankle = pt(27)
    right_ankle = pt(28)


    left_elbow_angle = calculate_angle(
        left_shoulder,
        left_elbow,
        left_wrist
    )

    right_elbow_angle = calculate_angle(
        right_shoulder,
        right_elbow,
        right_wrist
    )


    left_knee_angle = calculate_angle(
        left_hip,
        left_knee,
        left_ankle
    )

    right_knee_angle = calculate_angle(
        right_hip,
        right_knee,
        right_ankle
    )


    left_shoulder_angle = calculate_angle(
        left_elbow,
        left_shoulder,
        left_hip
    )

    right_shoulder_angle = calculate_angle(
        right_elbow,
        right_shoulder,
        right_hip
    )


    shoulder_mid = (
        (
            left_shoulder[0]
            + right_shoulder[0]
        ) / 2,

        (
            left_shoulder[1]
            + right_shoulder[1]
        ) / 2
    )

    hip_mid = (
        (
            left_hip[0]
            + right_hip[0]
        ) / 2,

        (
            left_hip[1]
            + right_hip[1]
        ) / 2
    )


    vertical_reference = (
        hip_mid[0],
        hip_mid[1] - 100
    )


    trunk_angle = calculate_angle(
        shoulder_mid,
        hip_mid,
        vertical_reference
    )


    return {
        "왼쪽 팔꿈치": left_elbow_angle,
        "오른쪽 팔꿈치": right_elbow_angle,
        "왼쪽 무릎": left_knee_angle,
        "오른쪽 무릎": right_knee_angle,
        "왼쪽 상완": left_shoulder_angle,
        "오른쪽 상완": right_shoulder_angle,
        "몸통 기울기": trunk_angle
    }
    # =========================================================
# AI 관절각 → REBA 기본점수 추천
# =========================================================

def recommend_reba_from_angles(angles):

    # -----------------------------
    # 몸통
    # -----------------------------
    trunk_angle = abs(
        angles.get("몸통 기울기") or 0
    )

    if trunk_angle <= 5:
        trunk_score = 1
    elif trunk_angle <= 20:
        trunk_score = 2
    elif trunk_angle <= 60:
        trunk_score = 3
    else:
        trunk_score = 4


    # -----------------------------
    # 상완
    # 좌/우 중 더 불리한 자세 사용
    # -----------------------------
    upper_angles = [
        angles.get("왼쪽 상완"),
        angles.get("오른쪽 상완")
    ]

    upper_angles = [
        x for x in upper_angles
        if x is not None
    ]

    upper_angle = (
        max(upper_angles)
        if upper_angles
        else 0
    )

    if upper_angle <= 20:
        upper_arm_score = 1
    elif upper_angle <= 45:
        upper_arm_score = 2
    elif upper_angle <= 90:
        upper_arm_score = 3
    else:
        upper_arm_score = 4


    # -----------------------------
    # 전완
    # 한쪽이라도 60~100°를 벗어나면 2점 추천
    # -----------------------------
    elbow_angles = [
        angles.get("왼쪽 팔꿈치"),
        angles.get("오른쪽 팔꿈치")
    ]

    elbow_angles = [
        x for x in elbow_angles
        if x is not None
    ]

    lower_arm_score = 1

    for elbow_angle in elbow_angles:

        if not (
            60 <= elbow_angle <= 100
        ):
            lower_arm_score = 2
            break


    # -----------------------------
    # 다리
    # 무릎 굴곡 정도만 이용한 보조 추천
    # -----------------------------
    knee_angles = [
        angles.get("왼쪽 무릎"),
        angles.get("오른쪽 무릎")
    ]

    knee_angles = [
        x for x in knee_angles
        if x is not None
    ]

    if knee_angles:

        knee_flexions = [
            max(
                0,
                180 - angle
            )
            for angle in knee_angles
        ]

        max_knee_flexion = max(
            knee_flexions
        )

    else:

        max_knee_flexion = 0


    if max_knee_flexion < 30:
        legs_score = 1

    elif max_knee_flexion <= 60:
        legs_score = 2

    else:
        legs_score = 3


    return {
        "trunk": trunk_score,
        "upper_arm": upper_arm_score,
        "lower_arm": lower_arm_score,
        "legs": legs_score,

        "trunk_angle": round(
            trunk_angle,
            1
        ),

        "upper_arm_angle": round(
            upper_angle,
            1
        ),

        "max_knee_flexion": round(
            max_knee_flexion,
            1
        )
    }


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

# =========================================================
# 사진 + AI 자세분석
# =========================================================

st.subheader(
    "2. 작업사진 및 AI 자세분석"
)


uploaded_file = st.file_uploader(
    "평가할 작업사진을 업로드하세요.",
    type=[
        "jpg",
        "jpeg",
        "png"
    ]
)


if uploaded_file is not None:

    file_bytes = np.asarray(
        bytearray(
            uploaded_file.read()
        ),
        dtype=np.uint8
    )

    image_bgr = cv2.imdecode(
        file_bytes,
        cv2.IMREAD_COLOR
    )

    image_rgb = cv2.cvtColor(
        image_bgr,
        cv2.COLOR_BGR2RGB
    )


    st.write("#### 원본 작업사진")

    st.image(
        image_rgb,
        width="stretch"
    )


    if st.button(
        "🤖 AI 자세 분석 실행",
        type="primary"
    ):

        with st.spinner(
            "작업자의 관절 위치를 분석하고 있습니다..."
        ):

            landmarks, result, error = (
                analyze_pose(
                    image_rgb
                )
            )


        if error:

            st.error(
                error
            )


        else:

            st.success(
                "작업자 자세를 인식했습니다."
            )


            analyzed_image = draw_pose(
                image_rgb,
                landmarks
            )


            st.write(
                "#### AI 관절 인식 결과"
            )

            st.image(
                analyzed_image,
                width="stretch"
            )


            height, width = (
                image_rgb.shape[:2]
            )


            angles = get_pose_angles(
                landmarks,
                width,
                height
            )
            # REBA 자동 추천값 계산
recommendation = recommend_reba_from_angles(
    angles
)


# REBA 입력창에 추천값 전달
st.session_state[
    "reba_trunk"
] = recommendation[
    "trunk"
]

st.session_state[
    "reba_upper_arm"
] = recommendation[
    "upper_arm"
]

st.session_state[
    "reba_lower_arm"
] = recommendation[
    "lower_arm"
]

st.session_state[
    "reba_legs"
] = recommendation[
    "legs"
]


# 추천결과 저장
st.session_state[
    "ai_reba_recommendation"
] = recommendation


            st.write(
                "#### 주요 관절각"
            )


            angle_data = []

            for name, value in (
                angles.items()
            ):

                angle_data.append(
                    {
                        "부위": name,
                        "측정각도": (
                            f"{value}°"
                            if value is not None
                            else "-"
                        )
                    }
                )


            st.dataframe(
                angle_data,
                hide_index=True,
                width="stretch"
            )
st.write(
    "#### 🤖 AI REBA 추천"
)

st.success(
    f"""
    AI가 사진에서 확인 가능한 자세를 기준으로
    다음 점수를 추천했습니다.

    - 몸통: {recommendation['trunk']}점
    - 상완: {recommendation['upper_arm']}점
    - 전완: {recommendation['lower_arm']}점
    - 다리: {recommendation['legs']}점
    """
)

st.caption(
    "※ 목, 손목, 하중, 커플링, 활동요인은 "
    "사진만으로 정확한 판단이 어려우므로 "
    "평가자가 직접 확인해야 합니다."
)



            st.info(
                "AI 관절각은 사진의 촬영 방향, "
                "원근, 작업자 가림 및 카메라 각도에 "
                "따라 실제 관절각과 차이가 발생할 수 있습니다. "
                "REBA 최종 평가는 평가자가 사진과 "
                "현장 작업조건을 함께 확인해야 합니다."
            )


else:

    st.caption(
        "사진이 없어도 기존 REBA 수동 평가는 가능합니다."
    )


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
        key="reba_trunk",
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
    key="reba_legs",
    format_func=lambda x: {
        1: "1점 — 양발 안정 지지",
        2: "2점 — 한쪽 지지/불안정 또는 무릎 굴곡",
        3: "3점 — 큰 무릎 굴곡 등",
        4: "4점 — 매우 불리한 하지 자세"
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
    key="reba_upper_arm",
    format_func=lambda x: f"{x}점"
)

with c2:

    lower_arm = st.selectbox(
    "전완 점수",
    [1, 2],
    key="reba_lower_arm",
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

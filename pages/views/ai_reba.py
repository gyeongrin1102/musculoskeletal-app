from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from supabase import create_client

from auth import require_admin, logout_button


# =========================================================
# 관리자 인증
# =========================================================

require_admin()


# =========================================================
# Supabase 연결
# =========================================================

@st.cache_resource
def get_supabase():

    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


supabase = get_supabase()


# =========================================================
# 모델 경로
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "pose_landmarker.task"
)


# =========================================================
# MediaPipe 관절 연결선
# =========================================================

POSE_CONNECTIONS = [
    (11, 12),
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


IMPORTANT_POINTS = [
    11, 12,
    13, 14,
    15, 16,
    23, 24,
    25, 26,
    27, 28,
]


# =========================================================
# REBA TABLE A
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
# 각도 계산
# =========================================================

def calculate_angle(a, b, c):

    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    c = np.array(c, dtype=float)

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

    return round(
        float(angle),
        1
    )


# =========================================================
# 랜드마크 좌표
# =========================================================

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


def landmark_visible(
    landmarks,
    index,
    threshold=0.35
):

    lm = landmarks[index]

    visibility = getattr(
        lm,
        "visibility",
        1.0
    )

    return visibility >= threshold


# =========================================================
# MediaPipe 자세 분석
# =========================================================

def analyze_pose(image_rgb):

    if not MODEL_PATH.exists():

        return (
            None,
            "pose_landmarker.task 모델 파일을 찾을 수 없습니다."
        )

    try:

        base_options = python.BaseOptions(
            model_asset_path=str(MODEL_PATH)
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

            return (
                None,
                "사진에서 작업자의 자세를 인식하지 못했습니다."
            )

        return (
            result.pose_landmarks[0],
            None
        )

    except Exception as e:

        return (
            None,
            f"AI 자세분석 중 오류가 발생했습니다: {e}"
        )


# =========================================================
# 관절점 표시
# =========================================================

def draw_pose(
    image_rgb,
    landmarks
):

    output = image_rgb.copy()

    height, width = output.shape[:2]


    for start_idx, end_idx in POSE_CONNECTIONS:

        if not landmark_visible(
            landmarks,
            start_idx
        ):
            continue

        if not landmark_visible(
            landmarks,
            end_idx
        ):
            continue

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


    for idx in IMPORTANT_POINTS:

        if not landmark_visible(
            landmarks,
            idx
        ):
            continue

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


# =========================================================
# 주요 관절각 계산
# =========================================================

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

        "왼쪽 팔꿈치":
            left_elbow_angle,

        "오른쪽 팔꿈치":
            right_elbow_angle,

        "왼쪽 무릎":
            left_knee_angle,

        "오른쪽 무릎":
            right_knee_angle,

        "왼쪽 상완":
            left_shoulder_angle,

        "오른쪽 상완":
            right_shoulder_angle,

        "몸통 기울기":
            trunk_angle
    }


# =========================================================
# AI 관절각 → REBA 추천
# =========================================================

def recommend_reba_from_angles(
    angles
):

    trunk_angle = abs(
        angles.get(
            "몸통 기울기"
        )
        or 0
    )


    if trunk_angle <= 5:
        trunk_score = 1

    elif trunk_angle <= 20:
        trunk_score = 2

    elif trunk_angle <= 60:
        trunk_score = 3

    else:
        trunk_score = 4


    upper_angles = [
        angles.get("왼쪽 상완"),
        angles.get("오른쪽 상완")
    ]

    upper_angles = [
        x
        for x in upper_angles
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


    elbow_angles = [
        angles.get("왼쪽 팔꿈치"),
        angles.get("오른쪽 팔꿈치")
    ]

    elbow_angles = [
        x
        for x in elbow_angles
        if x is not None
    ]


    lower_arm_score = 1

    for elbow_angle in elbow_angles:

        if not (
            60
            <= elbow_angle
            <= 100
        ):

            lower_arm_score = 2
            break


    knee_angles = [
        angles.get("왼쪽 무릎"),
        angles.get("오른쪽 무릎")
    ]

    knee_angles = [
        x
        for x in knee_angles
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

        "trunk":
            trunk_score,

        "upper_arm":
            upper_arm_score,

        "lower_arm":
            lower_arm_score,

        "legs":
            legs_score,

        "trunk_angle":
            round(
                trunk_angle,
                1
            ),

        "upper_arm_angle":
            round(
                upper_angle,
                1
            ),

        "max_knee_flexion":
            round(
                max_knee_flexion,
                1
            )
    }


# =========================================================
# 위험수준 판정
# =========================================================

def classify_reba(score):

    if score <= 1:

        return {
            "level": "무시 가능",
            "action": "별도 조치가 일반적으로 필요하지 않음",
            "action_level": 0
        }


    elif score <= 3:

        return {
            "level": "낮음",
            "action": "개선 필요 여부 검토",
            "action_level": 1
        }


    elif score <= 7:

        return {
            "level": "중간",
            "action": "작업 개선 필요",
            "action_level": 2
        }


    elif score <= 10:

        return {
            "level": "높음",
            "action": "빠른 시일 내 개선 필요",
            "action_level": 3
        }


    else:

        return {
            "level": "매우 높음",
            "action": "즉각적인 개선 검토 필요",
            "action_level": 4
        }


# =========================================================
# 페이지
# =========================================================

st.title(
    "🤖 AI 작업자세 · REBA 평가"
)

logout_button()


st.write(
    "작업사진을 업로드하면 AI가 주요 관절 위치와 "
    "각도를 분석하고 REBA 자세점수를 보조 추천합니다."
)


st.info(
    "AI 결과는 보조자료입니다. 실제 하중, 반복성, "
    "지속시간, 작업자세 및 현장조건을 평가자가 "
    "최종 확인해야 합니다."
)


st.divider()


# =========================================================
# 1. 작업 기본정보
# =========================================================

st.subheader(
    "1. 작업 기본정보"
)


col1, col2 = st.columns(2)


with col1:

    worker = st.text_input(
        "작업자/대상자",
        placeholder="예: 파일공 보조작업자"
    )

    department = st.text_input(
        "부서/공종",
        placeholder="예: 파일공"
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


st.divider()


# =========================================================
# 2. 사진 및 AI 분석
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
            uploaded_file.getvalue()
        ),
        dtype=np.uint8
    )


    image_bgr = cv2.imdecode(
        file_bytes,
        cv2.IMREAD_COLOR
    )


    if image_bgr is None:

        st.error(
            "이미지 파일을 읽을 수 없습니다."
        )

    else:

        image_rgb = cv2.cvtColor(
            image_bgr,
            cv2.COLOR_BGR2RGB
        )


        st.write(
            "#### 원본 작업사진"
        )

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

                landmarks, error = analyze_pose(
                    image_rgb
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


                recommendation = (
                    recommend_reba_from_angles(
                        angles
                    )
                )


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


                st.session_state[
                    "ai_reba_recommendation"
                ] = recommendation


                st.session_state[
                    "ai_pose_angles"
                ] = angles


# =========================================================
# AI 분석 결과 표시
# =========================================================

if (
    "ai_pose_angles"
    in st.session_state
):

    angles = st.session_state[
        "ai_pose_angles"
    ]


    recommendation = st.session_state[
        "ai_reba_recommendation"
    ]


    st.write(
        "#### 주요 관절각"
    )


    angle_data = []


    for name, value in angles.items():

        angle_data.append(
            {
                "부위": name,

                "측정각도":
                    (
                        f"{value}°"
                        if value is not None
                        else "-"
                    )
            }
        )


    st.dataframe(
        pd.DataFrame(
            angle_data
        ),
        hide_index=True,
        width="stretch"
    )


    st.write(
        "#### 🤖 AI REBA 추천"
    )


    st.success(
        f"""
AI가 사진에서 확인 가능한 자세를 기준으로 추천했습니다.

- **몸통:** {recommendation['trunk']}점
- **상완:** {recommendation['upper_arm']}점
- **전완:** {recommendation['lower_arm']}점
- **다리:** {recommendation['legs']}점
"""
    )


    st.caption(
        "※ 목, 손목, 하중, 커플링, 활동요인 등은 "
        "평가자가 실제 작업조건을 확인하여 판단하세요."
    )


st.divider()


# =========================================================
# 3. Group A
# =========================================================

st.subheader(
    "3. Group A — 목 · 몸통 · 다리"
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
            5: "5점 — 비틀림·측굴 등 보정 포함"
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


load_score = st.selectbox(
    "하중·힘 점수",
    [0, 1, 2, 3],
    format_func=lambda x: {
        0: "0점 — 5 kg 미만",
        1: "1점 — 5~10 kg",
        2: "2점 — 10 kg 초과",
        3: "3점 — 높은 하중 + 충격/급격한 힘"
    }[x]
)


st.divider()


# =========================================================
# 4. Group B
# =========================================================

st.subheader(
    "4. Group B — 상완 · 전완 · 손목"
)


c1, c2, c3 = st.columns(3)


with c1:

    upper_arm = st.selectbox(
        "상완 점수",
        [1, 2, 3, 4, 5, 6],
        key="reba_upper_arm",
        format_func=lambda x:
            f"{x}점"
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


coupling = st.selectbox(
    "커플링 점수",
    [0, 1, 2, 3],
    format_func=lambda x: {
        0: "0점 — Good",
        1: "1점 — Fair",
        2: "2점 — Poor",
        3: "3점 — Unacceptable"
    }[x]
)


st.divider()


# =========================================================
# 5. 활동요인
# =========================================================

st.subheader(
    "5. 활동요인"
)


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


st.divider()


# =========================================================
# 6. REBA 계산
# =========================================================

if st.button(
    "🧮 REBA 점수 계산",
    type="primary",
    width="stretch"
):

    table_a_score = TABLE_A[
        trunk
    ][
        neck
    ][
        legs - 1
    ]


    score_a = min(
        table_a_score
        + load_score,
        12
    )


    table_b_score = TABLE_B[
        upper_arm
    ][
        lower_arm
    ][
        wrist - 1
    ]


    score_b = min(
        table_b_score
        + coupling,
        12
    )


    score_c = TABLE_C[
        score_a - 1
    ][
        score_b - 1
    ]


    final_score = min(
        score_c
        + activity_score,
        15
    )


    result = classify_reba(
        final_score
    )


    # 결과를 session_state에 저장
    st.session_state[
        "latest_reba_result"
    ] = {

        "worker":
            worker,

        "department":
            department,

        "task_name":
            task_name,

        "evaluator":
            evaluator,

        "neck_score":
            neck,

        "trunk_score":
            trunk,

        "legs_score":
            legs,

        "load_score":
            load_score,

        "upper_arm_score":
            upper_arm,

        "lower_arm_score":
            lower_arm,

        "wrist_score":
            wrist,

        "coupling_score":
            coupling,

        "activity_score":
            activity_score,

        "score_a":
            score_a,

        "score_b":
            score_b,

        "final_reba":
            final_score,

        "risk_level":
            result[
                "level"
            ],

        "action_level":
            result[
                "action_level"
            ],

        "action_text":
            result[
                "action"
            ]
    }


# =========================================================
# 7. 계산 결과 표시
# =========================================================

if (
    "latest_reba_result"
    in st.session_state
):

    saved_result = st.session_state[
        "latest_reba_result"
    ]


    st.subheader(
        "6. REBA 평가결과"
    )


    a, b, c, d = st.columns(4)


    with a:

        st.metric(
            "Score A",
            saved_result[
                "score_a"
            ]
        )


    with b:

        st.metric(
            "Score B",
            saved_result[
                "score_b"
            ]
        )


    with c:

        st.metric(
            "Activity",
            saved_result[
                "activity_score"
            ]
        )


    with d:

        st.metric(
            "최종 REBA",
            saved_result[
                "final_reba"
            ]
        )


    st.write(
        "### 위험수준"
    )


    final_score = saved_result[
        "final_reba"
    ]


    result_text = (
        f"{saved_result['risk_level']} — "
        f"{saved_result['action_text']}"
    )


    if final_score <= 3:

        st.success(
            result_text
        )

    elif final_score <= 7:

        st.warning(
            result_text
        )

    else:

        st.error(
            result_text
        )


    st.write(
        f"**Action Level:** "
        f"{saved_result['action_level']}"
    )


    result_df = pd.DataFrame(
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
                saved_result[
                    "neck_score"
                ],

                saved_result[
                    "trunk_score"
                ],

                saved_result[
                    "legs_score"
                ],

                saved_result[
                    "load_score"
                ],

                saved_result[
                    "upper_arm_score"
                ],

                saved_result[
                    "lower_arm_score"
                ],

                saved_result[
                    "wrist_score"
                ],

                saved_result[
                    "coupling_score"
                ],

                saved_result[
                    "activity_score"
                ]
            ]
        }
    )


    st.dataframe(
        result_df,
        hide_index=True,
        width="stretch"
    )


    st.divider()


    # =====================================================
    # 8. Supabase 저장
    # =====================================================

    st.subheader(
        "7. 평가결과 저장"
    )


    if not worker:

        st.warning(
            "저장하려면 작업자/대상자를 입력해주세요."
        )


    if not task_name:

        st.warning(
            "저장하려면 작업명을 입력해주세요."
        )


    save_disabled = (
        not worker
        or not task_name
    )


    if st.button(
        "💾 REBA 평가결과 저장",
        type="primary",
        width="stretch",
        disabled=save_disabled
    ):

        try:

            pose_angles = (
                st.session_state.get(
                    "ai_pose_angles",
                    {}
                )
            )


            ai_recommendation = (
                st.session_state.get(
                    "ai_reba_recommendation",
                    {}
                )
            )


            insert_data = {

                "worker":
                    saved_result[
                        "worker"
                    ],

                "department":
                    saved_result[
                        "department"
                    ],

                "task_name":
                    saved_result[
                        "task_name"
                    ],

                "evaluator":
                    saved_result[
                        "evaluator"
                    ],

                "pose_angles":
                    pose_angles,

                "ai_recommendation":
                    ai_recommendation,

                "neck_score":
                    saved_result[
                        "neck_score"
                    ],

                "trunk_score":
                    saved_result[
                        "trunk_score"
                    ],

                "legs_score":
                    saved_result[
                        "legs_score"
                    ],

                "load_score":
                    saved_result[
                        "load_score"
                    ],

                "upper_arm_score":
                    saved_result[
                        "upper_arm_score"
                    ],

                "lower_arm_score":
                    saved_result[
                        "lower_arm_score"
                    ],

                "wrist_score":
                    saved_result[
                        "wrist_score"
                    ],

                "coupling_score":
                    saved_result[
                        "coupling_score"
                    ],

                "activity_score":
                    saved_result[
                        "activity_score"
                    ],

                "score_a":
                    saved_result[
                        "score_a"
                    ],

                "score_b":
                    saved_result[
                        "score_b"
                    ],

                "final_reba":
                    saved_result[
                        "final_reba"
                    ],

                "risk_level":
                    saved_result[
                        "risk_level"
                    ],

                "action_level":
                    saved_result[
                        "action_level"
                    ],

                "action_text":
                    saved_result[
                        "action_text"
                    ]
            }


            supabase.table(
                "reba_results"
            ).insert(
                insert_data
            ).execute()


            st.success(
                "✅ REBA 평가결과가 Supabase에 저장되었습니다."
            )


        except Exception as e:

            st.error(
                f"저장 중 오류가 발생했습니다: {e}"
            )


    st.caption(
        "AI 분석값과 최종 평가자가 선택한 REBA 점수를 "
        "함께 저장합니다."
    )

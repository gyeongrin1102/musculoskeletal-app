from pathlib import Path
from datetime import datetime

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
# 화면 설정
# =========================================================

st.title("🤖 AI 자세·REBA 평가")

logout_button()

st.write(
    "작업사진을 업로드하면 AI가 작업자의 자세를 인식하고 "
    "REBA 평가를 위한 관절각도와 점수 초안을 제안합니다."
)

st.info(
    "AI 분석결과는 평가 보조용입니다. "
    "최종 REBA 점수는 실제 작업조건을 확인한 평가자가 확정해주세요."
)

st.divider()


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
# Supabase Storage 사진 업로드
# =========================================================

def upload_reba_image(
    image_bytes,
    file_name,
    content_type
):

    bucket = (
        supabase
        .storage
        .from_("reba-images")
    )

    bucket.upload(
        path=file_name,
        file=image_bytes,
        file_options={
            "content-type": content_type,
            "upsert": "false"
        }
    )

    return file_name


# =========================================================
# 모델 경로
# =========================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "pose_landmarker.task"
)


if not MODEL_PATH.exists():

    st.error(
        "MediaPipe 모델파일을 찾을 수 없습니다.\n\n"
        f"{MODEL_PATH}"
    )

    st.stop()


# =========================================================
# MediaPipe 연결선
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

]


VISIBILITY_THRESHOLD = 0.35


# =========================================================
# 기본 함수
# =========================================================

def safe_int(
    value,
    default=0
):

    try:

        return int(
            value
        )

    except Exception:

        return default


def point_xy(
    landmark,
    width,
    height
):

    return np.array(
        [
            landmark.x * width,
            landmark.y * height
        ],
        dtype=np.float32
    )


def calculate_angle(
    point_a,
    point_b,
    point_c
):

    a = np.array(
        point_a,
        dtype=np.float32
    )

    b = np.array(
        point_b,
        dtype=np.float32
    )

    c = np.array(
        point_c,
        dtype=np.float32
    )


    ba = a - b

    bc = c - b


    denominator = (
        np.linalg.norm(ba)
        * np.linalg.norm(bc)
    )


    if denominator == 0:

        return 0.0


    cosine = np.dot(
        ba,
        bc
    ) / denominator


    cosine = np.clip(
        cosine,
        -1.0,
        1.0
    )


    angle = np.degrees(
        np.arccos(
            cosine
        )
    )


    return float(
        angle
    )


def midpoint(
    point_a,
    point_b
):

    return (
        np.array(point_a)
        + np.array(point_b)
    ) / 2


# =========================================================
# 관절각도 계산
# =========================================================

def get_pose_angles(
    landmarks,
    width,
    height
):

    pts = {}

    for index in [
        11, 12,
        13, 14,
        15, 16,
        23, 24,
        25, 26,
        27, 28
    ]:

        pts[index] = point_xy(
            landmarks[index],
            width,
            height
        )


    # 팔꿈치
    left_elbow = calculate_angle(
        pts[11],
        pts[13],
        pts[15]
    )

    right_elbow = calculate_angle(
        pts[12],
        pts[14],
        pts[16]
    )


    # 무릎
    left_knee = calculate_angle(
        pts[23],
        pts[25],
        pts[27]
    )

    right_knee = calculate_angle(
        pts[24],
        pts[26],
        pts[28]
    )


    # 위팔
    left_upper_arm = calculate_angle(
        pts[13],
        pts[11],
        pts[23]
    )

    right_upper_arm = calculate_angle(
        pts[14],
        pts[12],
        pts[24]
    )


    shoulder_mid = midpoint(
        pts[11],
        pts[12]
    )

    hip_mid = midpoint(
        pts[23],
        pts[24]
    )


    # 몸통의 수직선 대비 기울기
    dx = (
        shoulder_mid[0]
        - hip_mid[0]
    )

    dy = (
        hip_mid[1]
        - shoulder_mid[1]
    )


    trunk_angle = abs(
        np.degrees(
            np.arctan2(
                dx,
                dy
            )
        )
    )


    return {

        "left_elbow":
            round(
                left_elbow,
                1
            ),

        "right_elbow":
            round(
                right_elbow,
                1
            ),

        "left_knee":
            round(
                left_knee,
                1
            ),

        "right_knee":
            round(
                right_knee,
                1
            ),

        "left_upper_arm":
            round(
                left_upper_arm,
                1
            ),

        "right_upper_arm":
            round(
                right_upper_arm,
                1
            ),

        "trunk_angle":
            round(
                float(
                    trunk_angle
                ),
                1
            )
    }


# =========================================================
# AI 추천 REBA 점수
# =========================================================

def recommend_reba_from_angles(
    angles
):

    trunk_angle = (
        angles.get(
            "trunk_angle",
            0
        )
    )


    if trunk_angle <= 5:

        trunk_score = 1

    elif trunk_angle <= 20:

        trunk_score = 2

    elif trunk_angle <= 60:

        trunk_score = 3

    else:

        trunk_score = 4


    upper_angle = max(
        angles.get(
            "left_upper_arm",
            0
        ),
        angles.get(
            "right_upper_arm",
            0
        )
    )


    if upper_angle <= 20:

        upper_score = 1

    elif upper_angle <= 45:

        upper_score = 2

    elif upper_angle <= 90:

        upper_score = 3

    else:

        upper_score = 4


    left_elbow = angles.get(
        "left_elbow",
        90
    )

    right_elbow = angles.get(
        "right_elbow",
        90
    )


    if (
        60 <= left_elbow <= 100
        and
        60 <= right_elbow <= 100
    ):

        lower_score = 1

    else:

        lower_score = 2


    left_knee_flexion = max(
        0,
        180
        - angles.get(
            "left_knee",
            180
        )
    )

    right_knee_flexion = max(
        0,
        180
        - angles.get(
            "right_knee",
            180
        )
    )


    knee_flexion = max(
        left_knee_flexion,
        right_knee_flexion
    )


    if knee_flexion < 30:

        legs_score = 1

    elif knee_flexion <= 60:

        legs_score = 2

    else:

        legs_score = 3


    return {

        "trunk_score":
            trunk_score,

        "upper_arm_score":
            upper_score,

        "lower_arm_score":
            lower_score,

        "legs_score":
            legs_score
    }


# =========================================================
# AI 관절선 표시
# =========================================================

def draw_pose(
    image_rgb,
    landmarks
):

    output = (
        image_rgb.copy()
    )


    height, width = (
        output.shape[:2]
    )


    for start_idx, end_idx in (
        POSE_CONNECTIONS
    ):

        start = landmarks[
            start_idx
        ]

        end = landmarks[
            end_idx
        ]


        start_visibility = getattr(
            start,
            "visibility",
            1.0
        )

        end_visibility = getattr(
            end,
            "visibility",
            1.0
        )


        if (
            start_visibility
            < VISIBILITY_THRESHOLD
            or
            end_visibility
            < VISIBILITY_THRESHOLD
        ):

            continue


        start_point = (
            int(
                start.x
                * width
            ),
            int(
                start.y
                * height
            )
        )


        end_point = (
            int(
                end.x
                * width
            ),
            int(
                end.y
                * height
            )
        )


        cv2.line(
            output,
            start_point,
            end_point,
            (0, 220, 0),
            4
        )


    for index in [
        11, 12,
        13, 14,
        15, 16,
        23, 24,
        25, 26,
        27, 28
    ]:

        landmark = landmarks[
            index
        ]


        visibility = getattr(
            landmark,
            "visibility",
            1.0
        )


        if (
            visibility
            < VISIBILITY_THRESHOLD
        ):

            continue


        point = (
            int(
                landmark.x
                * width
            ),
            int(
                landmark.y
                * height
            )
        )


        cv2.circle(
            output,
            point,
            7,
            (0, 255, 0),
            -1
        )


    return output


# =========================================================
# MediaPipe 분석
# =========================================================

def analyze_pose(
    image_rgb
):

    try:

        base_options = (
            python.BaseOptions(
                model_asset_path=str(
                    MODEL_PATH
                )
            )
        )


        options = (
            vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=(
                    vision.RunningMode.IMAGE
                ),
                num_poses=1,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )
        )


        with vision.PoseLandmarker.create_from_options(
            options
        ) as landmarker:

            mp_image = mp.Image(
                image_format=(
                    mp.ImageFormat.SRGB
                ),
                data=image_rgb
            )


            result = (
                landmarker.detect(
                    mp_image
                )
            )


        if (
            not result.pose_landmarks
        ):

            return (
                None,
                "작업자의 전신 자세를 인식하지 못했습니다. "
                "가능하면 머리부터 발끝까지 보이는 사진을 사용해주세요."
            )


        return (
            result.pose_landmarks[0],
            None
        )


    except Exception as e:

        return (
            None,
            f"AI 자세 분석 오류: {e}"
        )


# =========================================================
# REBA TABLE A
# =========================================================

TABLE_A = {

    1: {
        1: [1, 2, 3, 4],
        2: [1, 2, 3, 4],
        3: [3, 3, 5, 6]
    },

    2: {
        1: [2, 3, 4, 5],
        2: [2, 3, 4, 5],
        3: [4, 4, 5, 6]
    },

    3: {
        1: [2, 4, 5, 6],
        2: [3, 4, 5, 6],
        3: [4, 5, 6, 7]
    },

    4: {
        1: [3, 5, 6, 7],
        2: [4, 5, 6, 7],
        3: [5, 6, 7, 8]
    },

    5: {
        1: [4, 6, 7, 8],
        2: [5, 6, 7, 8],
        3: [6, 7, 8, 9]
    }
}


# =========================================================
# REBA TABLE B
# =========================================================

TABLE_B = {

    1: {
        1: [1, 2, 2],
        2: [1, 2, 3]
    },

    2: {
        1: [1, 2, 3],
        2: [2, 3, 4]
    },

    3: {
        1: [3, 4, 5],
        2: [4, 5, 5]
    },

    4: {
        1: [4, 5, 5],
        2: [5, 6, 7]
    },

    5: {
        1: [6, 7, 8],
        2: [7, 8, 8]
    },

    6: {
        1: [7, 8, 8],
        2: [8, 9, 9]
    }
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

    [12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12]
]


# =========================================================
# REBA 계산
# =========================================================

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
        max(
            score_a,
            1
        ),
        12
    ) - 1


    b_index = min(
        max(
            score_b,
            1
        ),
        12
    ) - 1


    return TABLE_C[
        a_index
    ][
        b_index
    ]


def classify_reba(
    score
):

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
# 1. 기본정보
# =========================================================

st.subheader(
    "1. 평가 기본정보"
)


col1, col2 = st.columns(2)


with col1:

    worker = st.text_input(
        "작업자 또는 평가대상"
    )

    department = st.text_input(
        "공종 / 부서"
    )


with col2:

    task_name = st.text_input(
        "작업명"
    )

    evaluator = st.text_input(
        "평가자"
    )


st.divider()


# =========================================================
# 2. 사진 업로드
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


image_rgb = None


if uploaded_file is not None:

    uploaded_bytes = (
        uploaded_file.getvalue()
    )


    # 새 사진이 올라오면 이전 분석결과 제거
    upload_signature = (
        uploaded_file.name,
        len(uploaded_bytes)
    )


    if (
        st.session_state.get(
            "reba_upload_signature"
        )
        != upload_signature
    ):

        st.session_state[
            "reba_upload_signature"
        ] = upload_signature

        st.session_state.pop(
            "reba_analyzed_image_bytes",
            None
        )

        st.session_state.pop(
            "ai_pose_angles",
            None
        )

        st.session_state.pop(
            "ai_reba_recommendation",
            None
        )


    st.session_state[
        "reba_original_image_bytes"
    ] = uploaded_bytes


    st.session_state[
        "reba_original_content_type"
    ] = (
        uploaded_file.type
        or "image/jpeg"
    )


    st.session_state[
        "reba_original_filename"
    ] = uploaded_file.name


    file_bytes = np.asarray(
        bytearray(
            uploaded_bytes
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
            type="primary",
            width="stretch"
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

                analyzed_image = draw_pose(
                    image_rgb,
                    landmarks
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


                analyzed_bgr = cv2.cvtColor(
                    analyzed_image,
                    cv2.COLOR_RGB2BGR
                )


                success, encoded_image = (
                    cv2.imencode(
                        ".png",
                        analyzed_bgr
                    )
                )


                if success:

                    st.session_state[
                        "reba_analyzed_image_bytes"
                    ] = (
                        encoded_image.tobytes()
                    )


                st.session_state[
                    "ai_pose_angles"
                ] = angles


                st.session_state[
                    "ai_reba_recommendation"
                ] = recommendation


                st.session_state[
                    "reba_trunk"
                ] = recommendation[
                    "trunk_score"
                ]


                st.session_state[
                    "reba_upper_arm"
                ] = recommendation[
                    "upper_arm_score"
                ]


                st.session_state[
                    "reba_lower_arm"
                ] = recommendation[
                    "lower_arm_score"
                ]


                st.session_state[
                    "reba_legs"
                ] = recommendation[
                    "legs_score"
                ]


                st.success(
                    "작업자 자세를 인식했습니다."
                )


                st.rerun()


# =========================================================
# 저장된 AI 분석결과 표시
# =========================================================

analyzed_bytes = st.session_state.get(
    "reba_analyzed_image_bytes"
)


angles = st.session_state.get(
    "ai_pose_angles",
    {}
)


recommendation = st.session_state.get(
    "ai_reba_recommendation",
    {}
)


if analyzed_bytes:

    st.write(
        "#### AI 관절 인식 결과"
    )


    st.image(
        analyzed_bytes,
        width="stretch"
    )


if angles:

    st.write(
        "#### AI 관절각도"
    )


    angle_df = pd.DataFrame(
        [
            [
                "왼쪽 팔꿈치",
                angles.get(
                    "left_elbow",
                    ""
                )
            ],

            [
                "오른쪽 팔꿈치",
                angles.get(
                    "right_elbow",
                    ""
                )
            ],

            [
                "왼쪽 무릎",
                angles.get(
                    "left_knee",
                    ""
                )
            ],

            [
                "오른쪽 무릎",
                angles.get(
                    "right_knee",
                    ""
                )
            ],

            [
                "왼쪽 위팔",
                angles.get(
                    "left_upper_arm",
                    ""
                )
            ],

            [
                "오른쪽 위팔",
                angles.get(
                    "right_upper_arm",
                    ""
                )
            ],

            [
                "몸통 기울기",
                angles.get(
                    "trunk_angle",
                    ""
                )
            ]
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


if recommendation:

    st.write(
        "#### AI REBA 추천 초안"
    )


    rec_df = pd.DataFrame(
        [
            [
                "몸통",
                recommendation.get(
                    "trunk_score"
                )
            ],

            [
                "다리",
                recommendation.get(
                    "legs_score"
                )
            ],

            [
                "위팔",
                recommendation.get(
                    "upper_arm_score"
                )
            ],

            [
                "아래팔",
                recommendation.get(
                    "lower_arm_score"
                )
            ]
        ],
        columns=[
            "항목",
            "AI 추천점수"
        ]
    )


    st.dataframe(
        rec_df,
        hide_index=True,
        width="stretch"
    )


st.divider()


# =========================================================
# 3. REBA 세부평가
# =========================================================

st.subheader(
    "3. REBA 세부평가"
)


st.caption(
    "AI 추천점수는 초안입니다. "
    "목, 손목, 하중, 결합도, 활동점수와 "
    "비틀림·측굴·지지상태 등은 실제 작업을 확인하여 평가자가 조정해주세요."
)


c1, c2, c3 = st.columns(3)


with c1:

    neck_score = st.selectbox(
        "목(Neck)",
        [1, 2, 3],
        key="reba_neck"
    )


    trunk_score = st.selectbox(
        "몸통(Trunk)",
        [1, 2, 3, 4, 5],
        key="reba_trunk"
    )


    legs_score = st.selectbox(
        "다리(Legs)",
        [1, 2, 3, 4],
        key="reba_legs"
    )


with c2:

    upper_arm_score = st.selectbox(
        "위팔(Upper Arm)",
        [1, 2, 3, 4, 5, 6],
        key="reba_upper_arm"
    )


    lower_arm_score = st.selectbox(
        "아래팔(Lower Arm)",
        [1, 2],
        key="reba_lower_arm"
    )


    wrist_score = st.selectbox(
        "손목(Wrist)",
        [1, 2, 3],
        key="reba_wrist"
    )


with c3:

    load_score = st.selectbox(
        "하중/힘(Load)",
        [0, 1, 2, 3],
        key="reba_load"
    )


    coupling_score = st.selectbox(
        "결합도(Coupling)",
        [0, 1, 2, 3],
        key="reba_coupling"
    )


    activity_score = st.selectbox(
        "활동점수(Activity)",
        [0, 1, 2, 3],
        key="reba_activity"
    )


# =========================================================
# REBA 계산
# =========================================================

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


table_c_score = get_table_c_score(
    score_a,
    score_b
)


final_reba = min(
    table_c_score
    + activity_score,
    15
)


risk_level, action_level, action_text = (
    classify_reba(
        final_reba
    )
)


st.divider()


# =========================================================
# 4. 결과
# =========================================================

st.subheader(
    "4. REBA 평가결과"
)


r1, r2, r3, r4 = st.columns(4)


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
    f"**조치수준:** {action_level}"
)

st.write(
    f"**조치권고:** {action_text}"
)


saved_result = {

    "worker":
        worker,

    "department":
        department,

    "task_name":
        task_name,

    "evaluator":
        evaluator,

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

    "table_c_score":
        table_c_score,

    "final_reba":
        final_reba,

    "risk_level":
        risk_level,

    "action_level":
        action_level,

    "action_text":
        action_text
}


st.session_state[
    "latest_reba_result"
] = saved_result


st.divider()


# =========================================================
# 5. 결과 저장
# =========================================================

st.subheader(
    "5. REBA 평가결과 저장"
)


save_disabled = (
    not worker.strip()
    or
    not task_name.strip()
)


if save_disabled:

    st.warning(
        "저장하려면 작업자 또는 평가대상과 작업명을 입력해주세요."
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


        # =====================================================
        # 사진 Storage 업로드
        # =====================================================

        timestamp = (
            datetime.now()
            .strftime(
                "%Y%m%d_%H%M%S_%f"
            )
        )


        original_image_path = None

        analyzed_image_path = None


        # -----------------------------------------------------
        # 원본사진 업로드
        # -----------------------------------------------------

        original_bytes = (
            st.session_state.get(
                "reba_original_image_bytes"
            )
        )


        original_content_type = (
            st.session_state.get(
                "reba_original_content_type",
                "image/jpeg"
            )
        )


        original_filename = (
            st.session_state.get(
                "reba_original_filename",
                "original.jpg"
            )
        )


        if original_bytes:

            extension = (
                original_filename
                .split(".")[-1]
                .lower()
            )


            if extension not in [
                "jpg",
                "jpeg",
                "png"
            ]:

                extension = "jpg"


            original_image_path = (
                f"{timestamp}/"
                f"original.{extension}"
            )


            upload_reba_image(
                original_bytes,
                original_image_path,
                original_content_type
            )


        # -----------------------------------------------------
        # AI 분석사진 업로드
        # -----------------------------------------------------

        analyzed_image_bytes = (
            st.session_state.get(
                "reba_analyzed_image_bytes"
            )
        )


        if analyzed_image_bytes:

            analyzed_image_path = (
                f"{timestamp}/"
                "analyzed.png"
            )


            upload_reba_image(
                analyzed_image_bytes,
                analyzed_image_path,
                "image/png"
            )


        # =====================================================
        # DB 저장
        # =====================================================

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
                ],

            "original_image_path":
                original_image_path,

            "analyzed_image_path":
                analyzed_image_path,
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


        st.success(
            "✅ REBA 평가결과와 작업사진이 저장되었습니다."
        )


    except Exception as e:

        st.error(
            f"REBA 평가결과 저장 오류: {e}"
        )

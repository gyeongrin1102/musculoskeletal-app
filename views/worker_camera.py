from pathlib import Path
from datetime import datetime
import hashlib

import cv2
import numpy as np
import streamlit as st
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from supabase import create_client
from session_query_cache import clear_session_query_cache


st.title("작업자세 촬영")
st.caption("업체와 작업 정보를 입력한 뒤 촬영하세요. 사진은 AI 초안과 함께 관리자 검토 대기함에 저장됩니다.")

st.divider()


@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


supabase = get_supabase()


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "pose_landmarker.task"
)

if not MODEL_PATH.exists():
    st.error(
        "AI 자세분석 모델을 찾을 수 없습니다. "
        "관리자에게 문의해주세요."
    )
    st.stop()


def upload_image(image_bytes, path, content_type):
    (
        supabase
        .storage
        .from_("reba-images")
        .upload(
            path=path,
            file=image_bytes,
            file_options={
                "content-type": content_type,
                "upsert": "false"
            }
        )
    )
    return path


def start_new_capture():
    st.session_state["worker_capture_revision"] = (
        st.session_state.get("worker_capture_revision", 0) + 1
    )
    for key in (
        "worker_capture_last_original",
        "worker_capture_last_analyzed",
        "worker_capture_last_angles",
        "worker_capture_last_recommendation",
    ):
        st.session_state.pop(key, None)


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


def point_xy(landmark, width, height):
    return np.array(
        [
            landmark.x * width,
            landmark.y * height
        ],
        dtype=np.float32
    )


def calculate_angle(point_a, point_b, point_c):
    a = np.array(point_a, dtype=np.float32)
    b = np.array(point_b, dtype=np.float32)
    c = np.array(point_c, dtype=np.float32)

    ba = a - b
    bc = c - b

    denominator = np.linalg.norm(ba) * np.linalg.norm(bc)

    if denominator == 0:
        return 0.0

    cosine = np.dot(ba, bc) / denominator
    cosine = np.clip(cosine, -1.0, 1.0)

    return float(np.degrees(np.arccos(cosine)))


def midpoint(point_a, point_b):
    return (
        np.array(point_a)
        + np.array(point_b)
    ) / 2


def get_pose_angles(landmarks, width, height):
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

    left_elbow = calculate_angle(pts[11], pts[13], pts[15])
    right_elbow = calculate_angle(pts[12], pts[14], pts[16])
    left_knee = calculate_angle(pts[23], pts[25], pts[27])
    right_knee = calculate_angle(pts[24], pts[26], pts[28])
    left_upper_arm = calculate_angle(pts[13], pts[11], pts[23])
    right_upper_arm = calculate_angle(pts[14], pts[12], pts[24])

    shoulder_mid = midpoint(pts[11], pts[12])
    hip_mid = midpoint(pts[23], pts[24])

    dx = shoulder_mid[0] - hip_mid[0]
    dy = hip_mid[1] - shoulder_mid[1]

    trunk_angle = abs(
        np.degrees(
            np.arctan2(dx, dy)
        )
    )

    return {
        "left_elbow": round(left_elbow, 1),
        "right_elbow": round(right_elbow, 1),
        "left_knee": round(left_knee, 1),
        "right_knee": round(right_knee, 1),
        "left_upper_arm": round(left_upper_arm, 1),
        "right_upper_arm": round(right_upper_arm, 1),
        "trunk_angle": round(float(trunk_angle), 1),
    }


def recommend_reba_from_angles(angles):
    trunk_angle = angles.get("trunk_angle", 0)

    if trunk_angle <= 5:
        trunk_score = 1
    elif trunk_angle <= 20:
        trunk_score = 2
    elif trunk_angle <= 60:
        trunk_score = 3
    else:
        trunk_score = 4

    upper_angle = max(
        angles.get("left_upper_arm", 0),
        angles.get("right_upper_arm", 0)
    )

    if upper_angle <= 20:
        upper_score = 1
    elif upper_angle <= 45:
        upper_score = 2
    elif upper_angle <= 90:
        upper_score = 3
    else:
        upper_score = 4

    left_elbow = angles.get("left_elbow", 90)
    right_elbow = angles.get("right_elbow", 90)

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
        180 - angles.get("left_knee", 180)
    )

    right_knee_flexion = max(
        0,
        180 - angles.get("right_knee", 180)
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
        "trunk_score": trunk_score,
        "upper_arm_score": upper_score,
        "lower_arm_score": lower_score,
        "legs_score": legs_score,
    }


def draw_pose(image_rgb, landmarks):
    output = image_rgb.copy()
    height, width = output.shape[:2]

    for start_idx, end_idx in POSE_CONNECTIONS:
        start = landmarks[start_idx]
        end = landmarks[end_idx]

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
            start_visibility < VISIBILITY_THRESHOLD
            or
            end_visibility < VISIBILITY_THRESHOLD
        ):
            continue

        start_point = (
            int(start.x * width),
            int(start.y * height)
        )

        end_point = (
            int(end.x * width),
            int(end.y * height)
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
        landmark = landmarks[index]

        visibility = getattr(
            landmark,
            "visibility",
            1.0
        )

        if visibility < VISIBILITY_THRESHOLD:
            continue

        point = (
            int(landmark.x * width),
            int(landmark.y * height)
        )

        cv2.circle(
            output,
            point,
            7,
            (0, 255, 0),
            -1
        )

    return output


def analyze_pose(image_rgb):
    try:
        base_options = python.BaseOptions(
            model_asset_path=str(MODEL_PATH)
        )

        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )

        with vision.PoseLandmarker.create_from_options(
            options
        ) as landmarker:
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=image_rgb
            )

            result = landmarker.detect(mp_image)

        if not result.pose_landmarks:
            return (
                None,
                "작업자의 전신 자세를 인식하지 못했습니다. "
                "머리부터 발끝까지 보이도록 다시 촬영해주세요."
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


st.subheader("1. 작업정보")

company = st.text_input(
    "업체명",
    placeholder="예: ○○건설"
)

department = st.text_input(
    "공종 / 부서",
    placeholder="예: 철근팀"
)

task_name = st.text_input(
    "작업명",
    placeholder="예: 철근 결속"
)

worker = st.text_input(
    "근로자 이름 또는 식별명",
    placeholder="선택사항"
)

st.divider()


st.subheader("2. 작업사진")

st.caption(
    "가능하면 작업자의 머리부터 발끝까지 한 화면에 나오게 촬영해주세요."
)

photo = st.camera_input(
    "📷 작업자세 촬영",
    key=f"worker_camera_{st.session_state.get('worker_capture_revision', 0)}"
)


if photo is not None:
    if (
        not company.strip()
        or
        not task_name.strip()
    ):
        st.warning(
            "업체명과 작업명을 먼저 입력해주세요."
        )
        st.stop()

    original_bytes = photo.getvalue()

    signature_source = (
        original_bytes
        + company.encode("utf-8")
        + department.encode("utf-8")
        + task_name.encode("utf-8")
        + worker.encode("utf-8")
    )

    signature = hashlib.sha256(
        signature_source
    ).hexdigest()

    saved_signature = st.session_state.get(
        "worker_capture_saved_signature"
    )

    if signature != saved_signature:
        with st.spinner(
            "AI 자세분석 후 자동 저장하고 있습니다..."
        ):
            try:
                file_bytes = np.asarray(
                    bytearray(original_bytes),
                    dtype=np.uint8
                )

                image_bgr = cv2.imdecode(
                    file_bytes,
                    cv2.IMREAD_COLOR
                )

                if image_bgr is None:
                    st.error(
                        "촬영한 이미지를 읽을 수 없습니다."
                    )
                    st.stop()

                image_rgb = cv2.cvtColor(
                    image_bgr,
                    cv2.COLOR_BGR2RGB
                )

                landmarks, error = analyze_pose(
                    image_rgb
                )

                if error:
                    st.error(error)
                    st.stop()

                analyzed_image = draw_pose(
                    image_rgb,
                    landmarks
                )

                height, width = image_rgb.shape[:2]

                angles = get_pose_angles(
                    landmarks,
                    width,
                    height
                )

                recommendation = recommend_reba_from_angles(
                    angles
                )

                analyzed_bgr = cv2.cvtColor(
                    analyzed_image,
                    cv2.COLOR_RGB2BGR
                )

                success, encoded_image = cv2.imencode(
                    ".png",
                    analyzed_bgr
                )

                if not success:
                    st.error(
                        "AI 분석사진 생성에 실패했습니다."
                    )
                    st.stop()

                analyzed_bytes = encoded_image.tobytes()

                timestamp = datetime.now().strftime(
                    "%Y%m%d_%H%M%S_%f"
                )

                folder = (
                    f"worker-captures/"
                    f"{timestamp}"
                )

                original_path = (
                    f"{folder}/original.jpg"
                )

                analyzed_path = (
                    f"{folder}/analyzed.png"
                )

                upload_image(
                    original_bytes,
                    original_path,
                    "image/jpeg"
                )

                upload_image(
                    analyzed_bytes,
                    analyzed_path,
                    "image/png"
                )

                insert_data = {
                    "company": company,
                    "worker": worker,
                    "department": department,
                    "task_name": task_name,
                    "original_image_path": original_path,
                    "analyzed_image_path": analyzed_path,
                    "pose_angles": angles,
                    "ai_recommendation": recommendation,
                    "status": "대기",
                }

                (
                    supabase
                    .table("reba_capture_queue")
                    .insert(insert_data)
                    .execute()
                )
                clear_session_query_cache()

                st.session_state[
                    "worker_capture_saved_signature"
                ] = signature

                st.session_state[
                    "worker_capture_last_original"
                ] = original_bytes

                st.session_state[
                    "worker_capture_last_analyzed"
                ] = analyzed_bytes

                st.session_state[
                    "worker_capture_last_angles"
                ] = angles

                st.session_state[
                    "worker_capture_last_recommendation"
                ] = recommendation

                st.success(
                    "✅ 촬영이 완료되었고 자동 저장되었습니다."
                )

            except Exception as e:
                st.error(
                    f"자동 저장 오류: {e}"
                )

    else:
        st.success(
            "✅ 이 사진은 이미 저장되었습니다."
        )


last_original = st.session_state.get(
    "worker_capture_last_original"
)

last_analyzed = st.session_state.get(
    "worker_capture_last_analyzed"
)

last_recommendation = st.session_state.get(
    "worker_capture_last_recommendation",
    {}
)

if last_original:
    st.divider()

    st.subheader("3. 촬영 결과")

    c1, c2 = st.columns(2)

    with c1:
        st.image(
            last_original,
            caption="원본 작업사진",
            width="stretch"
        )

    with c2:
        if last_analyzed:
            st.image(
                last_analyzed,
                caption="AI 관절선 분석사진",
                width="stretch"
            )

    if last_recommendation:
        st.write("#### AI 자세분석 초안")

        st.write(
            f"- 몸통 추천점수: "
            f"{last_recommendation.get('trunk_score', '-')}"
        )

        st.write(
            f"- 다리 추천점수: "
            f"{last_recommendation.get('legs_score', '-')}"
        )

        st.write(
            f"- 위팔 추천점수: "
            f"{last_recommendation.get('upper_arm_score', '-')}"
        )

        st.write(
            f"- 아래팔 추천점수: "
            f"{last_recommendation.get('lower_arm_score', '-')}"
        )

    st.info(
        "최종 REBA 평가는 관리자가 목·손목·하중·결합도·활동점수 등 "
        "실제 작업조건을 확인한 후 확정합니다."
    )

    st.button(
        "재촬영",
        on_click=start_new_capture,
        width="stretch"
    )


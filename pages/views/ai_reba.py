from pathlib import Path
from datetime import datetime
import hashlib
import copy

import cv2
import numpy as np
import pandas as pd
import streamlit as st
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from auth import require_admin, logout_button, get_authenticated_supabase
from session_query_cache import clear_session_query_cache
from ui_theme import apply_theme

from joint_drag_editor import joint_drag_editor

require_admin()
apply_theme()

st.title("AI 자세·REBA 평가")
logout_button()
st.caption("작업 사진과 AI 분석을 확인한 뒤 평가자가 REBA 점수를 확정합니다.")
st.divider()

supabase = get_authenticated_supabase()
# 임시 진단: 인증 토큰 값은 표시하지 않음
from auth import ACCESS_TOKEN_KEY

session_token = st.session_state.get(ACCESS_TOKEN_KEY, "")
storage_client = getattr(supabase.storage, "_client", None)
client_headers = getattr(storage_client, "headers", {}) or {}

authorization = client_headers.get("Authorization", "")

st.caption(
    "Storage 인증 확인: "
    + (
        "관리자 토큰 사용"
        if session_token and authorization == f"Bearer {session_token}"
        else "인증 헤더 확인 필요"
    )
)

def upload_reba_image(image_bytes, file_name, content_type):
    bucket = supabase.storage.from_("reba-images")
    bucket.upload(
        path=file_name,
        file=image_bytes,
        file_options={
            "content-type": content_type,
            "upsert": "false"
        }
    )
    return file_name


def download_storage_file(path):
    if not path:
        return None
    try:
        data = supabase.storage.from_("reba-images").download(path)
        if isinstance(data, bytes):
            return data
        if hasattr(data, "content"):
            return data.content
        return bytes(data)
    except Exception:
        return None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "pose_landmarker.task"

if not MODEL_PATH.exists():
    st.error(f"MediaPipe 모델파일을 찾을 수 없습니다.\n\n{MODEL_PATH}")
    st.stop()

POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
    (24, 26), (26, 28),
]
VISIBILITY_THRESHOLD = 0.35


def point_xy(landmark, width, height):
    return np.array([landmark.x * width, landmark.y * height], dtype=np.float32)


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
    return (np.array(point_a) + np.array(point_b)) / 2


def image_signature(image_bytes):
    return hashlib.sha256(image_bytes).hexdigest()


def submission_signature(image_bytes, values):
    payload = "\x1f".join(str(value) for value in values)
    return hashlib.sha256(
        image_bytes + payload.encode("utf-8")
    ).hexdigest()


def resolve_company(row):
    company = row.get("company") or row.get("company_name")
    if company:
        return str(company).strip()
    department = str(row.get("department") or "").strip()
    return department.split(" / ", 1)[0].strip() if " / " in department else ""


def resolve_department(row):
    department = str(row.get("department") or "").strip()
    if " / " in department:
        return department.split(" / ", 1)[1].strip()
    return department


def reset_new_capture():
    st.session_state["new_capture_revision"] = st.session_state.get("new_capture_revision", 0) + 1
    for key in (
        "new_reba_signature", "new_reba_original_bytes",
        "new_reba_analyzed_bytes", "new_reba_angles",
        "new_reba_recommendation", "new_reba_error",
        "new_saving_signature", "new_trunk", "new_legs",
        "new_upper_arm", "new_lower_arm",
    ):
        st.session_state.pop(key, None)


def cancel_new_evaluation():
    reset_new_capture()
    for key in (
        "new_worker", "new_company_choice", "new_company_custom",
        "new_department_choice", "new_department_custom",
        "new_task_choice", "new_task_custom", "new_evaluator",
        "new_neck", "new_trunk", "new_legs", "new_upper_arm",
        "new_lower_arm", "new_wrist", "new_load", "new_coupling",
        "new_activity",
    ):
        st.session_state.pop(key, None)


def decode_image(image_bytes):
    file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
    image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image_bgr is None:
        return None
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

def display_photo(image_bytes, caption):
    """화면 표시용으로만 사진 축소"""
    try:
        image = decode_image(image_bytes)
        if image is None:
            st.warning(f"{caption}: 이미지를 읽을 수 없습니다.")
            return

        height, width = image.shape[:2]
        max_width = 1200

        if width > max_width:
            scale = max_width / width
            image = cv2.resize(
                image,
                (max_width, max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )

        st.image(image, caption=caption, width="stretch")

    except Exception as e:
        st.error(f"사진 표시 오류: {e}")

def get_pose_angles(landmarks, width, height):
    pts = {}
    for index in [11,12,13,14,15,16,23,24,25,26,27,28]:
        pts[index] = point_xy(landmarks[index], width, height)

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
    trunk_angle = abs(np.degrees(np.arctan2(dx, dy)))

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
    lower_score = 1 if (60 <= left_elbow <= 100 and 60 <= right_elbow <= 100) else 2

    left_knee_flexion = max(0, 180 - angles.get("left_knee", 180))
    right_knee_flexion = max(0, 180 - angles.get("right_knee", 180))
    knee_flexion = max(left_knee_flexion, right_knee_flexion)
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
        start_visibility = getattr(start, "visibility", 1.0)
        end_visibility = getattr(end, "visibility", 1.0)
        if start_visibility < VISIBILITY_THRESHOLD or end_visibility < VISIBILITY_THRESHOLD:
            continue
        start_point = (int(start.x * width), int(start.y * height))
        end_point = (int(end.x * width), int(end.y * height))
        cv2.line(output, start_point, end_point, (0, 220, 0), 4)

    for index in [11,12,13,14,15,16,23,24,25,26,27,28]:
        landmark = landmarks[index]
        visibility = getattr(landmark, "visibility", 1.0)
        if visibility < VISIBILITY_THRESHOLD:
            continue
        point = (int(landmark.x * width), int(landmark.y * height))
        cv2.circle(output, point, 7, (0, 255, 0), -1)

    return output


def analyze_pose(image_rgb):
    try:
        base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        with vision.PoseLandmarker.create_from_options(options) as landmarker:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
            result = landmarker.detect(mp_image)

        if not result.pose_landmarks:
            return None, "작업자의 전신 자세를 인식하지 못했습니다. 가능하면 머리부터 발끝까지 보이는 사진을 사용해주세요."
        return result.pose_landmarks[0], None
    except Exception as e:
        return None, f"AI 자세 분석 오류: {e}"


def auto_analyze_image(image_bytes, state_prefix):
    signature = image_signature(image_bytes)
    signature_key = f"{state_prefix}_signature"

    if st.session_state.get(signature_key) != signature:
        st.session_state.pop(f"{state_prefix}_landmarks", None)

    if (
        st.session_state.get(signature_key) == signature
        and st.session_state.get(f"{state_prefix}_analyzed_bytes")
    ):
        return

    image_rgb = decode_image(image_bytes)
    if image_rgb is None:
        st.session_state[f"{state_prefix}_error"] = "이미지 파일을 읽을 수 없습니다."
        return

    landmarks, error = analyze_pose(image_rgb)
    if error:
        st.session_state[f"{state_prefix}_error"] = error
        st.session_state[signature_key] = signature
        return

    st.session_state[f"{state_prefix}_landmarks"] = copy.deepcopy(landmarks)


    analyzed_image = draw_pose(image_rgb, landmarks)
    height, width = image_rgb.shape[:2]
    angles = get_pose_angles(landmarks, width, height)
    recommendation = recommend_reba_from_angles(angles)
    analyzed_bgr = cv2.cvtColor(analyzed_image, cv2.COLOR_RGB2BGR)
    success, encoded_image = cv2.imencode(".png", analyzed_bgr)
    if not success:
        st.session_state[f"{state_prefix}_error"] = "AI 분석사진 변환에 실패했습니다."
        return

    st.session_state[signature_key] = signature
    st.session_state[f"{state_prefix}_original_bytes"] = image_bytes
    st.session_state[f"{state_prefix}_analyzed_bytes"] = encoded_image.tobytes()
    st.session_state[f"{state_prefix}_angles"] = angles
    st.session_state[f"{state_prefix}_recommendation"] = recommendation
    st.session_state.pop(f"{state_prefix}_error", None)


TABLE_A = {
    1:{1:[1,2,3,4],2:[1,2,3,4],3:[3,3,5,6]},
    2:{1:[2,3,4,5],2:[2,3,4,5],3:[4,4,5,6]},
    3:{1:[2,4,5,6],2:[3,4,5,6],3:[4,5,6,7]},
    4:{1:[3,5,6,7],2:[4,5,6,7],3:[5,6,7,8]},
    5:{1:[4,6,7,8],2:[5,6,7,8],3:[6,7,8,9]},
}
TABLE_B = {
    1:{1:[1,2,2],2:[1,2,3]},
    2:{1:[1,2,3],2:[2,3,4]},
    3:{1:[3,4,5],2:[4,5,5]},
    4:{1:[4,5,5],2:[5,6,7]},
    5:{1:[6,7,8],2:[7,8,8]},
    6:{1:[7,8,8],2:[8,9,9]},
}
TABLE_C = [
    [1,1,1,2,3,3,4,5,6,7,7,7],
    [1,2,2,3,4,4,5,6,6,7,7,8],
    [2,3,3,3,4,5,6,7,7,8,8,8],
    [3,4,4,4,5,6,7,8,8,9,9,9],
    [4,4,4,5,6,7,8,8,9,9,9,9],
    [6,6,6,7,8,8,9,9,10,10,10,10],
    [7,7,7,8,9,9,9,10,10,11,11,11],
    [8,8,8,9,10,10,10,10,10,11,11,11],
    [9,9,9,10,10,10,11,11,11,12,12,12],
    [10,10,10,11,11,11,11,12,12,12,12,12],
    [11,11,11,11,12,12,12,12,12,12,12,12],
    [12,12,12,12,12,12,12,12,12,12,12,12],
]


def get_score_a(trunk_score, neck_score, legs_score, load_score):
    base_score = TABLE_A[trunk_score][neck_score][legs_score - 1]
    return min(base_score + load_score, 12)


def get_score_b(upper_arm_score, lower_arm_score, wrist_score, coupling_score):
    base_score = TABLE_B[upper_arm_score][lower_arm_score][wrist_score - 1]
    return min(base_score + coupling_score, 12)


def get_table_c_score(score_a, score_b):
    a_index = min(max(score_a, 1), 12) - 1
    b_index = min(max(score_b, 1), 12) - 1
    return TABLE_C[a_index][b_index]


def classify_reba(score):
    if score <= 1:
        return "무시 가능 (Negligible)", 0, "개선 불필요"
    elif score <= 3:
        return "낮음 (Low)", 1, "개선 필요 가능성 있음"
    elif score <= 7:
        return "보통 (Medium)", 2, "개선 필요"
    elif score <= 10:
        return "높음 (High)", 3, "빠른 시일 내 개선 필요"
    else:
        return "매우 높음 (Very High)", 4, "즉각적 조치 필요"


def load_reba_results():
    try:
        response = (
            supabase
            .table("reba_results")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        st.error(f"기존 REBA 결과 조회 오류: {e}")
        return []


mode = st.radio(
    "작업할 기능을 선택하세요.",
    ["📷 새 REBA 평가", "🖼️ 기존 REBA 평가에 사진만 연결"],
    horizontal=True
)
st.divider()


if mode == "📷 새 REBA 평가":
    st.subheader("1. 평가 기본정보")

    previous_rows = load_reba_results()
    company_options = sorted({
        resolve_company(row)
        for row in previous_rows
        if resolve_company(row)
    })

    company_choice = st.selectbox(
        "업체 빠른 선택",
        ["직접 입력"] + company_options,
        key="new_company_choice"
    )
    if company_choice == "직접 입력":
        company = st.text_input("업체명", placeholder="예: ○○건설", key="new_company_custom")
    else:
        company = company_choice

    department_options = sorted({
        resolve_department(row)
        for row in previous_rows
        if resolve_department(row)
        and (not company or resolve_company(row) == company)
    })
    department_choice = st.selectbox(
        "공종 빠른 선택",
        ["직접 입력"] + department_options,
        key="new_department_choice"
    )
    if department_choice == "직접 입력":
        department = st.text_input("공종 / 부서", placeholder="예: 철근팀", key="new_department_custom")
    else:
        department = department_choice

    task_options = sorted({
        str(row.get("task_name")).strip()
        for row in previous_rows
        if row.get("task_name")
        and (not company or resolve_company(row) == company)
        and (not department or resolve_department(row) == department)
    })
    task_choice = st.selectbox(
        "작업명 빠른 선택",
        ["직접 입력"] + task_options,
        key="new_task_choice"
    )
    if task_choice == "직접 입력":
        task_name = st.text_input("작업명", placeholder="예: 철근 결속", key="new_task_custom")
    else:
        task_name = task_choice

    col1, col2 = st.columns(2)
    with col1:
        worker = st.text_input("작업자 또는 평가대상", key="new_worker")
    with col2:
        evaluator = st.text_input("평가자", key="new_evaluator")

    st.divider()
    st.subheader("2. 현장사진 촬영")

    source = st.radio(
        "사진 입력방법",
        ["📷 스마트폰 촬영", "🖼️ 사진 업로드"],
        horizontal=True,
        key="new_source"
    )

    capture_revision = st.session_state.get("new_capture_revision", 0)
    if source == "📷 스마트폰 촬영":
        photo = st.camera_input(
            "작업자 전신이 보이도록 촬영해주세요.",
            key=f"new_camera_{capture_revision}"
        )
    else:
        photo = st.file_uploader(
            "작업사진을 선택하세요.",
            type=["jpg", "jpeg", "png"],
            key=f"new_upload_{capture_revision}"
        )

    if photo is not None:
        image_bytes = photo.getvalue()
        display_photo(image_bytes, "촬영/업로드 사진")

        with st.spinner("AI가 자세를 자동 분석하고 있습니다..."):
            auto_analyze_image(image_bytes, "new_reba")

        error = st.session_state.get("new_reba_error")
        if error:
            st.error(error)

        analyzed_bytes = st.session_state.get("new_reba_analyzed_bytes")
        angles = st.session_state.get("new_reba_angles", {})
        recommendation = st.session_state.get("new_reba_recommendation", {})

        if analyzed_bytes:
            st.success("AI 자세분석이 완료되었습니다.")
            display_photo(analyzed_bytes, "AI 관절선 분석사진")
        if analyzed_bytes and st.session_state.get("new_reba_landmarks"):
            with st.expander("✏️ 사진에서 관절점 직접 이동", expanded=False):
                st.caption(
                    "초록색 관절점을 잡아서 실제 관절 위치로 옮긴 뒤 "
                    "'보정 적용'을 누르세요. 최종 REBA 점수는 자동 변경되지 않습니다."
                )

                current_landmarks = st.session_state["new_reba_landmarks"]
                joint_indices = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

                joint_points = [
                    {
                        "id": idx,
                        "x": float(current_landmarks[idx].x),
                        "y": float(current_landmarks[idx].y),
                    }
                    for idx in joint_indices
                ]

                correction = joint_drag_editor(
                    st.session_state["new_reba_original_bytes"],
                    joint_points,
                    key=f"joint_drag_{image_signature(image_bytes)}",
                )

                if isinstance(correction, dict) and correction.get("action") == "apply":
                    revision = str(correction.get("revision", ""))
                    revision_key = "new_reba_drag_revision"

                    if revision and st.session_state.get(revision_key) != revision:
                        st.session_state[revision_key] = revision

                        points_by_id = {
                            int(p["id"]): p
                            for p in correction.get("points", [])
                            if isinstance(p, dict)
                            and all(k in p for k in ("id", "x", "y"))
                        }

                        if set(joint_indices).issubset(points_by_id):
                            corrected = copy.deepcopy(current_landmarks)

                            for idx in joint_indices:
                                p = points_by_id[idx]
                                corrected[idx].x = max(0.0, min(1.0, float(p["x"])))
                                corrected[idx].y = max(0.0, min(1.0, float(p["y"])))
                                corrected[idx].visibility = 1.0

                            original_rgb = decode_image(
                                st.session_state["new_reba_original_bytes"]
                            )

                            if original_rgb is not None:
                                output = draw_pose(original_rgb, corrected)
                                output_bgr = cv2.cvtColor(
                                    output, cv2.COLOR_RGB2BGR
                                )
                                ok, encoded = cv2.imencode(".png", output_bgr)

                                if ok:
                                    height, width = original_rgb.shape[:2]
                                    corrected_angles = get_pose_angles(
                                        corrected, width, height
                                    )

                                    st.session_state["new_reba_landmarks"] = corrected
                                    st.session_state["new_reba_analyzed_bytes"] = (
                                        encoded.tobytes()
                                    )
                                    st.session_state["new_reba_angles"] = (
                                        corrected_angles
                                    )
                                    st.session_state["new_reba_recommendation"] = (
                                        recommend_reba_from_angles(corrected_angles)
                                    )
                                    st.rerun()
                                else:
                                    st.error("보정 사진 생성에 실패했습니다.")
                            else:
                                st.error("원본사진을 불러오지 못했습니다.")
                        else:
                            st.error("관절 좌표가 불완전하여 보정하지 않았습니다.")

        if angles or recommendation:
            with st.expander("AI 분석 참고값", expanded=bool(recommendation)):
                st.caption("AI 결과는 참고용이며, 최종 점수는 아래 평가 항목에서 평가자가 확인·수정합니다.")
                if angles:
                    angle_df = pd.DataFrame(
                        [
                            ["왼쪽 팔꿈치", angles.get("left_elbow", "")],
                            ["오른쪽 팔꿈치", angles.get("right_elbow", "")],
                            ["왼쪽 무릎", angles.get("left_knee", "")],
                            ["오른쪽 무릎", angles.get("right_knee", "")],
                            ["왼쪽 위팔", angles.get("left_upper_arm", "")],
                            ["오른쪽 위팔", angles.get("right_upper_arm", "")],
                            ["몸통 기울기", angles.get("trunk_angle", "")],
                        ],
                        columns=["관절/부위", "각도(°)"]
                    )
                    st.dataframe(angle_df, hide_index=True, width="stretch")
                if recommendation:
                    st.write("AI 권고 점수")
                    st.json(recommendation)

        if recommendation:
            defaults = {
                "new_trunk": recommendation["trunk_score"],
                "new_legs": recommendation["legs_score"],
                "new_upper_arm": recommendation["upper_arm_score"],
                "new_lower_arm": recommendation["lower_arm_score"],
            }
            for key, value in defaults.items():
                if key not in st.session_state:
                    st.session_state[key] = value

    st.divider()
    st.subheader("3. REBA 점수 확인/수정")

    st.markdown("**AI 권고 기반 항목**")
    st.caption("AI 추천값으로 시작하며, 각 점수는 평가자가 직접 확정하거나 수정할 수 있습니다.")
    c1, c2 = st.columns(2)
    with c1:
        trunk_score = st.selectbox("몸통(Trunk)", [1,2,3,4,5], key="new_trunk")
        legs_score = st.selectbox("다리(Legs)", [1,2,3,4], key="new_legs")
    with c2:
        upper_arm_score = st.selectbox("위팔(Upper Arm)", [1,2,3,4,5,6], key="new_upper_arm")
        lower_arm_score = st.selectbox("아래팔(Lower Arm)", [1,2], key="new_lower_arm")
    st.markdown("**평가자 수동 판단 항목**")
    st.caption("목·손목·하중·결합도·활동 점수는 현장 조건을 확인해 입력해주세요.")
    c1, c2, c3 = st.columns(3)
    with c1:
        neck_score = st.selectbox("목(Neck)", [1,2,3], key="new_neck")
        wrist_score = st.selectbox("손목(Wrist)", [1,2,3], key="new_wrist")
    with c2:
        load_score = st.selectbox("하중/힘(Load)", [0,1,2,3], key="new_load")
        coupling_score = st.selectbox("결합도(Coupling)", [0,1,2,3], key="new_coupling")
    with c3:
        activity_score = st.selectbox("활동점수(Activity)", [0,1,2,3], key="new_activity")

    score_a = get_score_a(trunk_score, neck_score, legs_score, load_score)
    score_b = get_score_b(upper_arm_score, lower_arm_score, wrist_score, coupling_score)
    table_c_score = get_table_c_score(score_a, score_b)
    final_reba = min(table_c_score + activity_score, 15)
    risk_level, action_level, action_text = classify_reba(final_reba)

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.metric("Score A", score_a)
    with r2:
        st.metric("Score B", score_b)
    with r3:
        st.metric("Table C", table_c_score)
    with r4:
        st.metric("최종 REBA", final_reba)

    st.write(f"**위험등급:** {risk_level}")
    st.write(f"**조치권고:** {action_text}")
    st.divider()

    saved_values = (
        worker.strip(),
        company.strip(),
        department.strip(),
        task_name.strip(),
        evaluator.strip(),
        neck_score, trunk_score, legs_score, load_score,
        upper_arm_score, lower_arm_score, wrist_score,
        coupling_score, activity_score,
    )
    current_signature = (
        submission_signature(photo.getvalue(), saved_values)
        if photo is not None
        else None
    )
    already_saved = (
        current_signature is not None
        and current_signature in st.session_state.get("new_saved_signatures", set())
    )
    if already_saved:
        st.success("저장 완료: 같은 사진과 평가내용은 중복 저장되지 않습니다.")

    save_disabled = (
        not worker.strip()
        or not company.strip()
        or not department.strip()
        or not task_name.strip()
        or photo is None
        or already_saved
        or st.session_state.get("new_saving_signature") == current_signature
    )

    if st.button(
        "💾 REBA 평가 + 사진 저장",
        type="primary",
        width="stretch",
        disabled=save_disabled
    ):
        try:
            st.session_state["new_saving_signature"] = current_signature
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            original_bytes = photo.getvalue()
            original_name = getattr(photo, "name", "camera.jpg")
            content_type = getattr(photo, "type", None) or "image/jpeg"
            extension = original_name.split(".")[-1].lower()
            if extension not in ["jpg", "jpeg", "png"]:
                extension = "jpg"

            original_path = f"{timestamp}/original.{extension}"
            upload_reba_image(original_bytes, original_path, content_type)

            analyzed_bytes = st.session_state.get("new_reba_analyzed_bytes")
            analyzed_path = None
            if analyzed_bytes:
                analyzed_path = f"{timestamp}/analyzed.png"
                upload_reba_image(analyzed_bytes, analyzed_path, "image/png")

            insert_data = {
                "worker": worker,
                "department": (
                    f"{company.strip()} / {department.strip()}"
                    if department.strip()
                    else company.strip()
                ),
                "task_name": task_name,
                "evaluator": evaluator,
                "pose_angles": st.session_state.get("new_reba_angles", {}),
                "ai_recommendation": st.session_state.get("new_reba_recommendation", {}),
                "neck_score": neck_score,
                "trunk_score": trunk_score,
                "legs_score": legs_score,
                "load_score": load_score,
                "upper_arm_score": upper_arm_score,
                "lower_arm_score": lower_arm_score,
                "wrist_score": wrist_score,
                "coupling_score": coupling_score,
                "activity_score": activity_score,
                "score_a": score_a,
                "score_b": score_b,
                "final_reba": final_reba,
                "risk_level": risk_level,
                "action_level": action_level,
                "action_text": action_text,
                "original_image_path": original_path,
                "analyzed_image_path": analyzed_path,
            }

            supabase.table("reba_results").insert(insert_data).execute()
            clear_session_query_cache()
            saved_signatures = set(st.session_state.get("new_saved_signatures", set()))
            saved_signatures.add(current_signature)
            st.session_state["new_saved_signatures"] = saved_signatures
            st.session_state.pop("new_saving_signature", None)
            success_message = "저장 성공: REBA 평가와 원본사진이 저장되었습니다."
            if analyzed_path:
                success_message += " AI 분석사진도 함께 저장되었습니다."
            st.success(success_message)

        except Exception as e:
            st.session_state.pop("new_saving_signature", None)
            st.error(f"저장 오류: {e}")

    action_columns = st.columns(2)
    with action_columns[0]:
        st.button(
            "🔄 재촬영",
            width="stretch",
            on_click=reset_new_capture,
            disabled=photo is None
        )
    with action_columns[1]:
        st.button(
            "취소",
            width="stretch",
            on_click=cancel_new_evaluation
        )


else:
    st.subheader("기존 REBA 평가에 사진만 연결")
    st.info(
        "이 기능은 기존 REBA 점수를 전혀 바꾸지 않습니다. "
        "기존 평가에 원본사진과 AI 관절선 사진만 추가합니다."
    )

    rows = load_reba_results()
    if not rows:
        st.warning("저장된 REBA 평가결과가 없습니다.")
        st.stop()

    options = {}
    for row in rows:
        label = (
            f"#{row.get('id', '')} | "
            f"{row.get('department', '')} | "
            f"{row.get('task_name', '')} | "
            f"{row.get('worker', '')} | "
            f"REBA {row.get('final_reba', '')}"
        )
        options[label] = row

    selected_label = st.selectbox(
        "사진을 연결할 기존 평가를 선택하세요.",
        list(options.keys())
    )
    selected = options[selected_label]

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("기존 REBA", selected.get("final_reba", ""))
    with m2:
        st.metric("위험등급", selected.get("risk_level", ""))
    with m3:
        st.metric("작업명", selected.get("task_name", ""))

    existing_original = download_storage_file(selected.get("original_image_path"))
    existing_analyzed = download_storage_file(selected.get("analyzed_image_path"))

    if existing_original or existing_analyzed:
        st.write("#### 현재 연결된 사진")
        ec1, ec2 = st.columns(2)
        with ec1:
            if existing_original:
                st.image(existing_original, caption="기존 원본사진", width="stretch")
        with ec2:
            if existing_analyzed:
                st.image(existing_analyzed, caption="기존 AI 분석사진", width="stretch")

    # 기존 저장사진의 관절점을 직접 보정하는 기능
    if existing_original:
        st.divider()
        st.subheader("✏️ 기존 저장사진 관절점 직접 보정")
        st.caption(
            "기존 원본사진을 이용해 관절을 다시 인식합니다. "
            "REBA 최종 점수와 원본사진은 변경하지 않습니다."
        )

        record_id = str(selected["id"])
        prefix = f"saved_joint_{record_id}"

        enable_edit = st.checkbox(
            "기존 사진 관절점 보정 시작",
            key=f"{prefix}_enabled"
        )

        if enable_edit:
            with st.spinner("기존 사진에서 관절 위치를 확인하고 있습니다..."):
                auto_analyze_image(existing_original, prefix)

            error = st.session_state.get(f"{prefix}_error")

            if error:
                st.warning(error)

            landmarks = st.session_state.get(
                f"{prefix}_landmarks"
            )

            if landmarks:
                joint_indices = [
                    11, 12, 13, 14, 15, 16,
                    23, 24, 25, 26, 27, 28
                ]

                joint_points = [
                    {
                        "id": idx,
                        "x": float(landmarks[idx].x),
                        "y": float(landmarks[idx].y),
                    }
                    for idx in joint_indices
                ]

                correction = joint_drag_editor(
                    existing_original,
                    joint_points,
                    key=f"saved_drag_{record_id}",
                )

                if (
                    isinstance(correction, dict)
                    and correction.get("action") == "apply"
                ):
                    revision = str(correction.get("revision", ""))
                    revision_key = f"{prefix}_revision"

                    if (
                        revision
                        and st.session_state.get(revision_key) != revision
                    ):
                        st.session_state[revision_key] = revision

                        points_by_id = {
                            int(p["id"]): p
                            for p in correction.get("points", [])
                            if isinstance(p, dict)
                            and all(
                                k in p
                                for k in ("id", "x", "y")
                            )
                        }

                        if set(joint_indices).issubset(points_by_id):
                            import copy

                            corrected = copy.deepcopy(landmarks)

                            for idx in joint_indices:
                                point = points_by_id[idx]
                                corrected[idx].x = max(
                                    0.0,
                                    min(1.0, float(point["x"]))
                                )
                                corrected[idx].y = max(
                                    0.0,
                                    min(1.0, float(point["y"]))
                                )
                                corrected[idx].visibility = 1.0

                            original_rgb = decode_image(
                                existing_original
                            )

                            if original_rgb is not None:
                                output = draw_pose(
                                    original_rgb, corrected
                                )

                                output_bgr = cv2.cvtColor(
                                    output,
                                    cv2.COLOR_RGB2BGR
                                )

                                ok, encoded = cv2.imencode(
                                    ".png", output_bgr
                                )

                                if ok:
                                    height, width = original_rgb.shape[:2]

                                    corrected_angles = get_pose_angles(
                                        corrected, width, height
                                    )

                                    st.session_state[
                                        f"{prefix}_landmarks"
                                    ] = corrected

                                    st.session_state[
                                        f"{prefix}_corrected_bytes"
                                    ] = encoded.tobytes()

                                    st.session_state[
                                        f"{prefix}_corrected_angles"
                                    ] = corrected_angles

                                    st.rerun()
                                else:
                                    st.error(
                                        "보정사진 생성에 실패했습니다."
                                    )
                            else:
                                st.error(
                                    "기존 원본사진을 읽지 못했습니다."
                                )
                        else:
                            st.error(
                                "관절 좌표가 불완전해 보정하지 않았습니다."
                            )

                corrected_bytes = st.session_state.get(
                    f"{prefix}_corrected_bytes"
                )

                if corrected_bytes:
                    st.success("관절 위치 보정이 적용됐습니다.")

                    display_photo(
                        corrected_bytes,
                        "보정된 AI 관절선 사진 미리보기"
                    )

                    angles = st.session_state.get(
                        f"{prefix}_corrected_angles"
                    )

                    if angles:
                        with st.expander("보정 후 관절 각도"):
                            st.json(angles)

                    st.warning(
                        "아래 저장 버튼을 누르면 기존 평가의 "
                        "분석사진 연결만 새 사진으로 변경됩니다. "
                        "원본사진과 REBA 점수는 유지됩니다."
                    )

                    if st.button(
                        "💾 기존 평가에 보정사진 저장",
                        type="primary",
                        key=f"{prefix}_save",
                        width="stretch"
                    ):
                        try:
                            timestamp = datetime.now().strftime(
                                "%Y%m%d_%H%M%S_%f"
                            )

                            analyzed_path = (
                                f"{timestamp}/corrected_analyzed.png"
                            )

                            upload_reba_image(
                                corrected_bytes,
                                analyzed_path,
                                "image/png"
                            )

                            (
                                supabase
                                .table("reba_results")
                                .update({
                                    "analyzed_image_path": analyzed_path
                                })
                                .eq("id", selected["id"])
                                .execute()
                            )

                            clear_session_query_cache()

                            st.session_state.pop(
                                f"{prefix}_corrected_bytes", None
                            )

                            st.success(
                                "✅ 보정사진 저장 완료! "
                                "기존 REBA 점수와 원본사진은 "
                                "변경하지 않았습니다."
                            )

                            st.rerun()

                        except Exception as e:
                            st.error(
                                f"보정사진 저장 오류: {e}"
                            )

            elif not error:
                st.info(
                    "관절 분석 결과를 확인하는 중입니다."
                )

    st.divider()

    old_source = st.radio(
        "새로 연결할 사진 입력방법",
        ["📷 카메라 촬영", "🖼️ 사진 업로드"],
        horizontal=True,
        key="existing_source"
    )

    if old_source == "📷 카메라 촬영":
        existing_photo = st.camera_input(
            "작업자 전신이 보이도록 촬영해주세요.",
            key="existing_camera"
        )
    else:
        existing_photo = st.file_uploader(
            "기존 평가에 연결할 사진을 선택하세요.",
            type=["jpg", "jpeg", "png"],
            key="existing_upload"
        )

    if existing_photo is not None:
        existing_bytes = existing_photo.getvalue()
        st.image(existing_bytes, caption="새로 연결할 원본사진", width="stretch")

        with st.spinner("사진의 관절선을 자동 분석하고 있습니다..."):
            auto_analyze_image(existing_bytes, "existing_reba")

        error = st.session_state.get("existing_reba_error")
        if error:
            st.warning(
                "원본사진은 연결할 수 있지만 AI 분석사진은 만들지 못했습니다: "
                f"{error}"
            )

        existing_new_analyzed = st.session_state.get("existing_reba_analyzed_bytes")
        if existing_new_analyzed:
            st.image(
                existing_new_analyzed,
                caption="새 AI 관절선 분석사진",
                width="stretch"
            )

        st.warning(
            "아래 버튼을 눌러도 기존 REBA 점수, 위험등급, 평가내용은 변경되지 않습니다."
        )

        if st.button(
            "📎 기존 평가에 사진만 저장",
            type="primary",
            width="stretch"
        ):
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                original_name = getattr(existing_photo, "name", "camera.jpg")
                content_type = getattr(existing_photo, "type", None) or "image/jpeg"
                extension = original_name.split(".")[-1].lower()
                if extension not in ["jpg", "jpeg", "png"]:
                    extension = "jpg"

                original_path = f"{timestamp}/original.{extension}"
                upload_reba_image(existing_bytes, original_path, content_type)

                analyzed_path = None
                if existing_new_analyzed:
                    analyzed_path = f"{timestamp}/analyzed.png"
                    upload_reba_image(existing_new_analyzed, analyzed_path, "image/png")

                update_data = {
                    "original_image_path": original_path,
                    "analyzed_image_path": analyzed_path,
                }

                (
                    supabase
                    .table("reba_results")
                    .update(update_data)
                    .eq("id", selected["id"])
                    .execute()
                )

                clear_session_query_cache()

                st.success(
                    "✅ 기존 REBA 점수는 그대로 유지하고 사진만 연결했습니다."
                )

            except Exception as e:
                st.error(f"사진 연결 오류: {e}")

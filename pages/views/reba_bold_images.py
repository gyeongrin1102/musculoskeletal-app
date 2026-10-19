"""기존 REBA 분석사진의 초록색 관절선을 굵게 만드는 기능."""

import cv2
import numpy as np


def make_bold_reba_image(original_bytes, analyzed_bytes, thickness=9):
    original = cv2.imdecode(
        np.frombuffer(original_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR
    )
    analyzed = cv2.imdecode(
        np.frombuffer(analyzed_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR
    )

    if original is None or analyzed is None:
        raise ValueError("사진을 읽을 수 없습니다.")

    if original.shape != analyzed.shape:
        raise ValueError("원본사진과 분석사진 크기가 다릅니다.")

    hsv = cv2.cvtColor(analyzed, cv2.COLOR_BGR2HSV)

    green_mask = cv2.inRange(
        hsv,
        np.array([35, 70, 70], dtype=np.uint8),
        np.array([95, 255, 255], dtype=np.uint8)
    )

    difference = cv2.absdiff(original, analyzed)

    changed_mask = (
        np.max(difference, axis=2) > 40
    ).astype(np.uint8) * 255

    pose_mask = cv2.bitwise_and(
        green_mask,
        changed_mask
    )

    if cv2.countNonZero(pose_mask) < 20:
        raise ValueError("관절선을 충분히 찾지 못했습니다.")

    if cv2.countNonZero(pose_mask) > pose_mask.size * 0.10:
        raise ValueError("관절선 후보 영역이 비정상적으로 넓습니다.")

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (thickness, thickness)
    )

    bold_mask = cv2.dilate(
        pose_mask,
        kernel,
        iterations=1
    )

    result = analyzed.copy()
    result[bold_mask > 0] = (0, 225, 0)

    success, encoded = cv2.imencode(".png", result)

    if not success:
        raise ValueError("이미지 저장에 실패했습니다.")

    return encoded.tobytes()

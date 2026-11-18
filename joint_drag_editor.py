"""AI 관절점 드래그 편집기. 데이터베이스를 직접 변경하지 않음."""
import base64
from pathlib import Path

import cv2
import numpy as np
import streamlit.components.v1 as components

_FRONTEND = Path(__file__).parent / "joint_drag_widget"
_COMPONENT = components.declare_component(
    "joint_drag_editor_v1",
    path=str(_FRONTEND),
)

def joint_drag_editor(image_bytes, points, key):
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        return None

    h, w = image.shape[:2]
    if max(h, w) > 1000:
        ratio = 1000 / max(h, w)
        image = cv2.resize(
            image,
            (max(1, round(w * ratio)), max(1, round(h * ratio))),
            interpolation=cv2.INTER_AREA,
        )

    success, encoded = cv2.imencode(
        ".jpg",
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), 82],
    )
    if not success:
        return None

    preview = base64.b64encode(encoded.tobytes()).decode("ascii")
    return _COMPONENT(
        image=preview,
        points=points,
        key=key,
        default=None,
    )

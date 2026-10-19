import os
import re
import json
import struct
import base64
import time
import threading
from io import BytesIO

import requests
import pandas as pd
import streamlit as st

from PIL import Image

import cv2
import numpy as np
import zxingcpp
import av

from Crypto.Cipher import AES
from Crypto.Util import Counter

from streamlit_webrtc import (
    WebRtcMode,
    webrtc_streamer,
)


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Holland Bazar T&D",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# SETTINGS
# ============================================================

EXCEL_PATH = "DATABASE.xlsx"

MEGA_FOLDER_URL = (
    "https://mega.nz/folder/HrximbwC"
    "#9wvR9D8OQnrAJlTItE6Oag"
)

MEGA_API = "https://g.api.mega.co.nz/cs"


# ============================================================
# BASIC CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .scanner-guide {
        text-align: center;
        color: #94a3b8;
        font-size: 14px;
        margin-top: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE
# ============================================================

@st.cache_data(ttl=5)
def load_data():

    if not os.path.exists(EXCEL_PATH):
        return None

    try:

        df = pd.read_excel(
            EXCEL_PATH,
            dtype=str,
        )

        df.columns = [
            str(i)
            for i in range(
                len(df.columns)
            )
        ]

        for column in df.columns:

            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        return df

    except Exception as e:

        st.error(
            f"خطأ في قراءة DATABASE.xlsx: {e}"
        )

        return None


# ============================================================
# MEGA BASE64
# ============================================================

def mega_b64_decode(value):

    if isinstance(value, str):
        value = value.encode("utf-8")

    value += b"=" * (-len(value) % 4)

    return base64.urlsafe_b64decode(value)


def base64_to_a32(value):

    raw = mega_b64_decode(value)

    if len(raw) % 4 != 0:

        raise ValueError(
            "Invalid MEGA key length."
        )

    return struct.unpack(
        ">" + ("I" * (len(raw) // 4)),
        raw,
    )


def a32_to_bytes(values):

    return struct.pack(
        ">" + ("I" * len(values)),
        *values,
    )


# ============================================================
# MEGA CRYPTO
# ============================================================

def decrypt_key(
    encrypted_key,
    key,
):

    encrypted_bytes = a32_to_bytes(
        encrypted_key
    )

    key_bytes = a32_to_bytes(
        key
    )

    cipher = AES.new(
        key_bytes,
        AES.MODE_ECB,
    )

    decrypted = cipher.decrypt(
        encrypted_bytes
    )

    return struct.unpack(
        ">" + ("I" * (len(decrypted) // 4)),
        decrypted,
    )


def decrypt_attributes(
    encrypted_attributes,
    key,
):

    encrypted = mega_b64_decode(
        encrypted_attributes
    )

    key_bytes = a32_to_bytes(
        key
    )

    cipher = AES.new(
        key_bytes,
        AES.MODE_CBC,
        iv=b"\x00" * 16,
    )

    decrypted = cipher.decrypt(
        encrypted
    )

    decrypted = decrypted.rstrip(
        b"\x00"
    )

    if not decrypted.startswith(
        b"MEGA"
    ):

        raise ValueError(
            "Invalid MEGA attribute prefix"
        )

    return json.loads(
        decrypted[4:].decode(
            "utf-8"
        )
    )


# ============================================================
# MEGA URL
# ============================================================

def parse_mega_folder_url(url):

    match = re.search(
        r"mega\.nz/folder/([^#/?]+)#([^/?]+)",
        url,
    )

    if match:

        return (
            match.group(1),
            match.group(2),
        )

    match = re.search(
        r"mega\.nz/#F!([^!#/?]+)[!#]([^/?]+)",
        url,
    )

    if match:

        return (
            match.group(1),
            match.group(2),
        )

    raise ValueError(
        "رابط مجلد MEGA غير صالح."
    )


# ============================================================
# MEGA API
# ============================================================

def mega_api_request(
    data,
    folder_handle=None,
):

    params = {
        "id": 0,
    }

    if folder_handle:
        params["n"] = folder_handle

    response = requests.post(
        MEGA_API,
        params=params,
        json=[data],
        timeout=60,
    )

    response.raise_for_status()

    result = response.json()

    if isinstance(result, int):

        raise RuntimeError(
            f"MEGA API error: {result}"
        )

    if (
        not isinstance(result, list)
        or not result
    ):

        raise RuntimeError(
            "MEGA returned an empty response."
        )

    if isinstance(result[0], int):

        raise RuntimeError(
            f"MEGA API error: {result[0]}"
        )

    return result[0]


# ============================================================
# MEGA NODES
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def get_mega_nodes():

    folder_handle, folder_key_text = (
        parse_mega_folder_url(
            MEGA_FOLDER_URL
        )
    )

    shared_key = base64_to_a32(
        folder_key_text
    )

    response = mega_api_request(
        {
            "a": "f",
            "c": 1,
            "ca": 1,
            "r": 1,
        },
        folder_handle=folder_handle,
    )

    nodes = response.get(
        "f",
        [],
    )

    result = []

    for node in nodes:

        if node.get("t") not in (
            0,
            1,
        ):
            continue

        encrypted_node_key = node.get("k")
        encrypted_attributes = node.get("a")
        node_handle = node.get("h")

        if not encrypted_node_key:
            continue

        if not encrypted_attributes:
            continue

        if not node_handle:
            continue

        try:

            if ":" in encrypted_node_key:

                encrypted_key_text = (
                    encrypted_node_key.split(
                        ":",
                        1,
                    )[1]
                )

            else:

                encrypted_key_text = (
                    encrypted_node_key
                )

            encrypted_key = base64_to_a32(
                encrypted_key_text
            )

            node_key = decrypt_key(
                encrypted_key,
                shared_key,
            )

            if node.get("t") == 0:

                if len(node_key) < 8:
                    continue

                file_key = (
                    node_key[0] ^ node_key[4],
                    node_key[1] ^ node_key[5],
                    node_key[2] ^ node_key[6],
                    node_key[3] ^ node_key[7],
                )

            else:

                file_key = node_key

            attributes = decrypt_attributes(
                encrypted_attributes,
                file_key,
            )

            filename = attributes.get(
                "n",
                "",
            )

            if not filename:
                continue

            result.append(
                {
                    "handle": node_handle,
                    "name": filename,
                    "type": node.get("t"),
                    "key": list(node_key),
                    "parent": node.get("p"),
                    "size": node.get("s", 0),
                }
            )

        except Exception:

            continue

    return result


# ============================================================
# FIND IMAGE
# ============================================================

def find_mega_image(
    nodes,
    code,
    barcode,
):

    identifiers = []

    for value in (
        barcode,
        code,
    ):

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        if value.lower() == "nan":
            continue

        identifiers.append(
            value.lower()
        )

    extensions = (
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
    )

    files = [
        node
        for node in nodes
        if node["type"] == 0
        and node["name"].lower().endswith(
            extensions
        )
    ]

    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if stem == identifier:

                return node

    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if identifier in stem:

                return node

    return None


# ============================================================
# DOWNLOAD IMAGE
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def download_mega_image(
    node_handle,
    node_key,
):

    folder_handle, _ = (
        parse_mega_folder_url(
            MEGA_FOLDER_URL
        )
    )

    response = mega_api_request(
        {
            "a": "g",
            "g": 1,
            "n": node_handle,
        },
        folder_handle=folder_handle,
    )

    download_url = response.get("g")

    if not download_url:

        raise RuntimeError(
            "MEGA did not return a download URL."
        )

    key = tuple(node_key)

    aes_key_words = (
        key[0] ^ key[4],
        key[1] ^ key[5],
        key[2] ^ key[6],
        key[3] ^ key[7],
    )

    aes_key = a32_to_bytes(
        aes_key_words
    )

    iv_words = (
        key[4],
        key[5],
        0,
        0,
    )

    counter_value = (
        (iv_words[0] << 32)
        + iv_words[1]
    ) << 64

    counter = Counter.new(
        128,
        initial_value=counter_value,
    )

    decryptor = AES.new(
        aes_key,
        AES.MODE_CTR,
        counter=counter,
    )

    response = requests.get(
        download_url,
        stream=True,
        timeout=120,
    )

    response.raise_for_status()

    output = BytesIO()

    for chunk in response.iter_content(
        chunk_size=1024 * 1024
    ):

        if chunk:

            output.write(
                decryptor.decrypt(
                    chunk
                )
            )

    return output.getvalue()


# ============================================================
# BARCODE FORMAT FILTER
# ============================================================

def retail_formats():

    try:

        return zxingcpp.barcode_formats_from_str(
            "EAN13|EAN8|UPCA|UPCE|"
            "Code128|Code39|Code93|ITF|"
            "ITF14|Codabar|DataBar"
        )

    except Exception:

        return zxingcpp.BarcodeFormats()


ZX_FORMATS = retail_formats()


# ============================================================
# ZXING DECODER
# ============================================================

def zxing_decode(
    image,
):

    if image is None:
        return None

    candidates = []

    # Original
    candidates.append(
        image
    )

    # Grayscale
    if len(image.shape) == 3:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

    else:

        gray = image

    candidates.append(
        gray
    )

    # CLAHE
    clahe = cv2.createCLAHE(
        clipLimit=2.5,
        tileGridSize=(8, 8),
    )

    clahe_img = clahe.apply(
        gray
    )

    candidates.append(
        clahe_img
    )

    # OTSU
    _, otsu = cv2.threshold(
        clahe_img,
        0,
        255,
        cv2.THRESH_BINARY
        + cv2.THRESH_OTSU,
    )

    candidates.append(
        otsu
    )

    # Adaptive threshold
    adaptive = cv2.adaptiveThreshold(
        clahe_img,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        7,
    )

    candidates.append(
        adaptive
    )

    # Upscale smaller images
    enlarged = cv2.resize(
        gray,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_CUBIC,
    )

    candidates.append(
        enlarged
    )


    for candidate in candidates:

        try:

            results = (
                zxingcpp.read_barcodes(
                    candidate,
                    formats=ZX_FORMATS,
                    try_rotate=True,
                    try_downscale=False,
                    try_invert=True,
                    binarizer=zxingcpp.Binarizer.LocalAverage,
                )
            )

        except Exception:

            continue


        for result in results:

            if not result.valid:
                continue

            text = str(
                result.text
            ).strip()

            if not text:
                continue

            text = re.sub(
                r"\s+",
                "",
                text,
            )

            return {
                "text": text,
                "format": str(
                    result.format
                ),
            }

    return None


# ============================================================
# OPEN CV BARCODE DETECTOR
# ============================================================

@st.cache_resource
def create_barcode_detector():

    try:

        if not hasattr(
            cv2,
            "barcode",
        ):

            return None

        detector = (
            cv2.barcode.BarcodeDetector()
        )

        return detector

    except Exception:

        return None


BARCODE_DETECTOR = (
    create_barcode_detector()
)


# ============================================================
# PERSPECTIVE WARP
# ============================================================

def order_points(points):

    points = np.asarray(
        points,
        dtype=np.float32,
    )

    if points.shape[0] != 4:

        return None

    sums = points.sum(
        axis=1
    )

    diffs = np.diff(
        points,
        axis=1,
    ).reshape(-1)

    top_left = points[
        np.argmin(sums)
    ]

    bottom_right = points[
        np.argmax(sums)
    ]

    top_right = points[
        np.argmin(diffs)
    ]

    bottom_left = points[
        np.argmax(diffs)
    ]

    return np.array(
        [
            top_left,
            top_right,
            bottom_right,
            bottom_left,
        ],
        dtype=np.float32,
    )


def perspective_crop(
    image,
    points,
):

    ordered = order_points(
        points
    )

    if ordered is None:
        return None

    (
        top_left,
        top_right,
        bottom_right,
        bottom_left,
    ) = ordered


    width_a = np.linalg.norm(
        bottom_right
        - bottom_left
    )

    width_b = np.linalg.norm(
        top_right
        - top_left
    )

    height_a = np.linalg.norm(
        top_right
        - bottom_right
    )

    height_b = np.linalg.norm(
        top_left
        - bottom_left
    )


    width = int(
        max(
            width_a,
            width_b,
        )
    )

    height = int(
        max(
            height_a,
            height_b,
        )
    )


    if width < 20 or height < 10:
        return None


    # Barcode needs plenty of horizontal resolution.
    width = max(
        width * 3,
        900,
    )

    height = max(
        height * 3,
        300,
    )


    destination = np.array(
        [
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1],
        ],
        dtype=np.float32,
    )


    matrix = cv2.getPerspectiveTransform(
        ordered,
        destination,
    )


    warped = cv2.warpPerspective(
        image,
        matrix,
        (
            width,
            height,
        ),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )

    return warped


# ============================================================
# OPENCV DETECTION
# ============================================================

def opencv_decode(
    frame,
):

    if BARCODE_DETECTOR is None:
        return None


    try:

        image = frame

        height, width = image.shape[:2]

        # Keep enough resolution for small retail barcodes.
        if width < 1400:

            scale = (
                1400 / width
            )

            image = cv2.resize(
                image,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC,
            )


        # ----------------------------------------------------
        # First attempt: detector does everything.
        # ----------------------------------------------------

        try:

            (
                ok,
                decoded_info,
                decoded_type,
                points,
            ) = (
                BARCODE_DETECTOR
                .detectAndDecodeWithType(
                    image
                )
            )

            if ok:

                for value in decoded_info:

                    if value:

                        value = re.sub(
                            r"\s+",
                            "",
                            str(value),
                        )

                        if value:

                            return {
                                "text": value,
                                "format": (
                                    str(
                                        decoded_type[
                                            0
                                        ]
                                    )
                                    if decoded_type
                                    else "barcode"
                                ),
                            }

        except Exception:

            pass


        # ----------------------------------------------------
        # Second attempt:
        #
        # Detect the barcode rectangle even if OpenCV
        # couldn't decode it.
        # ----------------------------------------------------

        try:

            detected, points = (
                BARCODE_DETECTOR.detect(
                    image
                )
            )

        except Exception:

            detected = False
            points = None


        if not detected:
            return None

        if points is None:
            return None


        # Normalize point layout.
        points_array = np.asarray(
            points
        )


        # OpenCV normally returns:
        # N x 4 x 2
        #
        # but handle flat layouts too.

        if (
            points_array.ndim == 3
            and points_array.shape[-2:] == (4, 2)
        ):

            rectangles = (
                points_array
            )

        elif (
            points_array.ndim == 2
            and points_array.shape[1] == 2
            and len(points_array) >= 4
        ):

            rectangles = [
                points_array[
                    :4
                ]
            ]

        else:

            return None


        # ----------------------------------------------------
        # Decode each detected barcode region.
        # ----------------------------------------------------

        for rectangle in rectangles:

            crop = perspective_crop(
                image,
                rectangle,
            )

            if crop is None:
                continue


            # Add white quiet-zone border.
            crop = cv2.copyMakeBorder(
                crop,
                80,
                80,
                120,
                120,
                cv2.BORDER_CONSTANT,
                value=(255, 255, 255),
            )


            result = zxing_decode(
                crop
            )

            if result:

                return result


        return None

    except Exception:

        return None


# ============================================================
# MASTER BARCODE DECODER
# ============================================================

def decode_frame(
    frame,
):

    if frame is None:
        return None


    # --------------------------------------------------------
    # OpenCV barcode detector + perspective correction
    # --------------------------------------------------------

    result = opencv_decode(
        frame
    )

    if result:

        return result


    # --------------------------------------------------------
    # ZXing fallback on strategically cropped regions.
    # --------------------------------------------------------

    image = frame

    h, w = image.shape[:2]


    candidates = [
        image,

        image[
            int(h * 0.15):
            int(h * 0.85),
            int(w * 0.05):
            int(w * 0.95)
        ],

        image[
            int(h * 0.25):
            int(h * 0.75),
            :
        ],

        image[
            int(h * 0.35):
            int(h * 0.65),
            :
        ],
    ]


    for candidate in candidates:

        result = zxing_decode(
            candidate
        )

        if result:

            return result


    return None


# ============================================================
# CAMERA SHARED STATE
# ============================================================

if "barcode_result" not in st.session_state:

    st.session_state[
        "barcode_result"
    ] = ""


if "barcode_format" not in st.session_state:

    st.session_state[
        "barcode_format"
    ] = ""


if "scanner_running" not in st.session_state:

    st.session_state[
        "scanner_running"
    ] = False


# Thread-safe scanner state.
scanner_lock = threading.Lock()

scanner_state = {
    "result": None,
    "last_attempt": 0.0,
}


# ============================================================
# LIVE SCANNER
# ============================================================

def render_live_scanner():

    st.subheader(
        "📷 الماسح المباشر"
    )

    st.caption(
        "ضع الباركود داخل المستطيل الأخضر، "
        "واجعله واضحاً وكبيراً في الكاميرا."
    )


    st.info(
        "💡 للحصول على أفضل قراءة: "
        "اقترب من الباركود، تجنب انعكاس الضوء، "
        "واجعل الخطوط أفقية داخل الإطار."
    )


    # --------------------------------------------------------
    # Camera
    # --------------------------------------------------------

    def video_frame_callback(
        frame
    ):

        image = frame.to_ndarray(
            format="bgr24"
        )


        now = time.monotonic()


        # Don't run expensive processing on every frame.
        should_scan = (
            now
            - scanner_state[
                "last_attempt"
            ]
            >= 0.20
        )


        if should_scan:

            scanner_state[
                "last_attempt"
            ] = now


            result = decode_frame(
                image
            )


            if result:

                with scanner_lock:

                    scanner_state[
                        "result"
                    ] = result


        # ----------------------------------------------------
        # Scanner guide
        # ----------------------------------------------------

        h, w = image.shape[:2]


        # Wide horizontal barcode box.
        box_width = int(
            w * 0.82
        )

        box_height = int(
            h * 0.30
        )


        left = (
            w - box_width
        ) // 2

        top = (
            h - box_height
        ) // 2

        right = (
            left + box_width
        )

        bottom = (
            top + box_height
        )


        # Outer box
        cv2.rectangle(
            image,
            (left, top),
            (right, bottom),
            (0, 255, 0),
            3,
        )


        # Center scan line
        center_y = (
            top + bottom
        ) // 2


        cv2.line(
            image,
            (
                left + 20,
                center_y,
            ),
            (
                right - 20,
                center_y,
            ),
            (0, 255, 0),
            2,
        )


        # Corner markers
        corner = 45
        thickness = 7


        # Top-left
        cv2.line(
            image,
            (left, top),
            (left + corner, top),
            (0, 255, 0),
            thickness,
        )

        cv2.line(
            image,
            (left, top),
            (left, top + corner),
            (0, 255, 0),
            thickness,
        )


        # Top-right
        cv2.line(
            image,
            (right, top),
            (right - corner, top),
            (0, 255, 0),
            thickness,
        )

        cv2.line(
            image,
            (right, top),
            (right, top + corner),
            (0, 255, 0),
            thickness,
        )


        # Bottom-left
        cv2.line(
            image,
            (left, bottom),
            (left + corner, bottom),
            (0, 255, 0),
            thickness,
        )

        cv2.line(
            image,
            (left, bottom),
            (left, bottom - corner),
            (0, 255, 0),
            thickness,
        )


        # Bottom-right
        cv2.line(
            image,
            (right, bottom),
            (right - corner, bottom),
            (0, 255, 0),
            thickness,
        )

        cv2.line(
            image,
            (right, bottom),
            (right, bottom - corner),
            (0, 255, 0),
            thickness,
        )


        return av.VideoFrame.from_ndarray(
            image,
            format="bgr24",
        )


    ctx = webrtc_streamer(
        key="warehouse-barcode-scanner",

        mode=WebRtcMode.SENDRECV,

        video_frame_callback=(
            video_frame_callback
        ),

        media_stream_constraints={
            "video": {
                "width": {
                    "ideal": 1920
                },
                "height": {
                    "ideal": 1080
                },
                "facingMode": {
                    "ideal": "environment"
                },
            },
            "audio": False,
        },

        rtc_configuration={
            "iceServers": [
                {
                    "urls": [
                        "stun:stun.l.google.com:19302"
                    ]
                }
            ]
        },

        desired_playing_state=True,

        sendback_audio=False,
    )


    # --------------------------------------------------------
    # Wait for scanner result
    # --------------------------------------------------------

    if ctx.state.playing:

        result_placeholder = st.empty()


        while ctx.state.playing:

            with scanner_lock:

                result = scanner_state[
                    "result"
                ]


            if result:

                # Clear immediately so it doesn't repeat.
                with scanner_lock:

                    scanner_state[
                        "result"
                    ] = None


                st.session_state[
                    "barcode_result"
                ] = result["text"]

                st.session_state[
                    "barcode_format"
                ] = result["format"]


                st.session_state[
                    "scanner_running"
                ] = False


                st.rerun()


            result_placeholder.info(
                "🔎 جاري التعرف على الباركود..."
            )


            time.sleep(
                0.10
            )


# ============================================================
# PHOTO SCANNER
# ============================================================

def render_photo_scanner():

    st.subheader(
        "📸 مسح من صورة"
    )

    st.caption(
        "إذا كانت الإضاءة أو الكاميرا تمنع القراءة المباشرة، "
        "التقط صورة واضحة للباركود هنا."
    )


    photo = st.camera_input(
        "التقاط صورة للباركود",
        key="barcode_photo",
    )


    if photo is None:

        return


    try:

        image = Image.open(
            BytesIO(
                photo.getvalue()
            )
        ).convert(
            "RGB"
        )


        frame = cv2.cvtColor(
            np.array(image),
            cv2.COLOR_RGB2BGR,
        )


        with st.spinner(
            "جاري تحليل الباركود..."
        ):

            result = decode_frame(
                frame
            )


        if result:

            st.success(
                f"تمت قراءة الباركود: "
                f"{result['text']}"
            )

            st.session_state[
                "barcode_result"
            ] = result["text"]

            st.session_state[
                "barcode_format"
            ] = result["format"]

            st.rerun()


        else:

            st.error(
                "لم أتمكن من قراءة الباركود من الصورة."
            )

            st.image(
                image,
                caption="الصورة التي تم تحليلها",
                width="stretch",
            )


            st.warning(
                "حاول أن تجعل الباركود يحتل معظم الصورة "
                "وأن يكون خارج الإطار/اللمعان."
            )


    except Exception as e:

        st.error(
            f"خطأ أثناء تحليل الصورة: {e}"
        )


# ============================================================
# PRODUCT
# ============================================================

def render_product(
    df,
    search_query,
):

    col_code = "0"
    col_barcode = "1"
    col_desc = "2"
    col_qty = "3"


    matches = df[
        (df[col_barcode] == search_query)
        |
        (df[col_code] == search_query)
    ]


    if matches.empty:

        st.error(
            "❌ لم يتم العثور على المنتج."
        )


        similar = df[
            df[col_code].str.contains(
                search_query,
                na=False,
                case=False,
                regex=False,
            )
            |
            df[col_barcode].str.contains(
                search_query,
                na=False,
                case=False,
                regex=False,
            )
        ]


        if not similar.empty:

            st.subheader(
                "نتائج مشابهة"
            )


            for _, row in (
                similar.head(5).iterrows()
            ):

                description = str(
                    row[col_desc]
                ).strip()

                code = str(
                    row[col_code]
                ).strip()

                barcode = str(
                    row[col_barcode]
                ).strip()


                with st.container(
                    border=True
                ):

                    st.write(
                        f"**{description}**"
                    )

                    st.caption(
                        f"الكود: {code}  •  "
                        f"الباركود: {barcode}"
                    )

        return


    row = matches.iloc[0]


    code = str(
        row[col_code]
    ).strip()

    barcode = str(
        row[col_barcode]
    ).strip()

    description = str(
        row[col_desc]
    ).strip()

    quantity = str(
        row[col_qty]
    ).strip()


    if (
        not barcode
        or barcode.lower() == "nan"
    ):

        barcode = "غير متوفر"


    if (
        not description
        or description.lower() == "nan"
    ):

        description = "غير متوفر"


    if (
        not quantity
        or quantity.lower() == "nan"
    ):

        quantity = "0"


    # ========================================================
    # PRODUCT CARD
    # ========================================================

    st.success(
        "✅ تم العثور على المنتج"
    )


    with st.container(
        border=True
    ):

        st.title(
            f"📦 {description}"
        )

        st.divider()


        col1, col2, col3 = (
            st.columns(
                3,
                gap="large",
            )
        )


        with col1:

            st.metric(
                "كود المنتج",
                code,
            )


        with col2:

            st.metric(
                "الباركود",
                barcode,
            )


        with col3:

            st.metric(
                "الكمية",
                quantity,
            )


    # ========================================================
    # IMAGE
    # ========================================================

    st.subheader(
        "🖼️ صورة المنتج"
    )


    try:

        with st.spinner(
            "جاري تحميل صورة المنتج..."
        ):

            nodes = get_mega_nodes()

            image_node = find_mega_image(
                nodes,
                code,
                barcode,
            )


        if image_node is None:

            st.info(
                "لا توجد صورة مرتبطة بهذا المنتج."
            )

            return


        image_bytes = (
            download_mega_image(
                image_node["handle"],
                image_node["key"],
            )
        )


        image = Image.open(
            BytesIO(
                image_bytes
            )
        )


        image.thumbnail(
            (
                600,
                650,
            ),
            Image.Resampling.LANCZOS,
        )


        left, center, right = (
            st.columns(
                [1, 2, 1]
            )
        )


        with center:

            st.image(
                image,
                width="stretch",
            )

            st.caption(
                image_node["name"]
            )


    except Exception as e:

        st.error(
            f"تعذر تحميل صورة المنتج: {e}"
        )


# ============================================================
# MAIN
# ============================================================

df = load_data()


if df is None:

    st.error(
        "❌ ملف DATABASE.xlsx غير موجود."
    )

    st.stop()


if df.empty:

    st.error(
        "❌ ملف DATABASE.xlsx فارغ."
    )

    st.stop()


# ============================================================
# HEADER
# ============================================================

st.title(
    "📦 Holland Bazar T&D"
)

st.caption(
    "البحث عن المنتجات والمخزون"
)

st.divider()


# ============================================================
# TABS
# ============================================================

search_tab, live_tab, photo_tab = st.tabs(
    [
        "🔎 البحث",
        "📷 الماسح المباشر",
        "📸 صورة الباركود",
    ]
)


# ============================================================
# SEARCH
# ============================================================

with search_tab:

    scanned = st.session_state.get(
        "barcode_result",
        "",
    )


    if scanned:

        st.success(
            f"📷 الباركود المقروء: **{scanned}**"
        )


        if st.button(
            "✕ إلغاء نتيجة المسح",
            use_container_width=True,
        ):

            st.session_state[
                "barcode_result"
            ] = ""

            st.session_state[
                "barcode_format"
            ] = ""

            st.rerun()


    search_query = st.text_input(
        "الباركود أو كود المنتج",
        value=scanned,
        placeholder="مثال: 6932308668058",
        key="product_search",
    ).strip()


    if search_query:

        render_product(
            df,
            search_query,
        )

    else:

        st.info(
            "أدخل الباركود أو كود المنتج، "
            "أو استخدم أحد الماسحين."
        )


# ============================================================
# LIVE SCANNER
# ============================================================

with live_tab:

    render_live_scanner()


# ============================================================
# PHOTO SCANNER
# ============================================================

with photo_tab:

    render_photo_scanner()

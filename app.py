import os
import re
import json
import struct
import base64
import time
import queue
from io import BytesIO

import requests
import pandas as pd
import streamlit as st

from PIL import Image, ImageEnhance, ImageOps, ImageFilter

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
# SIMPLE GLOBAL STYLING
#
# IMPORTANT:
# No HTML cards are used below.
# Streamlit native containers/cards do the UI.
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem;
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
# MEGA FILE INDEX
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
# FIND PRODUCT IMAGE
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

    image_extensions = (
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
            image_extensions
        )
    ]

    # Exact filename
    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if stem == identifier:

                return node

    # Filename contains barcode/code
    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if identifier in stem:

                return node

    return None


# ============================================================
# DOWNLOAD MEGA IMAGE
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

    if len(key) < 8:

        raise RuntimeError(
            "Invalid MEGA file key."
        )

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

        if not chunk:
            continue

        output.write(
            decryptor.decrypt(chunk)
        )

    return output.getvalue()


# ============================================================
# BARCODE DECODER
# ============================================================

def decode_barcode_frame(
    frame_bgr
):

    """
    Try several intelligently selected versions of the
    camera frame.

    This is deliberately more aggressive than the previous
    snapshot-only scanner.
    """

    if frame_bgr is None:
        return None

    try:

        frame = frame_bgr.copy()

        height, width = frame.shape[:2]

        # ----------------------------------------------------
        # Resize to a useful processing size.
        # ----------------------------------------------------

        target_width = 1400

        if width > target_width:

            scale = (
                target_width / width
            )

            frame = cv2.resize(
                frame,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC,
            )

        height, width = frame.shape[:2]

        # ----------------------------------------------------
        # Candidate images.
        # ----------------------------------------------------

        candidates = []

        # Full image
        candidates.append(frame)

        # Central region
        x1 = int(width * 0.05)
        x2 = int(width * 0.95)

        y1 = int(height * 0.10)
        y2 = int(height * 0.90)

        candidates.append(
            frame[y1:y2, x1:x2]
        )

        # Central horizontal scanning area
        y1 = int(height * 0.25)
        y2 = int(height * 0.75)

        candidates.append(
            frame[y1:y2, :]
        )

        # ----------------------------------------------------
        # Process each candidate.
        # ----------------------------------------------------

        for image in candidates:

            if image is None:
                continue

            if image.size == 0:
                continue

            # Original
            versions = [
                image
            ]

            # Grayscale
            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY,
            )

            versions.append(gray)

            # CLAHE
            clahe = cv2.createCLAHE(
                clipLimit=2.0,
                tileGridSize=(8, 8),
            )

            enhanced = clahe.apply(
                gray
            )

            versions.append(
                enhanced
            )

            # OTSU threshold
            _, threshold = cv2.threshold(
                enhanced,
                0,
                255,
                cv2.THRESH_BINARY
                + cv2.THRESH_OTSU,
            )

            versions.append(
                threshold
            )

            # ------------------------------------------------
            # Decode
            # ------------------------------------------------

            for version in versions:

                try:

                    results = (
                        zxingcpp.read_barcodes(
                            version,
                            try_rotate=True,
                            try_downscale=False,
                            try_invert=True,
                        )
                    )

                except Exception:

                    continue

                for result in results:

                    if not result.valid:
                        continue

                    value = str(
                        result.text
                    ).strip()

                    if not value:
                        continue

                    # Remove accidental whitespace
                    value = re.sub(
                        r"\s+",
                        "",
                        value,
                    )

                    return {
                        "text": value,
                        "format": str(
                            result.format
                        ),
                    }

        return None

    except Exception:

        return None


# ============================================================
# LIVE CAMERA SCANNER
# ============================================================

def render_live_scanner():

    st.subheader(
        "📷 مسح الباركود"
    )

    st.caption(
        "وجّه الكاميرا نحو الباركود. "
        "عند التعرف عليه سيتم فتح المنتج تلقائياً."
    )

    if "scanner_enabled" not in st.session_state:

        st.session_state[
            "scanner_enabled"
        ] = False

    if "scanned_barcode" not in st.session_state:

        st.session_state[
            "scanned_barcode"
        ] = ""


    scanner_enabled = st.toggle(
        "تشغيل الكاميرا",
        value=st.session_state[
            "scanner_enabled"
        ],
        key="scanner_toggle",
    )

    st.session_state[
        "scanner_enabled"
    ] = scanner_enabled


    if not scanner_enabled:

        st.info(
            "فعّل الكاميرا لبدء مسح الباركود."
        )

        return


    # Queue shared between the camera callback
    # and Streamlit main thread.
    result_queue = queue.Queue(
        maxsize=1
    )

    last_scan_time = {
        "value": 0.0
    }


    def video_frame_callback(
        frame
    ):

        image = frame.to_ndarray(
            format="bgr24"
        )

        now = time.monotonic()

        # Don't run the decoder on every single frame.
        if (
            now
            - last_scan_time["value"]
            > 0.18
        ):

            last_scan_time[
                "value"
            ] = now

            decoded = (
                decode_barcode_frame(
                    image
                )
            )

            if decoded:

                try:

                    result_queue.put_nowait(
                        decoded
                    )

                except queue.Full:

                    pass

        # ----------------------------------------------------
        # Draw scanner guide
        # ----------------------------------------------------

        h, w = image.shape[:2]

        box_width = int(
            w * 0.78
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

        right = left + box_width
        bottom = top + box_height

        # Dark translucent-ish guide via lines.
        cv2.rectangle(
            image,
            (left, top),
            (right, bottom),
            (255, 255, 255),
            3,
        )

        # Corner markers
        corner = 35

        thickness = 6

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
        key="barcode-live-scanner",

        mode=WebRtcMode.SENDRECV,

        video_frame_callback=(
            video_frame_callback
        ),

        media_stream_constraints={
            "video": {
                "width": {
                    "ideal": 1280
                },
                "height": {
                    "ideal": 720
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
    # Wait for a result while the camera is active.
    # --------------------------------------------------------

    if ctx.state.playing:

        status = st.empty()

        status.info(
            "🔎 جاري البحث عن الباركود..."
        )

        while ctx.state.playing:

            try:

                result = (
                    result_queue.get(
                        timeout=0.25
                    )
                )

            except queue.Empty:

                continue

            barcode = result[
                "text"
            ]

            st.session_state[
                "scanned_barcode"
            ] = barcode

            st.session_state[
                "scanner_enabled"
            ] = False

            st.session_state[
                "scanner_toggle"
            ] = False

            st.rerun()


# ============================================================
# SEARCH / PRODUCT UI
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
            "لم يتم العثور على المنتج."
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


    # ========================================================
    # PRODUCT
    # ========================================================

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
    # PRODUCT HEADER
    # ========================================================

    st.success(
        "تم العثور على المنتج"
    )

    with st.container(
        border=True
    ):

        st.title(
            f"📦 {description}"
        )

        st.divider()

        info1, info2, info3 = (
            st.columns(
                3,
                gap="large",
            )
        )


        with info1:

            st.metric(
                "كود المنتج",
                code,
            )


        with info2:

            st.metric(
                "الباركود",
                barcode,
            )


        with info3:

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
                "لا توجد صورة مرتبطة بهذا "
                "الكود أو الباركود."
            )

            return


        image_bytes = (
            download_mega_image(
                image_node["handle"],
                image_node["key"],
            )
        )


        # ----------------------------------------------------
        # Resize image for a clean website presentation.
        # ----------------------------------------------------

        image = Image.open(
            BytesIO(image_bytes)
        )


        max_width = 520
        max_height = 620


        image.thumbnail(
            (
                max_width,
                max_height,
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
                width=500,
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
        "ملف DATABASE.xlsx غير موجود."
    )

    st.stop()


if df.empty:

    st.error(
        "ملف DATABASE.xlsx فارغ."
    )

    st.stop()


# ============================================================
# HEADER
# ============================================================

st.title(
    "📦 Holland Bazar T&D"
)

st.caption(
    "نظام البحث السريع عن المنتجات والمخزون"
)

st.divider()


# ============================================================
# SEARCH / SCANNER TABS
# ============================================================

search_tab, scanner_tab = st.tabs(
    [
        "🔎 البحث عن منتج",
        "📷 مسح الباركود",
    ]
)


# ============================================================
# SEARCH TAB
# ============================================================

with search_tab:

    scanned_value = st.session_state.get(
        "scanned_barcode",
        "",
    )


    search_query = st.text_input(
        "الباركود أو كود المنتج",
        value=scanned_value,
        placeholder="مثال: 6932308668058",
        key="product_search",
    ).strip()


    if scanned_value:

        st.success(
            f"تمت قراءة الباركود من الكاميرا: "
            f"{scanned_value}"
        )


        if st.button(
            "مسح نتيجة المسح",
            use_container_width=True,
        ):

            st.session_state[
                "scanned_barcode"
            ] = ""

            st.rerun()


    if search_query:

        render_product(
            df,
            search_query,
        )

    else:

        st.info(
            "أدخل الباركود أو كود المنتج، "
            "أو استخدم تبويب «مسح الباركود»."
        )


# ============================================================
# SCANNER TAB
# ============================================================

with scanner_tab:

    render_live_scanner()

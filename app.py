
import os
import re
import json
import struct
import base64
from io import BytesIO

import requests
import pandas as pd
import streamlit as st
from PIL import Image
from Crypto.Cipher import AES


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Holland Bazar T&D",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

EXCEL_PATH = "DATABASE.xlsx"

# Your existing public MEGA folder.
# Keep this value unchanged if your folder is unchanged.
MEGA_FOLDER_URL = (
    "https://mega.nz/folder/HrximbwC"
    "#9wvR9D8OQnrAJlTItE6Oag"
)

MEGA_API = "https://g.api.mega.co.nz/cs"


# ============================================================
# NATIVE STREAMLIT UI STYLING
#
# IMPORTANT:
# The previous version used large amounts of raw HTML in
# st.markdown(). This version deliberately does NOT do that.
# The visible application UI is built with Streamlit widgets,
# containers, columns and metrics, so HTML source cannot appear
# as text in the page.
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(
                circle at 90% 0%,
                rgba(34,197,94,.08),
                transparent 28%
            ),
            #07111f;
    }

    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #20344d !important;
        border-radius: 18px !important;
        background: rgba(13,27,42,.72) !important;
    }

    div[data-testid="stMetric"] {
        background: #091829;
        border: 1px solid #1e3851;
        padding: 15px;
        border-radius: 14px;
    }

    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.25rem !important;
    }

    div[data-testid="stTextInput"] input {
        direction: ltr !important;
        text-align: left !important;
        min-height: 48px;
        border-radius: 12px;
        background: #081525;
        border-color: #29425e;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #22c55e;
        box-shadow: 0 0 0 1px #22c55e;
    }

    button[kind="primary"] {
        border-radius: 11px !important;
    }

    div[data-testid="stTabs"] button {
        font-weight: 750;
    }

    .small-muted {
        color: #94a3b8;
        font-size: .88rem;
    }

    .success-line {
        color: #86efac;
        font-weight: 700;
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: .75rem;
            padding-right: .75rem;
            padding-top: 1rem;
        }
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

    df = pd.read_excel(
        EXCEL_PATH,
        dtype=str,
    )

    df.columns = [
        str(i)
        for i in range(len(df.columns))
    ]

    for col in df.columns:
        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    return df


df = load_data()

if df is None:
    st.error("ملف DATABASE.xlsx غير موجود في المشروع.")
    st.stop()

if df.empty:
    st.error("ملف DATABASE.xlsx موجود لكنه فارغ.")
    st.stop()

required_columns = {"0", "1", "2", "3"}

if not required_columns.issubset(df.columns):
    st.error(
        "DATABASE.xlsx يجب أن يحتوي على الأعمدة الأربعة الأولى: "
        "0 = الكود، 1 = الباركود، 2 = الوصف، 3 = الكمية."
    )
    st.stop()


# ============================================================
# MEGA PUBLIC-FOLDER READER
# ============================================================

def mega_b64_decode(value):
    if isinstance(value, str):
        value = value.encode()

    value += b"=" * (-len(value) % 4)

    return base64.urlsafe_b64decode(value)


def base64_to_a32(value):
    raw = mega_b64_decode(value)

    return struct.unpack(
        ">" + ("I" * (len(raw) // 4)),
        raw,
    )


def a32_to_bytes(values):
    return struct.pack(
        ">" + ("I" * len(values)),
        *values,
    )


def decrypt_key(encrypted_key, key):
    cipher = AES.new(
        a32_to_bytes(key),
        AES.MODE_ECB,
    )

    raw = cipher.decrypt(
        a32_to_bytes(encrypted_key)
    )

    return struct.unpack(
        ">" + ("I" * (len(raw) // 4)),
        raw,
    )


def decrypt_attributes(encrypted_attributes, key):
    encrypted = mega_b64_decode(
        encrypted_attributes
    )

    cipher = AES.new(
        a32_to_bytes(key),
        AES.MODE_CBC,
        iv=b"\x00" * 16,
    )

    decrypted = cipher.decrypt(
        encrypted
    ).rstrip(b"\x00")

    if not decrypted.startswith(b"MEGA"):
        raise ValueError(
            "Invalid MEGA attribute prefix"
        )

    return json.loads(
        decrypted[4:].decode("utf-8")
    )


def parse_mega_folder_url(url):
    match = re.search(
        r"mega\.nz/folder/([^#/?]+)#([^/?]+)",
        url,
    )

    if not match:
        raise ValueError("Invalid MEGA folder URL")

    return match.group(1), match.group(2)


def mega_api_request(data, folder_handle=None):
    params = {"id": 0}

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

    if not result:
        raise RuntimeError("MEGA returned no data.")

    if isinstance(result[0], int):
        raise RuntimeError(
            f"MEGA API error: {result[0]}"
        )

    return result[0]


@st.cache_data(ttl=3600, show_spinner=False)
def get_mega_nodes():
    folder_handle, folder_key_text = (
        parse_mega_folder_url(MEGA_FOLDER_URL)
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
        folder_handle,
    )

    output = []

    for node in response.get("f", []):
        if node.get("t") != 0:
            continue

        encrypted_node_key = node.get("k")
        encrypted_attributes = node.get("a")
        node_handle = node.get("h")

        if (
            not encrypted_node_key
            or not encrypted_attributes
            or not node_handle
        ):
            continue

        try:
            if ":" in encrypted_node_key:
                encrypted_node_key = (
                    encrypted_node_key.split(":", 1)[1]
                )

            encrypted_key = base64_to_a32(
                encrypted_node_key
            )

            node_key = decrypt_key(
                encrypted_key,
                shared_key,
            )

            if len(node_key) < 8:
                continue

            file_key = (
                node_key[0] ^ node_key[4],
                node_key[1] ^ node_key[5],
                node_key[2] ^ node_key[6],
                node_key[3] ^ node_key[7],
            )

            attributes = decrypt_attributes(
                encrypted_attributes,
                file_key,
            )

            filename = attributes.get("n", "")

            if filename:
                output.append(
                    {
                        "handle": node_handle,
                        "name": filename,
                        "key": list(node_key),
                    }
                )

        except Exception:
            continue

    return output


def find_mega_image(nodes, code, barcode):
    identifiers = []

    for value in (barcode, code):
        value = str(value or "").strip().lower()

        if value and value != "nan":
            identifiers.append(value)

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
        if node["name"].lower().endswith(extensions)
    ]

    # Exact filename match.
    for identifier in identifiers:
        for node in files:
            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if stem == identifier:
                return node

    # Partial filename match.
    for identifier in identifiers:
        for node in files:
            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if identifier in stem:
                return node

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def download_mega_image(node_handle, node_key):
    folder_handle, _ = parse_mega_folder_url(
        MEGA_FOLDER_URL
    )

    response = mega_api_request(
        {
            "a": "g",
            "g": 1,
            "n": node_handle,
        },
        folder_handle,
    )

    download_url = response.get("g")

    if not download_url:
        raise RuntimeError(
            "MEGA download URL unavailable."
        )

    key = tuple(node_key)

    aes_key = a32_to_bytes(
        (
            key[0] ^ key[4],
            key[1] ^ key[5],
            key[2] ^ key[6],
            key[3] ^ key[7],
        )
    )

    iv = a32_to_bytes(
        (
            key[4],
            key[5],
            0,
            0,
        )
    )

    cipher = AES.new(
        aes_key,
        AES.MODE_CTR,
        nonce=iv[:8],
        initial_value=int.from_bytes(
            iv[8:],
            "big",
        ),
    )

    response = requests.get(
        download_url,
        stream=True,
        timeout=120,
    )

    response.raise_for_status()

    result = BytesIO()

    for chunk in response.iter_content(
        1024 * 1024
    ):
        if chunk:
            result.write(
                cipher.decrypt(chunk)
            )

    return result.getvalue()


# ============================================================
# BARCODE SCANNER
#
# The previous scanner crashed because it referenced
# Html5QrcodeSupportedFormats BEFORE the external html5-qrcode
# script had finished loading.
#
# This version waits for the library to load, then reads the
# supported-format constants from window.Html5QrcodeSupportedFormats.
# ============================================================


# ============================================================
# NATIVE CAMERA BARCODE SCANNER — V5
#
# Camera:
#   Streamlit native st.camera_input()
#
# Decoder:
#   ZXing-C++ Python bindings (zxingcpp)
#
# Why ZXing-C++:
#   It is a dedicated multi-format barcode reader and supports
#   retail/warehouse formats including EAN/UPC, Code 128,
#   Code 39/93, ITF and Codabar. It also has built-in rotation,
#   downscale and invert attempts.
# ============================================================

from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import numpy as np
import cv2

try:
    import zxingcpp
    ZXING_AVAILABLE = True
except Exception:
    zxingcpp = None
    ZXING_AVAILABLE = False


def _barcode_text(value):
    """Normalize ZXing output for database matching."""
    if value is None:
        return ""

    value = str(value).strip()

    # Keep barcode data intact. Only remove accidental whitespace.
    return "".join(value.split())


def _decode_zxing(image):
    """
    Run ZXing-C++ with its own robust reader options.

    ZXing-C++ supports:
      - rotation search
      - downscale search
      - inverted barcode search
      - local-average binarization by default

    We deliberately do not restrict the format list, because
    warehouse labels may be Code128, EAN/UPC, ITF, etc.
    """
    if not ZXING_AVAILABLE:
        return []

    try:
        results = zxingcpp.read_barcodes(
            image,
            try_rotate=True,
            try_downscale=True,
            try_invert=True,
            return_errors=False,
        )
    except Exception:
        return []

    decoded = []

    for item in results:
        text_value = _barcode_text(
            getattr(item, "text", "")
        )

        if not text_value:
            continue

        decoded.append(
            {
                "value": text_value,
                "type": str(
                    getattr(
                        item,
                        "format",
                        "UNKNOWN",
                    )
                ),
                "position": getattr(
                    item,
                    "position",
                    None,
                ),
            }
        )

    return decoded


def _image_variants(pil_image):
    """
    Generate a small, deliberate set of high-value variants.

    We do not destroy the original image or aggressively blur it.
    The goal is to preserve the narrow barcode bars while giving
    ZXing a few different representations to work with.
    """
    image = pil_image.convert("RGB")

    # Keep enough resolution for small labels.
    max_dimension = 3000

    if max(image.size) > max_dimension:
        scale = max_dimension / max(image.size)
        image = image.resize(
            (
                max(1, int(image.width * scale)),
                max(1, int(image.height * scale)),
            ),
            Image.Resampling.LANCZOS,
        )

    yield ("original", image)

    gray = ImageOps.grayscale(image)
    yield ("gray", gray)

    # Moderate contrast.
    contrast = ImageEnhance.Contrast(gray).enhance(1.7)
    yield ("contrast", contrast)

    # Moderate sharpening.
    sharp = contrast.filter(
        ImageFilter.UnsharpMask(
            radius=1.2,
            percent=150,
            threshold=3,
        )
    )
    yield ("sharp", sharp)

    # Upscale grayscale for small printed labels.
    upscale = gray.resize(
        (
            gray.width * 2,
            gray.height * 2,
        ),
        Image.Resampling.LANCZOS,
    )
    yield ("upscale", upscale)

    # OpenCV adaptive threshold is useful when the warehouse
    # lighting is uneven.
    arr = np.array(gray)
    adaptive = cv2.adaptiveThreshold(
        arr,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        7,
    )
    yield (
        "adaptive",
        Image.fromarray(adaptive),
    )

    # Otsu threshold.
    _, otsu = cv2.threshold(
        arr,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    yield (
        "otsu",
        Image.fromarray(otsu),
    )

    # Inverted barcode.
    yield (
        "inverted",
        ImageOps.invert(gray),
    )


def _crop_barcode_regions(pil_image):
    """
    Use OpenCV's barcode detector only as a LOCALIZER.

    It is not our main decoder. If OpenCV can locate a barcode
    quadrilateral, crop it with generous margins and let ZXing-C++
    do the actual decoding.
    """
    crops = []

    try:
        detector = cv2.barcode_BarcodeDetector()
    except Exception:
        return crops

    try:
        image = cv2.cvtColor(
            np.array(pil_image.convert("RGB")),
            cv2.COLOR_RGB2BGR,
        )

        ok, decoded_info, points, _ = (
            detector.detectAndDecodeMulti(image)
        )

        if not ok or points is None:
            return crops

        points = np.asarray(points)

        for idx, polygon in enumerate(points):
            polygon = np.asarray(
                polygon,
                dtype=np.float32,
            ).reshape(-1, 2)

            if polygon.shape[0] < 4:
                continue

            x1 = max(
                0,
                int(np.min(polygon[:, 0])) - 60,
            )
            y1 = max(
                0,
                int(np.min(polygon[:, 1])) - 60,
            )
            x2 = min(
                image.shape[1],
                int(np.max(polygon[:, 0])) + 60,
            )
            y2 = min(
                image.shape[0],
                int(np.max(polygon[:, 1])) + 60,
            )

            if x2 <= x1 or y2 <= y1:
                continue

            crop = image[y1:y2, x1:x2]

            if crop.size == 0:
                continue

            crop_rgb = cv2.cvtColor(
                crop,
                cv2.COLOR_BGR2RGB,
            )

            crops.append(
                (
                    f"localized-{idx + 1}",
                    Image.fromarray(crop_rgb),
                )
            )

    except Exception:
        pass

    return crops


def barcode_candidates_from_image(uploaded_file):
    """
    Main decoder.

    Strategy:
      1. Decode original image with ZXing-C++.
      2. Try localized barcode crops.
      3. Try enhanced image variants.
      4. Try center/landscape crops for phone photos.
      5. Deduplicate results.
    """
    if not uploaded_file or not ZXING_AVAILABLE:
        return []

    try:
        image = Image.open(uploaded_file).convert("RGB")
    except Exception:
        return []

    attempts = []

    # Original first: never throw away information.
    attempts.append(
        ("original", image)
    )

    # Barcode localizer crops.
    attempts.extend(
        _crop_barcode_regions(image)
    )

    # Center crop: useful when the user follows the scanner
    # guide and places the barcode in the middle of the frame.
    w, h = image.size

    cx1 = int(w * 0.05)
    cx2 = int(w * 0.95)
    cy1 = int(h * 0.20)
    cy2 = int(h * 0.80)

    if cx2 > cx1 and cy2 > cy1:
        attempts.append(
            (
                "center",
                image.crop(
                    (cx1, cy1, cx2, cy2)
                ),
            )
        )

    # Try a broad horizontal band. This is especially useful for
    # labels where the barcode occupies the middle third.
    by1 = int(h * 0.25)
    by2 = int(h * 0.75)

    if by2 > by1:
        attempts.append(
            (
                "middle-band",
                image.crop(
                    (0, by1, w, by2)
                ),
            )
        )

    # Add enhanced variants.
    attempts.extend(
        list(_image_variants(image))
    )

    found = {}

    # Prevent an excessive number of expensive attempts.
    for attempt_name, candidate in attempts[:14]:
        decoded = _decode_zxing(candidate)

        for item in decoded:
            value = item["value"]

            if not value:
                continue

            key = (
                value,
                item["type"],
            )

            if key not in found:
                found[key] = {
                    "value": value,
                    "type": item["type"],
                    "attempt": attempt_name,
                }

    results = list(found.values())

    # Prefer:
    #   1. exact database matches
    #   2. numeric retail barcodes
    #   3. longer values
    def score(item):
        value = item["value"]

        exact = not df[
            (df["0"] == value)
            | (df["1"] == value)
        ].empty

        numeric = value.isdigit()

        return (
            int(exact),
            int(numeric),
            len(value),
        )

    results.sort(
        key=score,
        reverse=True,
    )

    return results


def barcode_matches_database(results):
    if not results:
        return None

    for result in results:
        value = result["value"]

        exact = df[
            (df["0"] == value)
            | (df["1"] == value)
        ]

        if not exact.empty:
            return result

    return results[0]


def camera_scanner_ui():
    st.subheader("📷 قارئ الباركود")

    st.caption(
        "صوّر الباركود بوضوح. لا تحتاج إلى التقاط المنتج كاملاً؛ "
        "اجعل الباركود كبيراً ومستقيماً داخل الصورة."
    )

    with st.container(border=True):

        st.markdown(
            "### 📸 تصوير الباركود"
        )

        st.info(
            "أفضل نتيجة: قرّب الهاتف حتى تملأ خطوط الباركود "
            "معظم عرض الصورة، وتجنب اللمعان والاهتزاز."
        )

        camera_photo = st.camera_input(
            "التقاط صورة للباركود",
            key="warehouse_barcode_camera_v5",
            resolution="1080p",
            label_visibility="visible",
        )

    uploaded_photo = st.file_uploader(
        "أو اختر صورة من الجهاز",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
        ],
        key="barcode_image_upload_v5",
    )

    photo = (
        camera_photo
        if camera_photo is not None
        else uploaded_photo
    )

    if photo is None:
        return

    st.divider()

    left, right = st.columns(
        [1.45, 1],
        gap="large",
    )

    with left:
        st.image(
            photo,
            caption="الصورة الملتقطة",
            width="stretch",
        )

    with right:

        if not ZXING_AVAILABLE:
            st.error(
                "محرك ZXing-C++ غير مثبت. "
                "تأكد من وجود zxing-cpp في requirements.txt."
            )
            return

        with st.spinner(
            "جاري تحليل الباركود..."
        ):
            results = (
                barcode_candidates_from_image(
                    photo
                )
            )

        if not results:
            st.error(
                "لم أستطع قراءة الباركود من هذه الصورة."
            )

            st.markdown(
                """
                **جرّب هذه الشروط:**
                - اجعل الباركود يملأ معظم الصورة.
                - أبقِ الهاتف ثابتاً.
                - اجعل الخطوط أفقية قدر الإمكان.
                - لا تستخدم فلاشاً ينعكس على الملصق.
                - تأكد أن الأطراف البيضاء للباركود ظاهرة.
                """
            )

            return

        best = barcode_matches_database(
            results
        )

        st.success(
            "✓ تم التعرف على الباركود"
        )

        st.metric(
            "الباركود",
            best["value"],
        )

        st.caption(
            f"النوع: {best['type']}  •  "
            f"طريقة القراءة: {best['attempt']}"
        )

        matching = df[
            (df["0"] == best["value"])
            | (df["1"] == best["value"])
        ]

        if not matching.empty:
            st.success(
                "تم العثور على المنتج في المخزون."
            )
            show_product(
                matching.iloc[0]
            )
        else:
            st.warning(
                "تمت قراءة الباركود، "
                "لكن الرقم غير موجود في قاعدة البيانات."
            )

            show_similar(
                best["value"]
            )

        if len(results) > 1:
            with st.expander(
                "قراءات أخرى من الصورة"
            ):
                for result in results[:8]:
                    st.write(
                        f"**{result['value']}** — "
                        f"{result['type']} — "
                        f"{result['attempt']}"
                    )



# ============================================================
# PRODUCT SEARCH
# ============================================================

def find_product(query):
    query = str(query).strip()

    if not query:
        return None

    exact = df[
        (df["0"] == query)
        | (df["1"] == query)
    ]

    if exact.empty:
        return None

    return exact.iloc[0]


def show_product(row):
    code = str(row["0"]).strip()
    barcode = str(row["1"]).strip()
    description = str(row["2"]).strip()
    quantity = str(row["3"]).strip()

    if not barcode or barcode.lower() == "nan":
        barcode = "غير متوفر"

    if not description or description.lower() == "nan":
        description = "غير متوفر"

    if not quantity or quantity.lower() == "nan":
        quantity = "0"

    st.success("تم العثور على المنتج")

    with st.container(border=True):
        st.subheader(description)

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("كود المنتج", code)

        with c2:
            st.metric("الباركود", barcode)

        with c3:
            st.metric("الكمية الحالية", quantity)

    with st.container(border=True):
        st.subheader("🖼️ صورة المنتج")

        try:
            with st.spinner("جاري تحميل صورة المنتج..."):
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
                else:
                    image_bytes = download_mega_image(
                        image_node["handle"],
                        image_node["key"],
                    )

                    image = Image.open(
                        BytesIO(image_bytes)
                    )

                    st.image(
                        image,
                        width="stretch",
                    )

        except Exception as error:
            st.warning(
                f"تعذر تحميل صورة المنتج: {error}"
            )


def show_similar(query):
    similar = df[
        df["0"].str.contains(
            query,
            case=False,
            na=False,
            regex=False,
        )
        |
        df["1"].str.contains(
            query,
            case=False,
            na=False,
            regex=False,
        )
    ].head(5)

    if similar.empty:
        return

    st.subheader("نتائج مشابهة")

    for _, row in similar.iterrows():
        with st.container(border=True):
            st.write(
                f"**{row['2']}**"
            )
            st.caption(
                f"الكود: {row['0']}  •  "
                f"الباركود: {row['1']}"
            )


def perform_search(query):
    query = str(query).strip()

    if not query:
        return

    row = find_product(query)

    if row is None:
        st.error(
            "لم يتم العثور على منتج بهذا الباركود أو الكود."
        )
        show_similar(query)
        return

    show_product(row)


# ============================================================
# HEADER
# ============================================================

st.title("Holland Bazar T&D 📦")
st.caption(
    "نظام البحث عن المنتجات والمخزون — نسخة تجريبية"
)

st.divider()


# ============================================================
# TABS
# ============================================================

search_tab, scanner_tab = st.tabs(
    [
        "🔎 البحث عن منتج",
        "📷 مسح الباركود",
    ]
)


# ============================================================
# MANUAL SEARCH
# ============================================================

with search_tab:

    with st.container(border=True):

        st.subheader("البحث عن منتج")
        st.caption(
            "أدخل الباركود أو كود المنتج للعثور على بيانات المخزون."
        )

        manual_query = st.text_input(
            "الباركود أو الكود",
            placeholder="مثال: 6820468232713",
            key="manual_query",
        )

        if manual_query:
            perform_search(
                manual_query
            )


# ============================================================
# CAMERA SCANNER
# ============================================================



with scanner_tab:

    camera_scanner_ui()

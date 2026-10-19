import os
import re
import json
import struct
import base64
from io import BytesIO

import requests
import pandas as pd
import streamlit as st

from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from Crypto.Cipher import AES
from Crypto.Util import Counter

import zxingcpp


# ============================================================
# PAGE CONFIG
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
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* =====================================================
       GLOBAL
       ===================================================== */

    .stApp {
        background:
            radial-gradient(
                circle at top right,
                rgba(46, 125, 50, 0.08),
                transparent 30%
            ),
            #0b0f14;

        color: #f8fafc;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* =====================================================
       HEADER
       ===================================================== */

    .app-header {
        text-align: center;
        margin-bottom: 1.5rem;
    }

    .app-title {
        font-size: clamp(26px, 4vw, 42px);
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 5px;
    }

    .app-subtitle {
        color: #94a3b8;
        font-size: 14px;
    }

    /* =====================================================
       SEARCH
       ===================================================== */

    .search-label {
        text-align: right;
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    /* =====================================================
       CAMERA CARD
       ===================================================== */

    .camera-card {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 20px;
    }

    .camera-title {
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .camera-description {
        color: #94a3b8;
        font-size: 13px;
        margin-bottom: 12px;
    }

    /* =====================================================
       PRODUCT CARD
       ===================================================== */

    .product-card {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 20px;
        padding: 24px;
        margin-top: 20px;
        margin-bottom: 18px;
    }

    .product-heading {
        font-size: 25px;
        font-weight: 800;
        margin-bottom: 22px;
        line-height: 1.4;
    }

    .info-card {
        background: #182131;
        border: 1px solid #29374a;
        border-radius: 14px;
        padding: 16px;
        height: 100%;
    }

    .info-label {
        color: #94a3b8;
        font-size: 12px;
        margin-bottom: 7px;
    }

    .info-value {
        color: #f8fafc;
        font-size: 17px;
        font-weight: 700;
        word-break: break-word;
    }

    /* =====================================================
       QUANTITY
       ===================================================== */

    .quantity-card {
        background:
            linear-gradient(
                135deg,
                #14532d,
                #166534
            );

        border: 1px solid #22c55e;
        border-radius: 18px;
        padding: 20px;
        text-align: center;
        margin-top: 18px;
    }

    .quantity-number {
        font-size: clamp(34px, 5vw, 48px);
        font-weight: 900;
        line-height: 1;
    }

    .quantity-label {
        margin-top: 8px;
        color: #bbf7d0;
        font-size: 13px;
    }

    /* =====================================================
       IMAGE
       ===================================================== */

    .image-card {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 20px;
        padding: 20px;
        margin-top: 20px;
    }

    .section-title {
        font-size: 20px;
        font-weight: 800;
        margin-bottom: 12px;
    }

    .image-name {
        color: #64748b;
        text-align: center;
        font-size: 12px;
        margin-top: 8px;
    }

    /* =====================================================
       CAMERA RESULT
       ===================================================== */

    .scan-success {
        background: #052e16;
        border: 1px solid #166534;
        border-radius: 12px;
        padding: 12px 15px;
        margin: 10px 0 15px 0;
        text-align: center;
        color: #bbf7d0;
        font-weight: 700;
    }

    /* =====================================================
       SUGGESTIONS
       ===================================================== */

    .suggestion-card {
        background: #111827;
        border: 1px solid #263244;
        border-radius: 14px;
        padding: 14px 16px;
        margin: 8px 0;
    }

    .suggestion-title {
        font-weight: 700;
        font-size: 15px;
    }

    .suggestion-details {
        color: #94a3b8;
        font-size: 12px;
        margin-top: 5px;
    }

    /* =====================================================
       MOBILE
       ===================================================== */

    @media (max-width: 700px) {

        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-top: 1rem;
        }

        .product-card,
        .image-card,
        .camera-card {
            padding: 15px;
            border-radius: 15px;
        }

        .product-heading {
            font-size: 21px;
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


def mega_b64_encode(value):

    return (
        base64.urlsafe_b64encode(value)
        .decode("utf-8")
        .rstrip("=")
    )


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

    json_data = decrypted[4:]

    return json.loads(
        json_data.decode("utf-8")
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
# GET MEGA NODES
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

    # Exact match first
    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if stem == identifier:

                return node

    # Partial match second
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
# BARCODE SCANNER
# ============================================================

def decode_barcode(image_bytes):

    """
    Decode barcodes from the camera image.

    ZXing supports EAN, UPC, Code 128 and many
    other retail/industrial barcode formats.
    """

    try:

        image = Image.open(
            BytesIO(image_bytes)
        ).convert("RGB")

    except Exception:

        return []


    # --------------------------------------------------------
    # Images to test
    # --------------------------------------------------------

    variants = []

    # Original
    variants.append(image)

    # Upscaled
    width, height = image.size

    if width < 1600:

        scale = 1600 / width

        enlarged = image.resize(
            (
                int(width * scale),
                int(height * scale),
            ),
            Image.Resampling.LANCZOS,
        )

        variants.append(enlarged)

    else:

        enlarged = image

    # Grayscale
    gray = ImageOps.grayscale(
        enlarged
    )

    variants.append(gray)

    # Contrast
    contrast = ImageEnhance.Contrast(
        gray
    ).enhance(1.8)

    variants.append(contrast)

    # Sharpen
    sharpened = contrast.filter(
        ImageFilter.SHARPEN
    )

    variants.append(sharpened)

    # Rotations
    variants.append(
        enlarged.rotate(
            90,
            expand=True,
        )
    )

    variants.append(
        enlarged.rotate(
            270,
            expand=True,
        )
    )


    # --------------------------------------------------------
    # Decode
    # --------------------------------------------------------

    found = []

    seen = set()

    for variant in variants:

        try:

            results = zxingcpp.read_barcodes(
                variant,
                try_rotate=True,
                try_downscale=True,
                try_invert=True,
            )

        except Exception:

            continue

        for result in results:

            value = str(
                result.text
            ).strip()

            if not value:
                continue

            if value in seen:
                continue

            seen.add(value)

            found.append(
                {
                    "text": value,
                    "format": str(
                        result.format
                    ),
                }
            )

    return found


# ============================================================
# IMAGE DISPLAY
# ============================================================

def display_product_image(
    image_bytes,
    filename,
):

    try:

        image = Image.open(
            BytesIO(image_bytes)
        )

        # Keep the image's proportions.
        # Limit giant portrait images so they don't
        # take over the entire page.

        max_height = 720

        width, height = image.size

        if height > max_height:

            ratio = (
                max_height
                / height
            )

            image = image.resize(
                (
                    int(width * ratio),
                    max_height,
                ),
                Image.Resampling.LANCZOS,
            )

        st.image(
            image,
            width="stretch",
        )

        st.markdown(
            f'<div class="image-name">'
            f'{filename}'
            f'</div>',
            unsafe_allow_html=True,
        )

    except Exception:

        st.image(
            image_bytes,
            width="stretch",
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="app-header">

        <div class="app-title">
            📦 Holland Bazar T&D
        </div>

        <div class="app-subtitle">
            نظام البحث عن المنتجات والمخزون
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATABASE
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
# CAMERA SCANNER
# ============================================================

st.markdown(
    """
    <div class="camera-card">

        <div class="camera-title">
            📷 مسح الباركود بالكاميرا
        </div>

        <div class="camera-description">
            وجّه الكاميرا نحو الباركود ثم التقط صورة.
            سيقرأ النظام الباركود ويبحث عن المنتج تلقائياً.
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


camera_image = st.camera_input(
    "📷 التقاط الباركود",
    key="barcode_camera",
)


# ============================================================
# CAMERA PROCESSING
# ============================================================

if camera_image is not None:

    scanned = decode_barcode(
        camera_image.getvalue()
    )

    if scanned:

        # Use the first detected barcode
        detected_value = scanned[0]["text"]

        st.session_state[
            "camera_barcode"
        ] = detected_value

        st.markdown(
            f"""
            <div class="scan-success">
                ✅ تم قراءة الباركود:
                <br>
                <strong>{detected_value}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.warning(
            "⚠️ لم يتم التعرف على الباركود. "
            "حاول تقريب الكاميرا، تحسين الإضاءة، "
            "وجعل الخطوط السوداء للباركود واضحة."
        )


# ============================================================
# SEARCH VALUE
# ============================================================

camera_value = st.session_state.get(
    "camera_barcode",
    "",
)


search_query = st.text_input(
    "🔎 الباركود أو الكود",
    value=camera_value,
    key="main_search",
    placeholder="مثال: 6932308668058",
)


search_query = search_query.strip()


# ============================================================
# CLEAR SCAN
# ============================================================

if camera_value:

    if st.button(
        "🧹 مسح البحث والبدء من جديد",
        use_container_width=True,
    ):

        st.session_state.pop(
            "camera_barcode",
            None,
        )

        st.rerun()


# ============================================================
# WAITING
# ============================================================

if not search_query:

    st.info(
        "👆 أدخل الكود يدوياً أو استخدم الكاميرا لمسح الباركود."
    )

    st.stop()


# ============================================================
# DATABASE COLUMNS
# ============================================================

col_code = "0"
col_barcode = "1"
col_desc = "2"
col_qty = "3"


# ============================================================
# SEARCH
# ============================================================

matches = df[
    (df[col_barcode] == search_query)
    |
    (df[col_code] == search_query)
]


# ============================================================
# PRODUCT FOUND
# ============================================================

if not matches.empty:

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


    if not barcode or barcode.lower() == "nan":
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
    # PRODUCT INFORMATION
    # ========================================================

    st.markdown(
        '<div class="product-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="product-heading">
            📦 {description}
        </div>
        """,
        unsafe_allow_html=True,
    )


    info_col1, info_col2 = st.columns(
        2,
        gap="medium",
    )


    with info_col1:

        st.markdown(
            f"""
            <div class="info-card">

                <div class="info-label">
                    🔢 كود المنتج
                </div>

                <div class="info-value">
                    {code}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with info_col2:

        st.markdown(
            f"""
            <div class="info-card">

                <div class="info-label">
                    🏷️ الباركود
                </div>

                <div class="info-value">
                    {barcode}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    st.markdown(
        f"""
        <div class="quantity-card">

            <div class="quantity-number">
                {quantity}
            </div>

            <div class="quantity-label">
                الكمية المتوفرة
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        '</div>',
        unsafe_allow_html=True,
    )


    # ========================================================
    # PRODUCT IMAGE
    # ========================================================

    st.markdown(
        '<div class="image-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title">'
        '🖼️ صورة المنتج'
        '</div>',
        unsafe_allow_html=True,
    )


    try:

        with st.spinner(
            "جاري البحث عن صورة المنتج..."
        ):

            nodes = get_mega_nodes()

            image_node = find_mega_image(
                nodes,
                code,
                barcode,
            )


        if image_node is None:

            st.warning(
                "📷 لم يتم العثور على صورة بهذا "
                "الكود أو الباركود."
            )

        else:

            with st.spinner(
                "جاري تحميل صورة المنتج..."
            ):

                image_bytes = (
                    download_mega_image(
                        image_node["handle"],
                        image_node["key"],
                    )
                )


            display_product_image(
                image_bytes,
                image_node["name"],
            )


    except Exception as e:

        st.error(
            f"❌ خطأ في تحميل صورة MEGA: {e}"
        )


    st.markdown(
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# PRODUCT NOT FOUND
# ============================================================

else:

    st.error(
        "❌ لم يتم العثور على المنتج بهذا "
        "الباركود أو الكود."
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

        st.markdown(
            "### 💡 هل تقصد أحد هذه المنتجات؟"
        )


        for _, suggestion in (
            similar.head(5).iterrows()
        ):

            suggestion_code = str(
                suggestion[col_code]
            ).strip()

            suggestion_barcode = str(
                suggestion[col_barcode]
            ).strip()

            suggestion_description = str(
                suggestion[col_desc]
            ).strip()


            st.markdown(
                f"""
                <div class="suggestion-card">

                    <div class="suggestion-title">
                        📦 {suggestion_description}
                    </div>

                    <div class="suggestion-details">
                        الكود: {suggestion_code}
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        الباركود: {suggestion_barcode}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

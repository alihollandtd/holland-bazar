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

import cv2
import numpy as np

from Crypto.Cipher import AES

from pyzbar.pyzbar import decode as zbar_decode
from pyzbar.pyzbar import ZBarSymbol


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Holland Bazar T&D",
    page_icon="📦",
    layout="centered",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .hero {
        background: linear-gradient(
            135deg,
            #14532d,
            #166534
        );
        padding: 24px;
        border-radius: 18px;
        margin-bottom: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 25px rgba(0,0,0,.25);
    }

    .hero h1 {
        margin: 0;
        font-size: 32px;
    }

    .hero p {
        margin-top: 8px;
        opacity: .85;
    }

    .scan-box {
        border: 3px solid #22c55e;
        border-radius: 18px;
        padding: 18px;
        background: #111827;
        text-align: center;
        margin: 15px 0;
    }

    .scan-title {
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .scan-help {
        color: #9ca3af;
        font-size: 14px;
        line-height: 1.7;
    }

    .barcode-result {
        background: #052e16;
        border: 2px solid #22c55e;
        border-radius: 14px;
        padding: 18px;
        text-align: center;
        margin: 15px 0;
    }

    .barcode-number {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: 2px;
        color: #86efac;
    }

    .product-card {
        background: #111827;
        border: 1px solid #374151;
        border-radius: 18px;
        padding: 22px;
        margin-top: 20px;
    }

    .product-title {
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 20px;
    }

    .metric-card {
        background: #1f2937;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        border: 1px solid #374151;
    }

    .metric-value {
        font-size: 22px;
        font-weight: 800;
        color: #ffffff;
        word-break: break-word;
    }

    .metric-label {
        color: #9ca3af;
        font-size: 13px;
        margin-top: 5px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE
# ============================================================

EXCEL_PATH = "DATABASE.xlsx"


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


# ============================================================
# MEGA
# ============================================================

MEGA_FOLDER_URL = (
    "https://mega.nz/folder/HrximbwC"
    "#9wvR9D8OQnrAJlTItE6Oag"
)

MEGA_API = "https://g.api.mega.co.nz/cs"


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


def decrypt_key(
    encrypted_key,
    key,
):

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


def decrypt_attributes(
    encrypted_attributes,
    key,
):

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
    )

    decrypted = decrypted.rstrip(
        b"\x00"
    )

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
        raise ValueError(
            "Invalid MEGA folder URL"
        )

    return (
        match.group(1),
        match.group(2),
    )


def mega_api_request(
    data,
    folder_handle=None,
):

    params = {
        "id": 0
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

    if not result:
        raise RuntimeError(
            "MEGA returned no data."
        )

    if isinstance(result[0], int):
        raise RuntimeError(
            f"MEGA API error: {result[0]}"
        )

    return result[0]


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
        folder_handle,
    )

    nodes = response.get(
        "f",
        []
    )

    output = []

    for node in nodes:

        if node.get("t") != 0:
            continue

        encrypted_node_key = node.get("k")
        encrypted_attributes = node.get("a")
        node_handle = node.get("h")

        if not encrypted_node_key:
            continue

        if not encrypted_attributes:
            continue

        try:

            if ":" in encrypted_node_key:

                encrypted_node_key = (
                    encrypted_node_key.split(
                        ":",
                        1
                    )[1]
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

            filename = attributes.get(
                "n",
                ""
            )

            if not filename:
                continue

            output.append(
                {
                    "handle": node_handle,
                    "name": filename,
                    "key": list(node_key),
                    "size": node.get("s", 0),
                }
            )

        except Exception:
            continue

    return output


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

        value = str(
            value or ""
        ).strip()

        if (
            value
            and value.lower() != "nan"
        ):

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
        n
        for n in nodes
        if n["name"]
        .lower()
        .endswith(image_extensions)
    ]

    # Exact filename
    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if stem == identifier:
                return node

    # Partial filename
    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if identifier in stem:
                return node

    return None


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
        folder_handle,
    )

    download_url = response.get(
        "g"
    )

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
# BARCODE DECODER
# ============================================================

BARCODE_SYMBOLS = [
    ZBarSymbol.EAN13,
    ZBarSymbol.EAN8,
    ZBarSymbol.UPCA,
    ZBarSymbol.UPCE,
    ZBarSymbol.CODE128,
    ZBarSymbol.CODE39,
    ZBarSymbol.CODE93,
    ZBarSymbol.I25,
]


def clean_barcode(value):

    if value is None:
        return ""

    value = str(value).strip()

    value = re.sub(
        r"[^0-9A-Za-z\-_]",
        "",
        value,
    )

    return value


def barcode_is_valid(value):

    if not value:
        return False

    # Retail numeric barcode
    if value.isdigit():

        if len(value) in (
            8,
            12,
            13,
            14,
        ):
            return True

    # Alphanumeric warehouse barcode
    if len(value) >= 4:
        return True

    return False


def zbar_once(image):

    try:

        results = zbar_decode(
            image,
            symbols=BARCODE_SYMBOLS,
        )

    except Exception:
        return None


    for result in results:

        value = clean_barcode(
            result.data.decode(
                "utf-8",
                errors="ignore",
            )
        )

        if barcode_is_valid(value):

            return {
                "value": value,
                "type": str(
                    result.type
                ),
                "rect": result.rect,
            }

    return None


def preprocess_variants(image):

    variants = []

    # --------------------------------------------------------
    # Original
    # --------------------------------------------------------

    variants.append(
        image
    )


    # --------------------------------------------------------
    # Resize
    # --------------------------------------------------------

    height, width = image.shape[:2]

    if width < 1600:

        scale = (
            1600 / width
        )

        enlarged = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

        variants.append(
            enlarged
        )

    else:

        enlarged = image


    # --------------------------------------------------------
    # Gray
    # --------------------------------------------------------

    gray = cv2.cvtColor(
        enlarged,
        cv2.COLOR_BGR2GRAY,
    )

    variants.append(
        gray
    )


    # --------------------------------------------------------
    # CLAHE
    # --------------------------------------------------------

    clahe = cv2.createCLAHE(
        clipLimit=3.0,
        tileGridSize=(8, 8),
    )

    enhanced = clahe.apply(
        gray
    )

    variants.append(
        enhanced
    )


    # --------------------------------------------------------
    # Sharpen
    # --------------------------------------------------------

    blur = cv2.GaussianBlur(
        enhanced,
        (0, 0),
        2,
    )

    sharpened = cv2.addWeighted(
        enhanced,
        1.8,
        blur,
        -0.8,
        0,
    )

    variants.append(
        sharpened
    )


    # --------------------------------------------------------
    # OTSU
    # --------------------------------------------------------

    _, binary = cv2.threshold(
        sharpened,
        0,
        255,
        cv2.THRESH_BINARY
        + cv2.THRESH_OTSU,
    )

    variants.append(
        binary
    )


    # --------------------------------------------------------
    # Adaptive
    # --------------------------------------------------------

    adaptive = cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        7,
    )

    variants.append(
        adaptive
    )


    # --------------------------------------------------------
    # Inverted
    # --------------------------------------------------------

    variants.append(
        cv2.bitwise_not(
            binary
        )
    )


    return variants


def barcode_decode_image(
    image,
):

    if image is None:
        return None


    # Make sure OpenCV BGR.
    if len(image.shape) == 2:

        bgr = cv2.cvtColor(
            image,
            cv2.COLOR_GRAY2BGR,
        )

    else:

        bgr = image


    # --------------------------------------------------------
    # Pass 1: ZBar directly.
    # --------------------------------------------------------

    result = zbar_once(
        bgr
    )

    if result:
        return result


    # --------------------------------------------------------
    # Pass 2: all image enhancements.
    # --------------------------------------------------------

    variants = preprocess_variants(
        bgr
    )


    for variant in variants:

        result = zbar_once(
            variant
        )

        if result:
            return result


    # --------------------------------------------------------
    # Pass 3: targeted crops.
    #
    # A barcode is usually a horizontal strip.
    # We intentionally examine multiple horizontal regions.
    # --------------------------------------------------------

    h, w = bgr.shape[:2]

    crop_boxes = [

        # Central 90%
        (
            0,
            int(h * 0.05),
            w,
            int(h * 0.95),
        ),

        # Central 70%
        (
            0,
            int(h * 0.15),
            w,
            int(h * 0.85),
        ),

        # Middle strip
        (
            0,
            int(h * 0.25),
            w,
            int(h * 0.75),
        ),

        # Upper-middle
        (
            0,
            int(h * 0.10),
            w,
            int(h * 0.60),
        ),

        # Lower-middle
        (
            0,
            int(h * 0.40),
            w,
            int(h * 0.90),
        ),

    ]


    for x1, y1, x2, y2 in crop_boxes:

        crop = bgr[
            y1:y2,
            x1:x2,
        ]

        if crop.size == 0:
            continue


        crop_variants = (
            preprocess_variants(
                crop
            )
        )


        for variant in crop_variants:

            result = zbar_once(
                variant
            )

            if result:
                return result


    # --------------------------------------------------------
    # Pass 4: rotations.
    #
    # Useful when the barcode is slightly tilted.
    # --------------------------------------------------------

    center = (
        w // 2,
        h // 2,
    )

    rotation_matrix = cv2.getRotationMatrix2D(
        center,
        5,
        1.0,
    )

    rotated_plus = cv2.warpAffine(
        bgr,
        rotation_matrix,
        (w, h),
        borderValue=(
            255,
            255,
            255,
        ),
    )

    result = zbar_once(
        rotated_plus
    )

    if result:
        return result


    rotation_matrix = cv2.getRotationMatrix2D(
        center,
        -5,
        1.0,
    )

    rotated_minus = cv2.warpAffine(
        bgr,
        rotation_matrix,
        (w, h),
        borderValue=(
            255,
            255,
            255,
        ),
    )

    result = zbar_once(
        rotated_minus
    )

    if result:
        return result


    return None


# ============================================================
# PRODUCT SEARCH
# ============================================================

def render_product(
    df,
    query,
):

    query = str(
        query
    ).strip()


    if not query:
        return


    code_col = "0"
    barcode_col = "1"
    desc_col = "2"
    qty_col = "3"


    matches = df[
        (
            df[barcode_col]
            == query
        )
        |
        (
            df[code_col]
            == query
        )
    ]


    if matches.empty:

        st.error(
            "❌ لم يتم العثور على المنتج."
        )

        similar = df[
            df[code_col].str.contains(
                query,
                case=False,
                na=False,
                regex=False,
            )
            |
            df[barcode_col].str.contains(
                query,
                case=False,
                na=False,
                regex=False,
            )
        ]


        if not similar.empty:

            st.markdown(
                "### نتائج مشابهة"
            )

            for _, row in (
                similar.head(5).iterrows()
            ):

                with st.container(
                    border=True
                ):

                    st.write(
                        f"**{row[desc_col]}**"
                    )

                    st.caption(
                        f"الكود: {row[code_col]}  |  "
                        f"الباركود: {row[barcode_col]}"
                    )

        return


    row = matches.iloc[0]


    code = str(
        row[code_col]
    ).strip()

    barcode = str(
        row[barcode_col]
    ).strip()

    description = str(
        row[desc_col]
    ).strip()

    quantity = str(
        row[qty_col]
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


    # --------------------------------------------------------
    # PRODUCT CARD
    # --------------------------------------------------------

    st.markdown(
        f"""
        <div class="product-card">

            <div class="product-title">
                📦 {description}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    c1, c2, c3 = st.columns(3)


    with c1:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-value">
                    {code}
                </div>

                <div class="metric-label">
                    كود المنتج
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with c2:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-value">
                    {barcode}
                </div>

                <div class="metric-label">
                    الباركود
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with c3:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-value">
                    {quantity}
                </div>

                <div class="metric-label">
                    الكمية
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    # --------------------------------------------------------
    # PRODUCT IMAGE
    # --------------------------------------------------------

    st.markdown(
        "### 🖼️ صورة المنتج"
    )


    try:

        with st.spinner(
            "جاري تحميل الصورة..."
        ):

            nodes = get_mega_nodes()

            image_node = find_mega_image(
                nodes,
                code,
                barcode,
            )


        if image_node is None:

            st.info(
                "لا توجد صورة لهذا المنتج."
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


        st.image(
            image,
            width="stretch",
        )


    except Exception as e:

        st.error(
            f"تعذر تحميل صورة المنتج: {e}"
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">

        <h1>
            Holland Bazar T&D 📦
        </h1>

        <p>
            البحث عن المنتجات والمخزون
        </p>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TABS
# ============================================================

search_tab, camera_tab = st.tabs(
    [
        "🔎 البحث",
        "📷 مسح الباركود",
    ]
)


# ============================================================
# SEARCH TAB
# ============================================================

with search_tab:

    query = st.text_input(
        "الباركود أو كود المنتج",
        placeholder="أدخل الباركود هنا...",
        key="manual_search",
    )


    if query:

        render_product(
            load_data(),
            query,
        )


# ============================================================
# CAMERA TAB
# ============================================================

with camera_tab:

    st.markdown(
        """
        <div class="scan-box">

            <div class="scan-title">
                📷 امسح الباركود
            </div>

            <div class="scan-help">

                وجّه الكاميرا مباشرة إلى الباركود.<br>

                اجعل الخطوط واضحة وكبيرة داخل الصورة.<br>

                حاول تجنب انعكاس الضوء على الملصق.

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    camera_image = st.camera_input(
        "التقاط صورة للباركود",
        key="barcode_camera",
    )


    if camera_image is not None:

        try:

            pil_image = Image.open(
                BytesIO(
                    camera_image.getvalue()
                )
            ).convert(
                "RGB"
            )


            frame = cv2.cvtColor(
                np.array(pil_image),
                cv2.COLOR_RGB2BGR,
            )


            with st.spinner(
                "🔍 جاري قراءة الباركود..."
            ):

                result = (
                    barcode_decode_image(
                        frame
                    )
                )


            if result:

                barcode = result["value"]
                barcode_type = result["type"]


                st.markdown(
                    f"""
                    <div class="barcode-result">

                        <div>
                            ✅ تم التعرف على الباركود
                        </div>

                        <div class="barcode-number">
                            {barcode}
                        </div>

                        <div>
                            النوع: {barcode_type}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )


                st.success(
                    "تم العثور على المنتج."
                )


                render_product(
                    load_data(),
                    barcode,
                )


            else:

                st.error(
                    "❌ لم أتمكن من قراءة الباركود."
                )


                st.markdown(
                    """
                    **لأفضل نتيجة:**

                    1. اجعل الباركود يحتل معظم الصورة.
                    2. لا تصور الملصق من مسافة بعيدة.
                    3. لا تجعل ضوء الفلاش ينعكس على الباركود.
                    4. حاول إبقاء الهاتف ثابتاً.
                    5. اجعل الخطوط العمودية للباركود واضحة.
                    """,
                )


                with st.expander(
                    "عرض الصورة التي تم تحليلها"
                ):

                    st.image(
                        pil_image,
                        width="stretch",
                    )


        except Exception as e:

            st.error(
                f"حدث خطأ أثناء قراءة الباركود: {e}"
            )

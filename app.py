import os
import re
import json
import struct
import base64
from io import BytesIO

import requests
import pandas as pd
import streamlit as st

from Crypto.Cipher import AES
from Crypto.Util import Counter


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
# PROFESSIONAL UI
# ============================================================

st.markdown(
    """
    <style>

    /* ======================================================
       GLOBAL
       ====================================================== */

    .stApp {
        direction: rtl;
        background: #0b0f14;
    }

    .main .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 4rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    * {
        box-sizing: border-box;
    }


    /* ======================================================
       HEADER
       ====================================================== */

    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(
            135deg,
            #172033 0%,
            #111827 100%
        );
        border: 1px solid #263449;
        border-radius: 18px;
        padding: 22px 26px;
        margin-bottom: 22px;
        box-shadow: 0 8px 30px rgba(0,0,0,.20);
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .brand-icon {
        width: 46px;
        height: 46px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #166534;
        border-radius: 13px;
        font-size: 24px;
    }

    .brand-title {
        font-size: 25px;
        font-weight: 800;
        color: #f8fafc;
        line-height: 1.2;
    }

    .brand-subtitle {
        font-size: 13px;
        color: #94a3b8;
        margin-top: 4px;
    }


    /* ======================================================
       SEARCH AREA
       ====================================================== */

    .search-section {
        background: #111827;
        border: 1px solid #263449;
        border-radius: 18px;
        padding: 22px 24px 18px 24px;
        margin-bottom: 22px;
    }

    .search-title {
        color: #f8fafc;
        font-size: 19px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .search-hint {
        color: #64748b;
        font-size: 13px;
        margin-bottom: 12px;
    }

    div[data-testid="stTextInput"] input {
        direction: ltr !important;
        text-align: center !important;
        background: #0b1220 !important;
        color: #f8fafc !important;
        border: 2px solid #334155 !important;
        border-radius: 12px !important;
        min-height: 54px !important;
        font-size: 19px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #22c55e !important;
        box-shadow: 0 0 0 3px rgba(34,197,94,.12) !important;
    }


    /* ======================================================
       STATUS
       ====================================================== */

    .status-found {
        display: flex;
        align-items: center;
        gap: 10px;
        background: rgba(22,101,52,.16);
        border: 1px solid #166534;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 18px;
        color: #86efac;
        font-weight: 700;
    }

    .status-icon {
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #166534;
        border-radius: 50%;
    }


    /* ======================================================
       PRODUCT AREA
       ====================================================== */

    .product-card {
        background: #111827;
        border: 1px solid #263449;
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 8px 30px rgba(0,0,0,.18);
    }

    .product-card-header {
        padding: 20px 22px;
        border-bottom: 1px solid #263449;
        background: #151e2d;
    }

    .product-label {
        color: #64748b;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .product-name {
        color: #f8fafc;
        font-size: 23px;
        font-weight: 800;
        line-height: 1.4;
    }


    /* ======================================================
       INFO CARDS
       ====================================================== */

    .info-card {
        background: #0b1220;
        border: 1px solid #263449;
        border-radius: 12px;
        padding: 15px 17px;
        height: 100%;
    }

    .info-label {
        color: #64748b;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 7px;
    }

    .info-value {
        color: #e2e8f0;
        font-size: 17px;
        font-weight: 700;
        direction: ltr;
        text-align: right;
        word-break: break-word;
    }


    /* ======================================================
       QUANTITY
       ====================================================== */

    .quantity-card {
        background: linear-gradient(
            135deg,
            #14532d,
            #166534
        );
        border: 1px solid #22c55e;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        min-height: 145px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .quantity-label {
        color: #bbf7d0;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .quantity-number {
        color: #ffffff;
        font-size: 42px;
        font-weight: 900;
        line-height: 1;
    }

    .quantity-unit {
        color: #bbf7d0;
        font-size: 12px;
        margin-top: 8px;
    }


    /* ======================================================
       IMAGE AREA
       ====================================================== */

    .image-section {
        background: #111827;
        border: 1px solid #263449;
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,.18);
    }

    .image-section-title {
        color: #f8fafc;
        font-size: 17px;
        font-weight: 800;
        margin-bottom: 14px;
        text-align: right;
    }

    .image-preview {
        background: #080c12;
        border: 1px solid #263449;
        border-radius: 14px;
        min-height: 420px;
        max-height: 520px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 12px;
    }

    /* Keep Streamlit images from becoming enormous */
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
        align-items: center;
        background: #080c12;
        border: 1px solid #263449;
        border-radius: 14px;
        padding: 12px;
        min-height: 300px;
        max-height: 520px;
        overflow: hidden;
    }

    div[data-testid="stImage"] img {
        max-height: 480px !important;
        max-width: 100% !important;
        width: auto !important;
        height: auto !important;
        object-fit: contain !important;
        border-radius: 8px;
    }


    /* ======================================================
       IMAGE CAPTION
       ====================================================== */

    .image-file {
        color: #64748b;
        text-align: center;
        font-size: 12px;
        margin-top: 9px;
        direction: ltr;
    }


    /* ======================================================
       EMPTY / ERROR
       ====================================================== */

    .empty-box {
        background: #111827;
        border: 1px solid #263449;
        border-radius: 16px;
        padding: 35px 25px;
        text-align: center;
        color: #94a3b8;
    }

    .empty-icon {
        font-size: 40px;
        margin-bottom: 12px;
    }

    .empty-title {
        color: #e2e8f0;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 7px;
    }


    /* ======================================================
       SUGGESTIONS
       ====================================================== */

    .suggestion-title {
        color: #e2e8f0;
        font-size: 17px;
        font-weight: 800;
        margin: 24px 0 12px 0;
    }


    /* ======================================================
       STREAMLIT ELEMENT SPACING
       ====================================================== */

    div[data-testid="stVerticalBlock"] {
        gap: 0.65rem;
    }

    .stAlert {
        border-radius: 12px !important;
    }


    /* ======================================================
       MOBILE
       ====================================================== */

    @media (max-width: 700px) {

        .main .block-container {
            padding: 1rem 0.8rem 3rem 0.8rem;
        }

        .app-header {
            padding: 17px;
            border-radius: 14px;
        }

        .brand-title {
            font-size: 20px;
        }

        .brand-subtitle {
            font-size: 11px;
        }

        .brand-icon {
            width: 40px;
            height: 40px;
            font-size: 20px;
        }

        .search-section {
            padding: 16px;
            border-radius: 14px;
        }

        .product-name {
            font-size: 19px;
        }

        .quantity-number {
            font-size: 36px;
        }

        div[data-testid="stImage"] {
            min-height: 250px;
            max-height: 420px;
        }

        div[data-testid="stImage"] img {
            max-height: 390px !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MEGA BASE64 HELPERS
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

    if not decrypted.startswith(b"MEGA"):
        raise ValueError(
            "Invalid MEGA attribute prefix"
        )

    return json.loads(
        decrypted[4:].decode(
            "utf-8"
        )
    )


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

    raise ValueError(
        "رابط مجلد MEGA غير صالح."
    )


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

    if not isinstance(result, list) or not result:

        raise RuntimeError(
            "MEGA returned an empty response."
        )

    if isinstance(result[0], int):

        raise RuntimeError(
            f"MEGA API error: {result[0]}"
        )

    return result[0]


# ============================================================
# MEGA FILE LIST
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

        if node.get("t") not in (0, 1):
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

    counter_value = (
        (key[4] << 32)
        + key[5]
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
# DATABASE
# ============================================================

@st.cache_data(ttl=5)
def load_data():

    if not os.path.exists(
        EXCEL_PATH
    ):

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
            f"خطأ في قراءة قاعدة البيانات: {e}"
        )

        return None


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="app-header">

        <div class="brand">

            <div class="brand-icon">
                📦
            </div>

            <div>

                <div class="brand-title">
                    Holland Bazar T&D
                </div>

                <div class="brand-subtitle">
                    نظام البحث عن المنتجات والمخزون
                </div>

            </div>

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
# SEARCH SECTION
# ============================================================

st.markdown(
    """
    <div class="search-section">

        <div class="search-title">
            🔎 البحث عن منتج
        </div>

        <div class="search-hint">
            أدخل الباركود أو كود المنتج
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)

search_query = st.text_input(
    "الباركود أو الكود",
    key="main_search",
    placeholder="مثال: 6932308668058",
    label_visibility="collapsed",
)


search_query = search_query.strip()


# ============================================================
# NO SEARCH
# ============================================================

if not search_query:

    st.markdown(
        """
        <div class="empty-box">

            <div class="empty-icon">
                🔍
            </div>

            <div class="empty-title">
                ابدأ البحث عن منتج
            </div>

            <div>
                أدخل الباركود أو كود المنتج في مربع البحث أعلاه
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.stop()


# ============================================================
# COLUMNS
# ============================================================

col_code = "0"
col_barcode = "1"
col_desc = "2"
col_qty = "3"


# ============================================================
# SEARCH DATABASE
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

    if not description or description.lower() == "nan":
        description = "غير متوفر"

    if not quantity or quantity.lower() == "nan":
        quantity = "0"


    # ========================================================
    # FOUND STATUS
    # ========================================================

    st.markdown(
        """
        <div class="status-found">

            <div class="status-icon">
                ✓
            </div>

            تم العثور على المنتج

        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # MAIN TWO-COLUMN AREA
    # ========================================================

    info_column, image_column = st.columns(
        [0.95, 1.05],
        gap="large",
    )


    # ========================================================
    # PRODUCT INFORMATION
    # ========================================================

    with info_column:

        st.markdown(
            """
            <div class="product-card">

                <div class="product-card-header">

                    <div class="product-label">
                        المنتج
                    </div>

                    <div class="product-name">
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            description
        )

        st.markdown(
            """
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


        # -----------------------------------------------
        # CODE
        # -----------------------------------------------

        st.markdown(
            "<br>",
            unsafe_allow_html=True,
        )

        code_col, barcode_col = st.columns(
            2,
            gap="medium",
        )


        with code_col:

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


        with barcode_col:

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


        # -----------------------------------------------
        # QUANTITY
        # -----------------------------------------------

        st.markdown(
            "<br>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="quantity-card">

                <div class="quantity-label">
                    📦 الكمية المتوفرة
                </div>

                <div class="quantity-number">
                    {quantity}
                </div>

                <div class="quantity-unit">
                    وحدة في المخزون
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    # ========================================================
    # IMAGE
    # ========================================================

    with image_column:

        st.markdown(
            """
            <div class="image-section">

                <div class="image-section-title">
                    🖼️ صورة المنتج
                </div>

            </div>
            """,
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

                st.markdown(
                    """
                    <div class="empty-box">

                        <div class="empty-icon">
                            📷
                        </div>

                        <div class="empty-title">
                            لا توجد صورة
                        </div>

                        <div>
                            لم يتم العثور على صورة مرتبطة
                            بهذا الكود أو الباركود.
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                with st.spinner(
                    "جاري تحميل الصورة..."
                ):

                    image_bytes = (
                        download_mega_image(
                            image_node["handle"],
                            image_node["key"],
                        )
                    )


                # The CSS above constrains this image.
                st.image(
                    image_bytes,
                    use_container_width=False,
                )


                st.markdown(
                    f"""
                    <div class="image-file">
                        {image_node["name"]}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


        except Exception as e:

            st.error(
                f"❌ تعذر تحميل صورة المنتج: {e}"
            )


# ============================================================
# PRODUCT NOT FOUND
# ============================================================

else:

    st.markdown(
        """
        <div class="empty-box">

            <div class="empty-icon">
                🔎
            </div>

            <div class="empty-title">
                لم يتم العثور على المنتج
            </div>

            <div>
                لا يوجد منتج مطابق للباركود أو الكود المدخل.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    # ========================================================
    # SIMILAR PRODUCTS
    # ========================================================

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
            '<div class="suggestion-title">'
            '💡 منتجات مشابهة'
            '</div>',
            unsafe_allow_html=True,
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


            with st.container(
                border=True
            ):

                st.write(
                    f"**{suggestion_description}**"
                )

                st.caption(
                    f"الكود: {suggestion_code}  •  "
                    f"الباركود: {suggestion_barcode}"
                )

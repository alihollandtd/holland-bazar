import os
import re
import base64
import hashlib
import binascii
from pathlib import Path

import requests
import pandas as pd
import streamlit as st
from Crypto.Cipher import AES


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Holland Bazar T&D",
    layout="centered",
    page_icon="📦",
)


# ============================================================
# RTL / UI STYLE
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        direction: rtl;
        text-align: right;
    }

    .stTextInput label {
        direction: rtl;
        text-align: right;
    }

    .product-card {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 22px;
        margin-top: 20px;
        margin-bottom: 20px;
    }

    .product-title {
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 18px;
    }

    .product-row {
        padding: 8px 0;
        font-size: 17px;
    }

    .metric-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        margin-top: 15px;
    }

    .metric-number {
        font-size: 32px;
        font-weight: 800;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 14px;
    }

    .suggestion-box {
        background: #334155;
        border-radius: 10px;
        padding: 12px;
        margin: 6px 0;
    }

    .image-box {
        text-align: center;
        margin: 15px 0 20px 0;
    }

    .image-caption {
        color: #94a3b8;
        font-size: 13px;
        margin-top: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SETTINGS
# ============================================================

EXCEL_PATH = "DATABASE.xlsx"

# Your public MEGA folder.
# Keep this as the folder URL, NOT a fake image URL.
MEGA_FOLDER_URL = (
    "https://mega.nz/folder/HrximbwC"
    "#9wvR9D8OQnrAJlTItE6Oag"
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

        # Rename columns to 0,1,2,3...
        df.columns = [str(i) for i in range(len(df.columns))]

        for col in df.columns:
            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        return df

    except Exception as e:
        st.error(f"خطأ في قراءة قاعدة البيانات: {e}")
        return None


# ============================================================
# MEGA HELPERS
# ============================================================

def mega_folder_parts(folder_url):
    """
    Extract MEGA public folder handle and key.
    """

    match = re.search(
        r"mega\.nz/folder/([^#/?]+)#([^/?]+)",
        folder_url,
    )

    if not match:
        raise ValueError("رابط مجلد MEGA غير صالح.")

    return match.group(1), match.group(2)


def base64_url_decode(data):
    """
    Decode MEGA's URL-safe base64.
    """

    if isinstance(data, str):
        data = data.encode()

    data += b"=" * (-len(data) % 4)

    return base64.urlsafe_b64decode(data)


def base64_url_encode(data):
    """
    Encode bytes to MEGA URL-safe base64.
    """

    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def mega_a32_to_str(data):
    return data


def decrypt_mega_attributes(attr_data, key):
    """
    Decrypt MEGA file/folder attributes.

    MEGA stores attributes as:
        'MEGA' + JSON
    encrypted using AES-128-ECB.
    """

    cipher = AES.new(key, AES.MODE_ECB)

    decrypted = cipher.decrypt(attr_data)

    decrypted = decrypted.rstrip(b"\x00")

    if not decrypted.startswith(b"MEGA"):
        raise ValueError("تعذر فك بيانات ملف MEGA.")

    json_data = decrypted[4:]

    return json_data.decode("utf-8")


def mega_key_from_public_key(public_key):
    """
    Convert MEGA public folder key into AES key.

    MEGA public keys are base64 encoded.
    """

    key_bytes = base64_url_decode(public_key)

    if len(key_bytes) != 16:
        raise ValueError("مفتاح MEGA غير متوقع.")

    return key_bytes


def decrypt_file_key(encrypted_key, folder_key):
    """
    Decrypt the individual file key using the folder key.
    """

    cipher = AES.new(folder_key, AES.MODE_ECB)

    return cipher.decrypt(encrypted_key)


def decrypt_node_name(attributes, file_key):
    """
    Extract filename from decrypted MEGA attributes.
    """

    try:
        name = attributes.get("n")

        if name:
            return name

    except Exception:
        pass

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_mega_folder_files(folder_url):
    """
    Ask MEGA's public API for the files in the public folder.

    This does NOT download the entire folder.

    It only retrieves the folder's file list and the information
    needed to download a matching image later.
    """

    folder_handle, folder_key_string = mega_folder_parts(
        folder_url
    )

    folder_key = mega_key_from_public_key(
        folder_key_string
    )

    # MEGA public folder API
    endpoint = "https://g.api.mega.co.nz/cs"

    payload = [
        {
            "a": "f",
            "c": 1,
            "r": 1,
            "ca": 1,
            "ph": folder_handle,
        }
    ]

    response = requests.post(
        endpoint,
        params={"id": 0},
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    if not isinstance(result, list) or not result:
        raise RuntimeError("MEGA لم يرجع بيانات.")

    if isinstance(result[0], int):
        raise RuntimeError(
            f"MEGA API error: {result[0]}"
        )

    nodes = result[0].get("f", [])

    files = []

    for node in nodes:

        # Type 0 = file
        if node.get("t") != 0:
            continue

        encrypted_attributes = node.get("a")
        encrypted_key = node.get("k")

        if not encrypted_attributes or not encrypted_key:
            continue

        try:
            attributes_bytes = base64_url_decode(
                encrypted_attributes
            )

            attributes_json = decrypt_mega_attributes(
                attributes_bytes,
                folder_key,
            )

            import json

            attributes = json.loads(
                attributes_json
            )

            filename = attributes.get("n")

            if not filename:
                continue

            # File key format:
            # <user key>:<file key>
            if ":" in encrypted_key:
                _, encrypted_file_key = encrypted_key.split(
                    ":",
                    1,
                )
            else:
                encrypted_file_key = encrypted_key

            encrypted_file_key_bytes = base64_url_decode(
                encrypted_file_key
            )

            file_key = decrypt_file_key(
                encrypted_file_key_bytes,
                folder_key,
            )

            files.append(
                {
                    "name": filename,
                    "handle": node.get("h"),
                    "key": base64_url_encode(file_key),
                    "size": node.get("s"),
                }
            )

        except Exception:
            continue

    return files


def find_image_file(files, product_code, barcode):
    """
    Find an image by barcode or product code.

    Supported examples:

        123456.png
        123456.jpg
        123456.jpeg
        123456.webp

    Also supports filenames containing the code.
    """

    codes = []

    for value in [barcode, product_code]:

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        if value.lower() == "nan":
            continue

        codes.append(value)

    if not codes:
        return None

    image_extensions = (
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
    )

    # First: exact filename match
    for code in codes:

        for file in files:

            name = str(
                file.get("name", "")
            ).strip()

            stem = Path(name).stem

            if (
                stem.lower() == code.lower()
                and name.lower().endswith(
                    image_extensions
                )
            ):
                return file

    # Second: filename contains barcode/code
    for code in codes:

        for file in files:

            name = str(
                file.get("name", "")
            ).strip()

            if not name.lower().endswith(
                image_extensions
            ):
                continue

            if code.lower() in Path(name).stem.lower():
                return file

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def download_mega_file(file_handle, file_key, filename):
    """
    Download one file directly from MEGA.

    Returns the downloaded bytes.
    """

    # MEGA download request
    endpoint = "https://g.api.mega.co.nz/cs"

    payload = [
        {
            "a": "g",
            "g": 1,
            "n": file_handle,
        }
    ]

    response = requests.post(
        endpoint,
        params={"id": 0},
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    if not isinstance(result, list) or not result:
        raise RuntimeError(
            "MEGA download request failed."
        )

    info = result[0]

    if isinstance(info, int):
        raise RuntimeError(
            f"MEGA download error: {info}"
        )

    download_url = info.get("g")

    if not download_url:
        raise RuntimeError(
            "MEGA لم يعطِ رابط تحميل."
        )

    file_response = requests.get(
        download_url,
        timeout=120,
    )

    file_response.raise_for_status()

    encrypted_data = file_response.content

    # --------------------------------------------------------
    # MEGA uses AES-CTR for file content.
    # The returned file key is 16 bytes.
    # --------------------------------------------------------

    key_bytes = base64_url_decode(file_key)

    if len(key_bytes) != 16:
        raise RuntimeError(
            "مفتاح الصورة غير صالح."
        )

    # First 8 bytes are AES key material.
    aes_key = bytes(
        a ^ b
        for a, b in zip(
            key_bytes[:8],
            key_bytes[8:16],
        )
    ) + key_bytes[:8]

    # MEGA CTR uses the first 8 bytes as nonce.
    nonce = key_bytes[8:16]

    cipher = AES.new(
        aes_key,
        AES.MODE_CTR,
        nonce=b"",
        initial_value=int.from_bytes(
            nonce + b"\x00" * 8,
            byteorder="big",
        ),
    )

    decrypted = cipher.decrypt(
        encrypted_data
    )

    return decrypted


def get_product_image(product_code, barcode):
    """
    Find and download the matching image.
    """

    try:

        files = get_mega_folder_files(
            MEGA_FOLDER_URL
        )

        if not files:
            return None, "لم يتم العثور على صور في مجلد MEGA."

        image_file = find_image_file(
            files,
            product_code,
            barcode,
        )

        if not image_file:
            return None, None

        image_bytes = download_mega_file(
            image_file["handle"],
            image_file["key"],
            image_file["name"],
        )

        return image_bytes, image_file["name"]

    except Exception as e:

        return None, (
            "تعذر تحميل صورة المنتج من MEGA: "
            + str(e)
        )


# ============================================================
# MAIN APP
# ============================================================

df = load_data()

st.title("📦 Holland Bazar T&D")

search_query = st.text_input(
    "🔍 أدخل الباركود أو الرمز (كود) للبحث:",
    key="main_search",
).strip()


if df is not None and not df.empty:

    col_code = "0"
    col_barcode = "1"
    col_desc = "2"
    col_qty = "3"

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search_query:

        exact_match = df[
            (df[col_barcode] == search_query)
            | (df[col_code] == search_query)
        ]

        if not exact_match.empty:

            matched_row = exact_match.iloc[0]

            code = str(
                matched_row[col_code]
            ).strip()

            barcode = str(
                matched_row[col_barcode]
            ).strip()

            description = str(
                matched_row[col_desc]
            ).strip()

            quantity = str(
                matched_row[col_qty]
            ).strip()

            if barcode.lower() == "nan" or barcode == "":
                barcode = "غير متوفر"

            if quantity.lower() == "nan" or quantity == "":
                quantity = "0"

            if description.lower() == "nan":
                description = "غير متوفر"

            # ------------------------------------------------
            # PRODUCT CARD
            # ------------------------------------------------

            st.markdown(
                f"""
                <div class="product-card">

                    <div class="product-title">
                        📦 {description}
                    </div>

                    <div class="product-row">
                        <strong>🔢 الكود:</strong>
                        {code}
                    </div>

                    <div class="product-row">
                        <strong>🏷️ الباركود:</strong>
                        {barcode}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            # ------------------------------------------------
            # QUANTITY
            # ------------------------------------------------

            st.markdown(
                f"""
                <div class="metric-box">

                    <div class="metric-number">
                        {quantity}
                    </div>

                    <div class="metric-label">
                        الكمية المتوفرة
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            # ------------------------------------------------
            # PRODUCT IMAGE
            # ------------------------------------------------

            st.markdown(
                "### 🖼️ صورة المنتج"
            )

            with st.spinner(
                "جاري البحث عن صورة المنتج..."
            ):

                image_bytes, image_result = (
                    get_product_image(
                        code,
                        barcode,
                    )
                )

            if image_bytes:

                st.image(
                    image_bytes,
                    caption=(
                        f"صورة المنتج: "
                        f"{image_result}"
                    ),
                    use_container_width=True,
                )

            elif image_result:

                st.warning(
                    image_result
                )

            else:

                st.info(
                    "📷 لا توجد صورة مرتبطة بهذا "
                    "الكود أو الباركود في مجلد الصور."
                )

        else:

            st.error(
                "❌ لم يتم العثور على المنتج بهذا "
                "الباركود أو الكود."
            )

            # ------------------------------------------------
            # SIMILAR RESULTS
            # ------------------------------------------------

            similar_matches = df[
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

            if not similar_matches.empty:

                st.markdown(
                    "### 💡 هل تقصد أحد هذه الرموز القريبة؟"
                )

                for _, row in similar_matches.head(5).iterrows():

                    suggestion_code = str(
                        row[col_code]
                    ).strip()

                    suggestion_barcode = str(
                        row[col_barcode]
                    ).strip()

                    suggestion_description = str(
                        row[col_desc]
                    ).strip()

                    st.markdown(
                        f"""
                        <div class="suggestion-box">
                            <strong>
                                {suggestion_code}
                            </strong>
                            &nbsp; | &nbsp;
                            {suggestion_barcode}
                            <br>
                            {suggestion_description}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    else:

        st.info(
            "👆 أدخل الباركود أو الكود للبحث عن المنتج."
        )

else:

    st.error(
        "❌ تأكد من وجود ملف DATABASE.xlsx "
        "في نفس مجلد التطبيق."
    )

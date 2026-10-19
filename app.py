
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
# NATIVE CAMERA BARCODE SCANNER
# ============================================================

from PIL import Image
import numpy as np
import cv2

try:
    from pyzbar.pyzbar import decode as zbar_decode
    from pyzbar.pyzbar import ZBarSymbol
    ZBAR_AVAILABLE = True
except Exception:
    ZBAR_AVAILABLE = False
    ZBarSymbol = None


def barcode_candidates_from_image(uploaded_file):
    if not uploaded_file or not ZBAR_AVAILABLE:
        return []

    try:
        original = Image.open(uploaded_file).convert("RGB")
    except Exception:
        return []

    max_dimension = 2400
    if max(original.size) > max_dimension:
        scale = max_dimension / max(original.size)
        original = original.resize(
            (
                max(1, int(original.width * scale)),
                max(1, int(original.height * scale)),
            ),
            Image.Resampling.LANCZOS,
        )

    rgb = np.array(original)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    variants = [
        ("original", rgb),
        ("gray", gray),
        (
            "upscaled",
            cv2.resize(
                gray,
                None,
                fx=2.0,
                fy=2.0,
                interpolation=cv2.INTER_CUBIC,
            ),
        ),
    ]

    clahe = cv2.createCLAHE(
        clipLimit=2.5,
        tileGridSize=(8, 8),
    )
    variants.append(("contrast", clahe.apply(gray)))

    blur = cv2.GaussianBlur(gray, (0, 0), 2.0)
    variants.append(
        (
            "sharpened",
            cv2.addWeighted(
                gray, 1.7, blur, -0.7, 0
            ),
        )
    )

    _, otsu = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    variants.append(("otsu", otsu))

    adaptive = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        7,
    )
    variants.append(("adaptive", adaptive))
    variants.append(
        ("inverted", cv2.bitwise_not(gray))
    )

    found = {}

    # pyzbar/ZBar uses I25 for Interleaved 2 of 5.
    # Some builds do not expose every symbol as an enum member,
    # so build this list defensively instead of accessing a
    # missing attribute such as ZBarSymbol.ITF.
    symbol_names = [
        "EAN13",
        "EAN8",
        "UPCA",
        "UPCE",
        "CODE128",
        "CODE39",
        "CODE93",
        "I25",
        "CODABAR",
    ]

    symbols = [
        getattr(ZBarSymbol, name)
        for name in symbol_names
        if hasattr(ZBarSymbol, name)
    ]

    # If a particular ZBar build exposes no symbol constants,
    # let ZBar use its normal default decoder set.
    if not symbols:
        symbols = None

    for variant_name, image in variants:
        try:
            if symbols is None:
                decoded = zbar_decode(image)
            else:
                decoded = zbar_decode(
                    image,
                    symbols=symbols,
                )
        except Exception:
            continue

        for item in decoded:
            try:
                value = (
                    item.data
                    .decode(
                        "utf-8",
                        errors="ignore",
                    )
                    .strip()
                )
            except Exception:
                continue

            if not value:
                continue

            barcode_type = str(
                getattr(item, "type", "UNKNOWN")
            )
            quality = getattr(item, "quality", None)

            key = (value, barcode_type)

            if key not in found:
                found[key] = {
                    "value": value,
                    "type": barcode_type,
                    "quality": quality,
                    "variant": variant_name,
                }

    results = list(found.values())
    results.sort(
        key=lambda x: (
            not x["value"].isdigit(),
            -len(x["value"]),
            -(x["quality"] or 0),
        )
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
        "استخدم كاميرا الجهاز لالتقاط صورة واضحة للباركود، "
        "ثم سيقوم النظام بقراءته والبحث عنه."
    )

    with st.container(border=True):
        st.markdown("### طريقة الاستخدام")
        st.write("1. اضغط على زر الكاميرا.")
        st.write("2. قرّب الباركود واجعله مستقيماً وواضحاً.")
        st.write("3. التقط الصورة.")
        st.write("4. سيقرأ النظام الباركود تلقائياً.")

        camera_photo = st.camera_input(
            "📷 التقاط صورة للباركود",
            key="warehouse_barcode_camera_v4",
            resolution="1080p",
            label_visibility="visible",
        )

    uploaded_photo = st.file_uploader(
        "أو ارفع صورة باركود من الجهاز",
        type=["jpg", "jpeg", "png", "webp"],
        key="barcode_image_upload_v4",
    )

    photo = (
        camera_photo
        if camera_photo is not None
        else uploaded_photo
    )

    if photo is None:
        st.info(
            "📷 اضغط على الكاميرا أعلاه لالتقاط صورة."
        )
        return

    left, right = st.columns(
        [1.35, 1],
        gap="large",
    )

    with left:
        st.image(
            photo,
            caption="الصورة الملتقطة",
            width="stretch",
        )

    with right:
        with st.spinner("جاري قراءة الباركود..."):
            results = barcode_candidates_from_image(photo)

        if not results:
            st.error(
                "لم يتم العثور على باركود واضح في الصورة."
            )
            st.warning(
                "قرّب الكاميرا من الباركود، "
                "اجعل الخطوط كلها ظاهرة، "
                "وتجنب الانعكاس أو الضبابية."
            )
            return

        best = barcode_matches_database(results)

        st.success("تمت قراءة الباركود")
        st.metric("الباركود", best["value"])
        st.caption(f"نوع الباركود: {best['type']}")

        matching = df[
            (df["0"] == best["value"])
            | (df["1"] == best["value"])
        ]

        if not matching.empty:
            show_product(matching.iloc[0])
        else:
            st.warning(
                "تمت قراءة الرقم، لكنه غير موجود في قاعدة البيانات."
            )
            show_similar(best["value"])

        if len(results) > 1:
            with st.expander(
                "قراءات أخرى من نفس الصورة"
            ):
                for result in results[:5]:
                    st.write(
                        f"{result['value']} — "
                        f"{result['type']}"
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

    if not ZBAR_AVAILABLE:
        st.error(
            "محرك قراءة الباركود غير مثبت. "
            "تأكد من وجود pyzbar في requirements.txt "
            "و libzbar0 في packages.txt."
        )
        st.stop()

    camera_scanner_ui()

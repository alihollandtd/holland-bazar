import os
import asyncio
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import cv2

from PIL import (
    Image,
    ImageOps,
    ImageEnhance,
    ImageFilter,
)

# ============================================================
# MEGA
# ============================================================

try:
    from mega.client import MegaNzClient

    MEGA_AVAILABLE = True

except Exception:
    MegaNzClient = None
    MEGA_AVAILABLE = False


# ============================================================
# BARCODE
# ============================================================

try:
    import zxingcpp

    ZXING_AVAILABLE = True

except Exception:
    zxingcpp = None
    ZXING_AVAILABLE = False


# ============================================================
# CONFIGURATION
# ============================================================

EXCEL_PATH = "DATABASE.xlsx"

# Your public MEGA folder.
#
# IMPORTANT:
# Keep the complete public folder URL here.
# Do not create an image URL manually.
#
MEGA_FOLDER_URL = (
    "https://mega.nz/folder/"
    "HrximbwC"
    "#"
    "9wvR9D8OQnrAJlTItE6Oag"
)

IMAGE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
)

# Where MEGA images are cached.
CACHE_DIR = Path(
    tempfile.gettempdir()
) / "holland_bazar_mega_images"

CACHE_DIR.mkdir(
    parents=True,
    exist_ok=True,
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
# CSS
# ============================================================

st.markdown(
    """
<style>

.stApp {
    direction: rtl;
    text-align: right;

    background:
        radial-gradient(
            circle at top right,
            rgba(34,197,94,.07),
            transparent 30%
        ),
        #0b1120;
}

.block-container {
    max-width: 1180px;
    padding-top: 25px;
    padding-bottom: 50px;
}

/* HEADER */

.header {
    background:
        linear-gradient(
            135deg,
            #111827,
            #172033
        );

    border:
        1px solid #263247;

    border-radius:
        22px;

    padding:
        28px;

    margin-bottom:
        22px;

    box-shadow:
        0 15px 45px rgba(0,0,0,.25);
}

.header h1 {
    margin: 0;
    color: #f8fafc;
    font-size: 34px;
    font-weight: 850;
}

.header p {
    margin-top: 8px;
    margin-bottom: 0;
    color: #94a3b8;
}

/* CARDS */

.card {
    background:
        linear-gradient(
            145deg,
            #172033,
            #111827
        );

    border:
        1px solid #334155;

    border-radius:
        20px;

    padding:
        24px;

    margin-top:
        16px;

    box-shadow:
        0 12px 35px rgba(0,0,0,.20);
}

/* PRODUCT */

.product-name {
    font-size: 25px;
    font-weight: 850;
    color: #f8fafc;
    margin-bottom: 18px;
}

.label {
    color: #64748b;
    font-size: 13px;
}

.value {
    color: #e2e8f0;
    font-size: 17px;
    font-weight: 700;
}

.quantity {
    background:
        linear-gradient(
            135deg,
            #14532d,
            #166534
        );

    border:
        1px solid #22c55e;

    border-radius:
        18px;

    padding:
        20px;

    text-align:
        center;

    margin-top:
        20px;
}

.quantity-label {
    color: #bbf7d0;
    font-size: 13px;
}

.quantity-number {
    color: white;
    font-size: 42px;
    font-weight: 900;
}

/* IMAGE */

.image-card {
    background: #0f172a;

    border:
        1px solid #334155;

    border-radius:
        18px;

    padding:
        15px;

    text-align:
        center;
}

/* SCANNER */

.scanner-card {
    background:
        linear-gradient(
            145deg,
            #111827,
            #172033
        );

    border:
        1px solid #334155;

    border-radius:
        20px;

    padding:
        24px;

    margin-bottom:
        20px;
}

.scanner-card h2 {
    color: #f8fafc;
    margin-top: 0;
}

.scanner-card p {
    color: #94a3b8;
}

.guide {
    border:
        2px dashed #22c55e;

    border-radius:
        16px;

    padding:
        16px;

    text-align:
        center;

    color:
        #bbf7d0;

    background:
        rgba(34,197,94,.04);

    margin:
        15px 0;
}

.suggestion {
    background:
        #172033;

    border:
        1px solid #334155;

    border-radius:
        14px;

    padding:
        14px 18px;

    margin:
        8px 0;
}

.stButton > button {
    min-height:
        46px !important;

    border-radius:
        12px !important;

    font-weight:
        750 !important;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE
# ============================================================

@st.cache_data(ttl=5)
def load_database():

    if not os.path.exists(EXCEL_PATH):

        return None

    try:

        data = pd.read_excel(
            EXCEL_PATH,
            dtype=str,
        )

    except Exception as error:

        st.error(
            f"تعذر فتح DATABASE.xlsx: {error}"
        )

        return None

    data.columns = [
        str(i)
        for i in range(
            len(data.columns)
        )
    ]

    for column in data.columns:

        data[column] = (
            data[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    return data


df = load_database()


if df is None:

    st.error(
        "لم يتم العثور على DATABASE.xlsx"
    )

    st.stop()


required_columns = [
    "0",
    "1",
    "2",
    "3",
]

for column in required_columns:

    if column not in df.columns:

        st.error(
            f"العمود {column} غير موجود في DATABASE.xlsx"
        )

        st.stop()


# ============================================================
# NORMALIZE
# ============================================================

def clean(value):

    if value is None:
        return ""

    value = str(value).strip()

    if value.lower() in (
        "nan",
        "none",
        "null",
    ):
        return ""

    return value


def normalize(value):

    value = clean(value)

    return "".join(
        value.split()
    )


# ============================================================
# DATABASE MATCH
# ============================================================

def find_product(value):

    value = normalize(value)

    if not value:
        return pd.DataFrame()

    return df[
        (df["0"] == value)
        |
        (df["1"] == value)
    ]


# ============================================================
# MEGA DOWNLOAD
# ============================================================

def run_async(coro):

    try:

        return asyncio.run(
            coro
        )

    except RuntimeError:

        loop = asyncio.new_event_loop()

        try:

            return loop.run_until_complete(
                coro
            )

        finally:

            loop.close()


async def download_mega_folder():

    if not MEGA_AVAILABLE:

        raise RuntimeError(
            "async-mega-py is not installed."
        )

    client = MegaNzClient()

    try:

        public_handle, public_key, selected_node = (
            client.parse_folder_url(
                MEGA_FOLDER_URL
            )
        )

        result = await client.download_public_folder(
            public_handle,
            public_key,
            str(CACHE_DIR),
            selected_node,
        )

        return result

    finally:

        try:
            await client.close()
        except Exception:
            pass


@st.cache_resource(
    ttl=60 * 60 * 12
)
def sync_download_mega_folder():

    return run_async(
        download_mega_folder()
    )


# ============================================================
# FIND IMAGE IN CACHE
# ============================================================

def all_image_files():

    if not CACHE_DIR.exists():

        return []

    files = []

    for path in CACHE_DIR.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        files.append(path)

    return files


def image_filename_candidates(
    code,
    barcode,
):

    code = clean(code)
    barcode = clean(barcode)

    candidates = []

    values = [
        barcode,
        code,
    ]

    for value in values:

        if not value:
            continue

        candidates.extend(
            [
                value,
                value + ".png",
                value + ".jpg",
                value + ".jpeg",
                value + ".webp",
            ]
        )

    return candidates


def find_product_image(
    code,
    barcode,
):

    candidates = image_filename_candidates(
        code,
        barcode,
    )

    if not candidates:
        return None

    candidate_map = {
        str(path.name).lower(): path
        for path in all_image_files()
    }

    for candidate in candidates:

        found = candidate_map.get(
            candidate.lower()
        )

        if found:

            return found

    # More tolerant comparison.
    normalized_targets = {
        normalize(
            Path(candidate).stem
        )
        for candidate in candidates
    }

    for path in all_image_files():

        stem = normalize(
            path.stem
        )

        if stem in normalized_targets:

            return path

    return None


# ============================================================
# IMAGE LOADING
# ============================================================

def load_product_image(
    code,
    barcode,
):

    image_path = find_product_image(
        code,
        barcode,
    )

    if image_path is None:

        return None

    try:

        return Image.open(
            image_path
        ).convert(
            "RGB"
        )

    except Exception:

        return None


# ============================================================
# MEGA STATUS / IMAGE
# ============================================================

def ensure_mega_images():

    if not MEGA_AVAILABLE:

        return False

    existing = all_image_files()

    if existing:

        return True

    try:

        with st.spinner(
            "جاري تجهيز صور المنتجات من MEGA لأول مرة..."
        ):

            sync_download_mega_folder()

        return True

    except Exception as error:

        st.warning(
            "تعذر تحميل صور MEGA حالياً."
        )

        with st.expander(
            "تفاصيل MEGA"
        ):

            st.code(
                str(error)
            )

        return False


# ============================================================
# PRODUCT CARD
# ============================================================

def show_product(row):

    code = clean(
        row["0"]
    )

    barcode = clean(
        row["1"]
    )

    description = clean(
        row["2"]
    )

    quantity = clean(
        row["3"]
    )

    if not barcode:

        barcode = "غير متوفر"

    if not quantity:

        quantity = "0"

    # --------------------------------------------------------
    # Load image from MEGA cache.
    # --------------------------------------------------------

    product_image = load_product_image(
        code,
        barcode,
    )

    # If cache doesn't contain images yet,
    # download the public MEGA folder.
    if product_image is None:

        ensure_mega_images()

        product_image = load_product_image(
            code,
            barcode,
        )

    # --------------------------------------------------------
    # PRODUCT
    # --------------------------------------------------------

    image_col, info_col = st.columns(
        [0.85, 1.35],
        gap="large",
    )

    with image_col:

        if product_image is not None:

            st.markdown(
                '<div class="image-card">',
                unsafe_allow_html=True,
            )

            st.image(
                product_image,
                use_container_width=True,
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                """
                <div class="image-card"
                     style="
                     min-height:280px;
                     display:flex;
                     align-items:center;
                     justify-content:center;
                     ">

                    <div>
                        <div style="
                            font-size:50px;
                        ">
                            📦
                        </div>

                        <div style="
                            color:#64748b;
                            margin-top:10px;
                        ">
                            لا توجد صورة لهذا المنتج
                        </div>
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

    with info_col:

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="product-name">
                {description or "منتج بدون وصف"}
            </div>

            <div class="label">
                الكود
            </div>

            <div class="value">
                {code or "غير متوفر"}
            </div>

            <br>

            <div class="label">
                الباركود
            </div>

            <div class="value">
                {barcode}
            </div>

            <div class="quantity">

                <div class="quantity-label">
                    الكمية المتوفرة
                </div>

                <div class="quantity-number">
                    {quantity}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )


# ============================================================
# SIMILAR
# ============================================================

def show_similar(
    value
):

    value = clean(
        value
    )

    if not value:
        return

    mask = (
        df["0"].str.contains(
            value,
            case=False,
            na=False,
            regex=False,
        )
        |
        df["1"].str.contains(
            value,
            case=False,
            na=False,
            regex=False,
        )
    )

    matches = df[
        mask
    ].head(8)

    if matches.empty:
        return

    st.markdown(
        "### 💡 نتائج قريبة"
    )

    for _, row in matches.iterrows():

        code = clean(
            row["0"]
        )

        barcode = clean(
            row["1"]
        )

        description = clean(
            row["2"]
        )

        st.markdown(
            f"""
            <div class="suggestion">

                <strong>
                    {description or "بدون وصف"}
                </strong>

                <br>

                <span style="
                    color:#94a3b8;
                ">
                    الكود: {code}
                    &nbsp;&nbsp; | &nbsp;&nbsp;
                    الباركود: {barcode}
                </span>

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# BARCODE DECODER
# ============================================================

def decode_zxing(
    image
):

    if not ZXING_AVAILABLE:

        return []

    try:

        array = np.array(
            image.convert(
                "RGB"
            )
        )

        results = zxingcpp.read_barcodes(
            array,
            try_rotate=True,
            try_downscale=True,
            try_invert=True,
            return_errors=False,
        )

    except Exception:

        return []

    decoded = []

    for result in results:

        value = normalize(
            getattr(
                result,
                "text",
                "",
            )
        )

        if not value:
            continue

        decoded.append(
            {
                "value":
                    value,

                "type":
                    str(
                        getattr(
                            result,
                            "format",
                            "UNKNOWN",
                        )
                    ),
            }
        )

    return decoded


# ============================================================
# OPENCV DECODER
# ============================================================

def decode_opencv(
    image
):

    output = []

    try:

        detector = (
            cv2.barcode_BarcodeDetector()
        )

    except Exception:

        return output

    array = np.array(
        image.convert(
            "RGB"
        )
    )

    try:

        value, points, straight = (
            detector.detectAndDecode(
                array
            )
        )

        value = normalize(
            value
        )

        if value:

            output.append(
                {
                    "value": value,
                    "type": "OpenCV",
                }
            )

    except Exception:
        pass

    try:

        result = (
            detector.detectAndDecodeMulti(
                array
            )
        )

        if result:

            ok = result[0]

            if ok:

                values = result[1]

                for value in values:

                    value = normalize(
                        value
                    )

                    if value:

                        output.append(
                            {
                                "value":
                                    value,
                                "type":
                                    "OpenCV-Multi",
                            }
                        )

    except Exception:
        pass

    return output


# ============================================================
# BARCODE LOCALIZATION
# ============================================================

def barcode_regions(
    image
):

    output = []

    try:

        original = np.array(
            image.convert(
                "RGB"
            )
        )

        gray = cv2.cvtColor(
            original,
            cv2.COLOR_RGB2GRAY,
        )

        h, w = gray.shape

        detect_width = 1200

        if w > detect_width:

            scale = (
                detect_width
                / float(w)
            )

            small = cv2.resize(
                gray,
                (
                    detect_width,
                    int(h * scale),
                ),
                interpolation=cv2.INTER_AREA,
            )

        else:

            small = gray

            scale = 1.0

        gradient = cv2.Scharr(
            small,
            cv2.CV_32F,
            1,
            0,
        )

        gradient = cv2.convertScaleAbs(
            gradient
        )

        gradient = cv2.GaussianBlur(
            gradient,
            (9, 9),
            0,
        )

        _, threshold = cv2.threshold(
            gradient,
            0,
            255,
            cv2.THRESH_BINARY
            + cv2.THRESH_OTSU,
        )

        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (31, 7),
        )

        closed = cv2.morphologyEx(
            threshold,
            cv2.MORPH_CLOSE,
            kernel,
            iterations=2,
        )

        contours, _ = cv2.findContours(
            closed,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        candidates = []

        for contour in contours:

            x, y, cw, ch = (
                cv2.boundingRect(
                    contour
                )
            )

            if cw < 80:
                continue

            if ch < 20:
                continue

            ratio = (
                cw
                / float(
                    max(ch, 1)
                )
            )

            if ratio < 1.5:
                continue

            if ratio > 25:
                continue

            mx = int(
                cw * 0.25
            )

            my = int(
                ch * 1.0
            )

            x1 = max(
                0,
                x - mx,
            )

            y1 = max(
                0,
                y - my,
            )

            x2 = min(
                small.shape[1],
                x + cw + mx,
            )

            y2 = min(
                small.shape[0],
                y + ch + my,
            )

            if scale != 1:

                x1 = int(
                    x1 / scale
                )

                y1 = int(
                    y1 / scale
                )

                x2 = int(
                    x2 / scale
                )

                y2 = int(
                    y2 / scale
                )

            score = (
                ratio
                + np.sqrt(
                    cw * ch
                )
            )

            candidates.append(
                (
                    score,
                    (
                        x1,
                        y1,
                        x2,
                        y2,
                    ),
                )
            )

        candidates.sort(
            reverse=True
        )

        for score, box in candidates[:10]:

            x1, y1, x2, y2 = box

            crop = original[
                y1:y2,
                x1:x2,
            ]

            if crop.size:

                output.append(
                    Image.fromarray(
                        crop
                    )
                )

    except Exception:

        return []

    return output


# ============================================================
# IMAGE VARIANTS
# ============================================================

def scanner_variants(
    image
):

    image = image.convert(
        "RGB"
    )

    yield image

    gray = ImageOps.grayscale(
        image
    )

    yield gray

    contrast = (
        ImageEnhance.Contrast(
            gray
        ).enhance(1.8)
    )

    yield contrast

    sharpen = contrast.filter(
        ImageFilter.UnsharpMask(
            radius=1.2,
            percent=180,
            threshold=2,
        )
    )

    yield sharpen

    upscaled = gray.resize(
        (
            gray.width * 2,
            gray.height * 2,
        ),
        Image.Resampling.LANCZOS,
    )

    yield upscaled

    array = np.array(
        gray
    )

    _, otsu = cv2.threshold(
        array,
        0,
        255,
        cv2.THRESH_BINARY
        + cv2.THRESH_OTSU,
    )

    yield Image.fromarray(
        otsu
    )


# ============================================================
# BARCODE SCAN
# ============================================================

def scan_barcode(
    uploaded_file
):

    try:

        image = Image.open(
            uploaded_file
        ).convert(
            "RGB"
        )

    except Exception:

        return []

    found = {}

    def register(
        value,
        barcode_type,
        method,
    ):

        value = normalize(
            value
        )

        if not value:
            return

        key = (
            value,
            barcode_type,
        )

        if key not in found:

            found[key] = {
                "value":
                    value,

                "type":
                    barcode_type,

                "method":
                    method,

                "database":
                    not find_product(
                        value
                    ).empty,
            }

    # --------------------------------------------------------
    # ORIGINAL
    # --------------------------------------------------------

    for result in decode_zxing(
        image
    ):

        register(
            result["value"],
            result["type"],
            "ZXing / original",
        )

    for result in decode_opencv(
        image
    ):

        register(
            result["value"],
            result["type"],
            "OpenCV / original",
        )

    # --------------------------------------------------------
    # LOCALIZED REGIONS
    # --------------------------------------------------------

    for index, crop in enumerate(
        barcode_regions(
            image
        )
    ):

        for result in decode_zxing(
            crop
        ):

            register(
                result["value"],
                result["type"],
                f"ZXing / region {index + 1}",
            )

        for result in decode_opencv(
            crop
        ):

            register(
                result["value"],
                result["type"],
                f"OpenCV / region {index + 1}",
            )

        if any(
            item["database"]
            for item in found.values()
        ):

            break

    # --------------------------------------------------------
    # CENTER
    # --------------------------------------------------------

    width, height = image.size

    center = image.crop(
        (
            int(width * .03),
            int(height * .10),
            int(width * .97),
            int(height * .90),
        )
    )

    for result in decode_zxing(
        center
    ):

        register(
            result["value"],
            result["type"],
            "ZXing / center",
        )

    # --------------------------------------------------------
    # VARIANTS
    # --------------------------------------------------------

    for index, variant in enumerate(
        scanner_variants(
            image
        )
    ):

        for result in decode_zxing(
            variant
        ):

            register(
                result["value"],
                result["type"],
                f"ZXing / variant {index + 1}",
            )

        if any(
            item["database"]
            for item in found.values()
        ):

            break

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    results = list(
        found.values()
    )

    results.sort(
        key=lambda item: (
            int(
                item["database"]
            ),
            int(
                item["value"].isdigit()
            ),
            len(
                item["value"]
            ),
        ),
        reverse=True,
    )

    return results


# ============================================================
# CAMERA UI
# ============================================================

def scanner_ui():

    st.markdown(
        """
        <div class="scanner-card">

            <h2>
                📷 قارئ الباركود
            </h2>

            <p>
                صوّر الباركود، وسيتم التعرف عليه
                ومطابقته مباشرة مع المخزون.
            </p>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="guide">

            📦 قرّب الهاتف من الباركود
            واجعله واضحاً وكبيراً داخل الصورة.

        </div>
        """,
        unsafe_allow_html=True,
    )

    if not ZXING_AVAILABLE:

        st.error(
            "ZXing-C++ غير مثبت."
        )

        return

    photo = st.camera_input(
        "📷 التقاط صورة للباركود",
        key="main_barcode_camera",
    )

    upload = st.file_uploader(
        "أو اختر صورة من الجهاز",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
        ],
        key="barcode_upload",
    )

    source = (
        photo
        if photo is not None
        else upload
    )

    if source is None:

        return

    col1, col2 = st.columns(
        [1.3, 1],
        gap="large",
    )

    with col1:

        st.image(
            source,
            caption="الصورة",
            use_container_width=True,
        )

    with col2:

        if st.button(
            "🔍 قراءة الباركود",
            type="primary",
            use_container_width=True,
        ):

            with st.spinner(
                "جاري تحليل الباركود..."
            ):

                results = scan_barcode(
                    source
                )

            if not results:

                st.error(
                    "❌ لم يتم العثور على باركود."
                )

                st.info(
                    "قرّب الهاتف أكثر من الباركود "
                    "واجعل الخطوط واضحة."
                )

                return

            best = results[0]

            value = best[
                "value"
            ]

            st.success(
                f"✓ تم اكتشاف: {value}"
            )

            st.caption(
                f"{best['type']} — {best['method']}"
            )

            matches = find_product(
                value
            )

            if not matches.empty:

                show_product(
                    matches.iloc[0]
                )

            else:

                st.warning(
                    "تمت قراءة الباركود، "
                    "لكن الرقم غير موجود في المخزون."
                )

                show_similar(
                    value
                )

            if len(results) > 1:

                with st.expander(
                    "نتائج أخرى"
                ):

                    for result in results:

                        st.write(
                            result["value"],
                            "—",
                            result["type"],
                            "—",
                            result["method"],
                        )


# ============================================================
# MANUAL SEARCH
# ============================================================

def manual_search():

    st.markdown(
        """
        <div class="card">

            <h2 style="
                color:#f8fafc;
                margin-top:0;
            ">
                🔎 البحث عن منتج
            </h2>

            <p style="
                color:#94a3b8;
            ">
                أدخل الكود أو الباركود.
            </p>

        </div>
        """,
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "الكود / الباركود",
        placeholder="اكتب الرقم هنا...",
        key="manual_search",
    ).strip()

    if not query:

        return

    matches = find_product(
        query
    )

    if not matches.empty:

        show_product(
            matches.iloc[0]
        )

    else:

        st.error(
            "❌ المنتج غير موجود."
        )

        show_similar(
            query
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="header">

        <h1>
            📦 Holland Bazar T&D
        </h1>

        <p>
            نظام البحث الذكي عن المنتجات والمخزون
        </p>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TABS
# ============================================================

search_tab, scanner_tab = st.tabs(
    [
        "🔎 البحث",
        "📷 مسح الباركود",
    ]
)


# ============================================================
# SEARCH
# ============================================================

with search_tab:

    manual_search()

    st.divider()

    c1, c2, c3 = st.columns(
        3
    )

    with c1:

        st.metric(
            "المنتجات",
            f"{len(df):,}",
        )

    with c2:

        count = (
            df["1"]
            .replace(
                "",
                np.nan,
            )
            .notna()
            .sum()
        )

        st.metric(
            "الباركودات",
            f"{count:,}",
        )

    with c3:

        count = (
            df["0"]
            .replace(
                "",
                np.nan,
            )
            .notna()
            .sum()
        )

        st.metric(
            "الأكواد",
            f"{count:,}",
        )


# ============================================================
# SCANNER
# ============================================================

with scanner_tab:

    scanner_ui()

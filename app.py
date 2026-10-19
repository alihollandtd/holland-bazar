import streamlit as st
import pandas as pd
import os
import asyncio
import tempfile
import shutil
from pathlib import Path

# ============================================================
# IMPORTANT
# ============================================================
# We use async-mega-py.
#
# DO NOT install mega.py separately.
#
# ============================================================

from mega.client import MegaNzClient


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Holland Bazar T&D",
    layout="centered",
    page_icon="📦"
)


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

.stApp {
    direction: rtl;
    text-align: right;
}

div.stButton > button:first-child {
    background-color: #2e7d32;
    color: white;
    font-size: 18px;
    width: 100%;
}

.metric-box {
    padding: 20px;
    background-color: #1e293b;
    border: 2px solid #334155;
    border-radius: 12px;
    margin-bottom: 15px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
}

.metric-box h3 {
    color: #f8fafc !important;
    font-size: 22px;
    margin-bottom: 10px;
    line-height: 1.5;
}

.metric-box p {
    color: #cbd5e1 !important;
    font-size: 16px;
    margin: 5px 0;
}

.metric-box h2 {
    color: #4ade80 !important;
    font-size: 26px;
    margin-top: 15px;
    line-height: 1.5;
}

.metric-box hr {
    border-color: #475569;
}

.suggestion-box {
    padding: 10px 15px;
    background-color: #334155;
    border-radius: 8px;
    margin-top: 5px;
}

.photo-box {
    padding: 15px;
    background-color: #1e293b;
    border-radius: 12px;
    border: 1px solid #334155;
    margin-top: 10px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SETTINGS
# ============================================================

EXCEL_PATH = "DATABASE.xlsx"

MEGA_FOLDER_URL = (
    "https://mega.nz/folder/"
    "HrximbwC#9wvR9D8OQnrAJlTItE6Oag"
)

# Persistent local cache.
# Streamlit Cloud keeps this during the running instance.
IMAGE_CACHE_DIR = Path("image_cache")
IMAGE_CACHE_DIR.mkdir(exist_ok=True)


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
            dtype=str
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

    except Exception as e:

        st.error(
            f"خطأ في قراءة DATABASE.xlsx: {e}"
        )

        return None


df = load_data()


# ============================================================
# MEGA DOWNLOAD
# ============================================================

async def download_mega_folder():

    """
    Downloads the public MEGA folder to a temporary directory.

    Returns:
        Path to downloaded folder
    """

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="mega_inventory_"
        )
    )

    try:

        async with MegaNzClient() as mega:

            # Parse your public folder URL
            public_handle, public_key, selected_node = (
                mega.parse_folder_url(
                    MEGA_FOLDER_URL
                )
            )

            # Download public folder
            await mega.download_public_folder(
                public_handle,
                public_key,
                temp_dir,
                selected_node
            )

        return temp_dir

    except Exception:

        # Clean temporary directory if download failed
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        raise


# ============================================================
# FIND IMAGE
# ============================================================

def find_image_in_directory(
    directory,
    target_name
):

    target_name = str(
        target_name
    ).strip().casefold()

    valid_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    }

    for root, dirs, files in os.walk(directory):

        for filename in files:

            path = Path(root) / filename

            if path.suffix.casefold() not in valid_extensions:
                continue

            stem = path.stem.strip().casefold()

            if stem == target_name:

                return path

    return None


# ============================================================
# GET PRODUCT IMAGE
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False
)
def get_product_image(target_name):

    """
    Looks for the product image in the public MEGA folder.

    The image must be named using the barcode/code:

        123456.png
        123456.jpg
        123456.jpeg
        123456.webp
    """

    target_name = str(
        target_name
    ).strip()

    if not target_name:
        return None


    # --------------------------------------------------------
    # CHECK CACHE
    # --------------------------------------------------------

    cached_extensions = [
        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    ]

    for extension in cached_extensions:

        cached_file = (
            IMAGE_CACHE_DIR /
            f"{target_name}{extension}"
        )

        if cached_file.exists():

            return str(cached_file)


    # --------------------------------------------------------
    # DOWNLOAD MEGA FOLDER
    # --------------------------------------------------------

    try:

        downloaded_folder = asyncio.run(
            download_mega_folder()
        )

    except Exception as e:

        return {
            "error": str(e)
        }


    # --------------------------------------------------------
    # FIND TARGET IMAGE
    # --------------------------------------------------------

    image_path = find_image_in_directory(
        downloaded_folder,
        target_name
    )


    # --------------------------------------------------------
    # IMAGE FOUND
    # --------------------------------------------------------

    if image_path:

        destination = (
            IMAGE_CACHE_DIR /
            image_path.name
        )

        try:

            shutil.copy2(
                image_path,
                destination
            )

        except Exception:

            return {
                "error": (
                    "تعذر حفظ صورة المنتج."
                )
            }

        # Remove temporary MEGA download
        shutil.rmtree(
            downloaded_folder,
            ignore_errors=True
        )

        return str(destination)


    # --------------------------------------------------------
    # IMAGE NOT FOUND
    # --------------------------------------------------------

    shutil.rmtree(
        downloaded_folder,
        ignore_errors=True
    )

    return None


# ============================================================
# HEADER
# ============================================================

st.title("📦 Holland Bazar T&D")


# ============================================================
# SEARCH BOX
# ============================================================

search_query = st.text_input(
    "🔍 أدخل الباركود أو الرمز (كود) للبحث:",
    key="main_search"
).strip()


# ============================================================
# DATABASE VALIDATION
# ============================================================

if df is None:

    st.error(
        "❌ تأكد من وجود ملف DATABASE.xlsx "
        "في المستودع بجوار app.py."
    )

    st.stop()


if df.empty:

    st.error(
        "❌ ملف DATABASE.xlsx فارغ."
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

if search_query:

    exact_match = df[
        (df[col_barcode] == search_query)
        |
        (df[col_code] == search_query)
    ]


    # ========================================================
    # EXACT MATCH
    # ========================================================

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


        # ----------------------------------------------------
        # CLEAN BARCODE
        # ----------------------------------------------------

        if (
            barcode.lower() == "nan"
            or barcode == ""
        ):

            barcode = "غير متوفر"


        # ----------------------------------------------------
        # CLEAN QUANTITY
        # ----------------------------------------------------

        if (
            quantity.lower() == "nan"
            or quantity == ""
        ):

            quantity = "0"


        # ====================================================
        # PRODUCT INFORMATION
        # ====================================================

        st.markdown(
            f"""
            <div class="metric-box">

                <h3>
                    📝 الوصف: {description}
                </h3>

                <p>
                    <b>كود المنتج:</b> {code}
                </p>

                <p>
                    <b>الباركود:</b> {barcode}
                </p>

                <hr>

                <h2>
                    📊 الكمية في السستم: {quantity}
                </h2>

            </div>
            """,
            unsafe_allow_html=True
        )


        # ====================================================
        # PRODUCT PHOTO
        # ====================================================

        st.markdown(
            "### 📷 صورة المنتج"
        )


        # Use barcode first.
        # If barcode isn't available, use code.

        target_name = (
            barcode
            if barcode != "غير متوفر"
            else code
        )


        with st.spinner(
            "📷 جاري البحث عن صورة المنتج..."
        ):

            image_result = get_product_image(
                target_name
            )


        # ====================================================
        # IMAGE FOUND
        # ====================================================

        if (
            isinstance(image_result, str)
            and os.path.exists(image_result)
        ):

            st.markdown(
                '<div class="photo-box">',
                unsafe_allow_html=True
            )

            st.image(
                image_result,
                caption=(
                    f"الصورة الأصلية للمنتج: {code}"
                ),
                use_container_width=True
            )

            st.markdown(
                '</div>',
                unsafe_allow_html=True
            )


        # ====================================================
        # IMAGE NOT FOUND
        # ====================================================

        elif image_result is None:

            st.info(
                f"""
                📷 لا توجد صورة لهذا المنتج.

                النظام يبحث عن صورة باسم:

                `{target_name}.png`

                أو

                `{target_name}.jpg`

                أو

                `{target_name}.jpeg`

                أو

                `{target_name}.webp`
                """
            )


        # ====================================================
        # MEGA ERROR
        # ====================================================

        elif isinstance(image_result, dict):

            error_text = image_result.get(
                "error",
                "خطأ غير معروف"
            )

            st.error(
                f"""
                ❌ حدث خطأ أثناء قراءة صور MEGA:

                {error_text}
                """
            )


    # ========================================================
    # NO EXACT MATCH
    # ========================================================

    else:

        st.error(
            f"""
            ❌ لم يتم العثور على تطابق كامل
            للرمز المكتوب: ({search_query})
            """
        )


        # ----------------------------------------------------
        # SIMILAR MATCHES
        # ----------------------------------------------------

        similar_matches = df[
            df[col_code].str.contains(
                search_query,
                na=False,
                case=False,
                regex=False
            )
            |
            df[col_barcode].str.contains(
                search_query,
                na=False,
                case=False,
                regex=False
            )
        ]


        if not similar_matches.empty:

            st.markdown(
                "### 💡 هل تقصد أحد هذه الرموز القريبة؟"
            )


            for _, row in similar_matches.head(5).iterrows():

                sim_code = row[col_code]

                sim_desc = row[col_desc]


                st.markdown(
                    f"""
                    <div class="suggestion-box">

                        <p style="
                            color:#4ade80;
                            font-weight:bold;
                            margin:0;
                        ">
                            كود المنتج المقترح:
                            {sim_code}
                        </p>

                        <p style="
                            color:#f1f5f9;
                            margin:2px 0;
                        ">
                            📝 الوصف:
                            {sim_desc}
                        </p>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


# ============================================================
# INITIAL SCREEN
# ============================================================

else:

    st.markdown(
        """
        <div class="metric-box">

            <h3>
                🔎 ابحث عن منتج
            </h3>

            <p>
                أدخل الباركود أو كود المنتج
                لعرض معلومات المخزون والصورة.
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )

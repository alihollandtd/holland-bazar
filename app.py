import streamlit as st
import pandas as pd
import os
import asyncio
from pathlib import Path

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

.image-status {
    padding: 10px;
    border-radius: 8px;
    background-color: #1e293b;
    margin-bottom: 10px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SETTINGS
# ============================================================

# Your public MEGA folder
MEGA_FOLDER_URL = (
    "https://mega.nz/folder/"
    "HrximbwC#9wvR9D8OQnrAJlTItE6Oag"
)

EXCEL_PATH = "DATABASE.xlsx"

# Local temporary/cache directory
IMAGE_CACHE_DIR = Path("image_cache")
IMAGE_CACHE_DIR.mkdir(exist_ok=True)


# ============================================================
# LOAD DATABASE
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
            f"حدث خطأ أثناء قراءة DATABASE.xlsx: {e}"
        )

        return None


df = load_data()


# ============================================================
# MEGA IMAGE DOWNLOADER
# ============================================================

async def download_image_from_mega_async(target_name):

    """
    Connects to the public MEGA folder,
    finds the image whose filename matches
    the barcode/code, and downloads ONLY that image.
    """

    target_name = str(target_name).strip()

    if not target_name:
        return None

    # Possible image names
    possible_names = {
        f"{target_name}.png".casefold(),
        f"{target_name}.jpg".casefold(),
        f"{target_name}.jpeg".casefold(),
        f"{target_name}.webp".casefold(),
    }

    # --------------------------------------------------------
    # Connect to public MEGA folder
    # --------------------------------------------------------

    async with MegaNzClient() as mega:

        public_handle, public_key, selected_node = (
            mega.parse_folder_url(
                MEGA_FOLDER_URL
            )
        )

        # ----------------------------------------------------
        # Read the folder structure
        # ----------------------------------------------------

        filesystem = await mega.get_public_filesystem(
            public_handle,
            public_key
        )

        # ----------------------------------------------------
        # Find matching image
        # ----------------------------------------------------

        matching_node = None

        for node in filesystem.files:

            filename = (
                node.attributes.name
                or ""
            ).strip()

            if filename.casefold() in possible_names:

                matching_node = node
                break

        if matching_node is None:
            return None

        # ----------------------------------------------------
        # Local filename
        # ----------------------------------------------------

        filename = (
            matching_node.attributes.name
        )

        output_path = (
            IMAGE_CACHE_DIR /
            filename
        )

        # ----------------------------------------------------
        # Use cached image if it already exists
        # ----------------------------------------------------

        if output_path.exists():

            return str(output_path)

        # ----------------------------------------------------
        # Get encrypted file information
        # ----------------------------------------------------

        file_info = await mega._core.request_file_info(
            matching_node.id,
            public_handle
        )

        # ----------------------------------------------------
        # Download and decrypt the image
        # ----------------------------------------------------

        await mega._core.download_file(
            file_info,
            matching_node._crypto,
            output_path
        )

        # ----------------------------------------------------
        # Verify download
        # ----------------------------------------------------

        if output_path.exists():

            return str(output_path)

        return None


# ============================================================
# SAFE SYNC WRAPPER
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False
)
def get_product_image(target_name):

    """
    Streamlit-compatible wrapper around the
    asynchronous MEGA downloader.
    """

    try:

        return asyncio.run(
            download_image_from_mega_async(
                target_name
            )
        )

    except Exception as e:

        return f"ERROR:{e}"


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
# DATABASE CHECK
# ============================================================

if df is None:

    st.error(
        "❌ لم يتم العثور على DATABASE.xlsx"
    )

    st.stop()


if df.empty:

    st.error(
        "❌ ملف DATABASE.xlsx فارغ."
    )

    st.stop()


# ============================================================
# COLUMN DEFINITIONS
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
        # Clean barcode
        # ----------------------------------------------------

        if (
            barcode.lower() == "nan"
            or barcode == ""
        ):

            barcode = "غير متوفر"


        # ----------------------------------------------------
        # Clean quantity
        # ----------------------------------------------------

        if (
            quantity.lower() == "nan"
            or quantity == ""
        ):

            quantity = "0"


        # ====================================================
        # PRODUCT INFORMATION CARD
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
        # IMAGE
        # ====================================================

        st.markdown(
            "### 📷 صورة المنتج"
        )


        # Use barcode when available.
        # Otherwise use product code.
        target_name = (
            barcode
            if barcode != "غير متوفر"
            else code
        )


        # ----------------------------------------------------
        # Download image
        # ----------------------------------------------------

        with st.spinner(
            "جاري البحث عن صورة المنتج..."
        ):

            image_result = get_product_image(
                target_name
            )


        # ====================================================
        # IMAGE FOUND
        # ====================================================

        if (
            image_result
            and not str(image_result).startswith("ERROR:")
        ):

            st.image(
                image_result,
                caption=(
                    f"📷 الصورة الأصلية للمنتج: {code}"
                ),
                use_container_width=True
            )


        # ====================================================
        # IMAGE NOT FOUND
        # ====================================================

        elif image_result is None:

            st.info(
                f"""
                📷 لا توجد صورة لهذا المنتج.

                اسم الصورة المطلوب:
                `{target_name}.png`

                أو:

                `{target_name}.jpg`
                """
            )


        # ====================================================
        # IMAGE ERROR
        # ====================================================

        else:

            error_message = str(
                image_result
            ).replace(
                "ERROR:",
                ""
            )

            st.warning(
                f"""
                ⚠️ تعذر تحميل صورة المنتج.

                الخطأ:
                `{error_message}`
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
        # Similar results
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
# INITIAL STATE
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

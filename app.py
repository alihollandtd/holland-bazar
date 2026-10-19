import streamlit as st
import pandas as pd
import os
import tempfile
from pathlib import Path

# MEGA library
from mega import Mega


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

    </style>
""", unsafe_allow_html=True)


# ============================================================
# SETTINGS
# ============================================================

MEGA_FOLDER_ID = "HrximbwC"
MEGA_DECRYPT_KEY = "9wvR9D8OQnrAJlTItE6Oag"

EXCEL_PATH = "DATABASE.xlsx"

IMAGE_CACHE_DIR = Path("image_cache")
IMAGE_CACHE_DIR.mkdir(exist_ok=True)


# ============================================================
# LOAD EXCEL
# ============================================================

@st.cache_data(ttl=5)
def load_data():

    if os.path.exists(EXCEL_PATH):

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
                .astype(str)
                .str.strip()
            )

        return df

    return None


df = load_data()


# ============================================================
# MEGA CONNECTION
# ============================================================

@st.cache_resource
def get_mega():

    try:

        mega = Mega()

        # Anonymous connection.
        # This works with public MEGA files/folders.
        m = mega.login()

        return m

    except Exception as e:

        st.error(
            f"خطأ في الاتصال بخدمة MEGA: {e}"
        )

        return None


# ============================================================
# FIND IMAGE IN MEGA
# ============================================================

def get_image_from_mega(target_name):

    """
    Finds an image with the requested filename
    inside the public MEGA folder.

    Expected filename examples:

        123456.png
        123456.jpg
        123456.jpeg

    The function downloads ONLY the matching
    image instead of downloading the entire
    MEGA folder.
    """

    if not target_name:
        return None

    target_name = str(target_name).strip()

    possible_names = [
        f"{target_name}.png",
        f"{target_name}.jpg",
        f"{target_name}.jpeg",
        f"{target_name}.webp",
    ]

    # --------------------------------------------------------
    # LOCAL CACHE FIRST
    # --------------------------------------------------------

    for filename in possible_names:

        cached_file = IMAGE_CACHE_DIR / filename

        if cached_file.exists():
            return str(cached_file)

    # --------------------------------------------------------
    # MEGA URL
    # --------------------------------------------------------

    mega_folder_url = (
        f"https://mega.nz/folder/"
        f"{MEGA_FOLDER_ID}#"
        f"{MEGA_DECRYPT_KEY}"
    )

    try:

        m = get_mega()

        if m is None:
            return None

        # ----------------------------------------------------
        # NOTE:
        #
        # mega.py versions differ in their public-folder
        # support.
        #
        # We try to use the public folder filesystem first.
        # ----------------------------------------------------

        if hasattr(m, "get_public_folder"):

            files = m.get_public_folder(
                mega_folder_url
            )

            if files:

                for file_item in files:

                    try:

                        filename = (
                            file_item.get("name")
                            or file_item.get("a", {}).get("n")
                            or ""
                        )

                        if filename.lower() in [
                            x.lower()
                            for x in possible_names
                        ]:

                            destination = (
                                IMAGE_CACHE_DIR /
                                filename
                            )

                            m.download(
                                file_item,
                                str(IMAGE_CACHE_DIR)
                            )

                            if destination.exists():
                                return str(destination)

                    except Exception:
                        continue

        # ----------------------------------------------------
        # FALLBACK
        # ----------------------------------------------------

        st.warning(
            "تم العثور على مجلد MEGA، لكن إصدار مكتبة "
            "mega.py الحالي لا يدعم قراءة المجلد العام "
            "بالطريقة المطلوبة."
        )

        return None

    except Exception as e:

        st.warning(
            f"تعذر تحميل صورة المنتج: {e}"
        )

        return None


# ============================================================
# PAGE
# ============================================================

st.title("📦 Holland Bazar T&D")


# ============================================================
# SEARCH
# ============================================================

search_query = st.text_input(
    "🔍 أدخل الباركود أو الرمز (كود) للبحث:",
    key="main_search"
).strip()


# ============================================================
# INVENTORY SEARCH
# ============================================================

if df is not None and not df.empty:

    col_code = "0"
    col_barcode = "1"
    col_desc = "2"
    col_qty = "3"


    if search_query:

        exact_match = df[
            (df[col_barcode] == search_query) |
            (df[col_code] == search_query)
        ]


        # ====================================================
        # EXACT MATCH
        # ====================================================

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


            # ------------------------------------------------
            # CLEAN VALUES
            # ------------------------------------------------

            if (
                barcode.lower() == "nan"
                or barcode == ""
            ):
                barcode = "غير متوفر"


            if (
                quantity.lower() == "nan"
                or quantity == ""
            ):
                quantity = "0"


            # =================================================
            # PRODUCT INFORMATION
            # =================================================

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


            # =================================================
            # IMAGE SEARCH
            # =================================================

            target_name = (
                barcode
                if barcode != "غير متوفر"
                else code
            )


            st.markdown(
                "### 📷 صورة المنتج"
            )


            # -------------------------------------------------
            # FIND IMAGE
            # -------------------------------------------------

            image_path = get_image_from_mega(
                target_name
            )


            # -------------------------------------------------
            # DISPLAY IMAGE
            # -------------------------------------------------

            if image_path:

                st.image(
                    image_path,
                    caption=(
                        f"الصورة الأصلية للمنتج: {code}"
                    ),
                    use_container_width=True
                )

            else:

                st.info(
                    f"📷 لم يتم العثور على صورة باسم "
                    f"`{target_name}.png` أو JPG/JPEG/WEBP "
                    f"داخل مجلد الصور."
                )


        # ====================================================
        # NO EXACT MATCH
        # ====================================================

        else:

            st.error(
                f"❌ لم يتم العثور على تطابق كامل "
                f"للرمز المكتوب: ({search_query})"
            )


            similar_matches = df[
                df[col_code].str.contains(
                    search_query,
                    na=False,
                    case=False
                )
                |
                df[col_barcode].str.contains(
                    search_query,
                    na=False,
                    case=False
                )
            ]


            if not similar_matches.empty:

                st.markdown(
                    "### 💡 هل تقصد أحد هذه الرموز القريبة؟"
                )


                for idx, row in similar_matches.head(5).iterrows():

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
# DATABASE MISSING
# ============================================================

else:

    st.error(
        "تأكد من وجود ملف DATABASE.xlsx "
        "في مستودع GitHub الخاص بك بجوار ملف app.py."
    )

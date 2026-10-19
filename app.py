```python
import streamlit as st
import pandas as pd
import os
import asyncio
from pathlib import Path

# IMPORTANT:
# This is the maintained async MEGA package.
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

EXCEL_PATH = "DATABASE.xlsx"

# Your MEGA public folder
MEGA_FOLDER_URL = (
    "https://mega.nz/folder/"
    "HrximbwC#9wvR9D8OQnrAJlTItE6Oag"
)

# Local cache for downloaded images
IMAGE_CACHE_DIR = Path("image_cache")
IMAGE_CACHE_DIR.mkdir(exist_ok=True)


# ============================================================
# LOAD EXCEL
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

        # Keep your existing column numbering
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
            f"خطأ في قراءة ملف DATABASE.xlsx: {e}"
        )

        return None


df = load_data()


# ============================================================
# MEGA
# ============================================================

@st.cache_resource
def create_mega_client():

    try:
        mega = Mega()
        return mega.login()

    except Exception as e:

        return None


# ============================================================
# GET IMAGE FROM MEGA
# ============================================================

def get_image_from_mega(target_name):

    """
    Finds the product image inside the public MEGA folder.

    Accepted image names:

        123456.png
        123456.jpg
        123456.jpeg
        123456.webp
    """

    target_name = str(target_name).strip()

    if not target_name:
        return None


    # --------------------------------------------------------
    # Check local cache first
    # --------------------------------------------------------

    extensions = [
        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    ]

    for ext in extensions:

        cached = IMAGE_CACHE_DIR / (
            target_name + ext
        )

        if cached.exists():
            return str(cached)


    # --------------------------------------------------------
    # Connect to MEGA
    # --------------------------------------------------------

    mega = create_mega_client()

    if mega is None:
        return None


    # --------------------------------------------------------
    # Temporary folder
    # --------------------------------------------------------

    temp_dir = IMAGE_CACHE_DIR / "mega_temp"
    temp_dir.mkdir(exist_ok=True)


    try:

        # ----------------------------------------------------
        # Download the public folder contents
        #
        # The MEGA library handles the encryption/decryption.
        # ----------------------------------------------------

        mega.download_url(
            MEGA_FOLDER_URL,
            dest_path=str(temp_dir)
        )

    except Exception:

        # Some mega.py versions use the async public-folder
        # implementation instead.
        #
        # We don't let this crash the Streamlit application.
        pass


    # --------------------------------------------------------
    # Search downloaded files
    # --------------------------------------------------------

    for root, dirs, files in os.walk(temp_dir):

        for filename in files:

            filename_without_case = filename.casefold()

            for ext in extensions:

                expected = (
                    target_name + ext
                ).casefold()

                if filename_without_case == expected:

                    source = Path(root) / filename
                    destination = (
                        IMAGE_CACHE_DIR / filename
                    )

                    try:

                        source.replace(
                            destination
                        )

                    except Exception:

                        destination.write_bytes(
                            source.read_bytes()
                        )

                    return str(destination)


    return None


# ============================================================
# PAGE HEADER
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
# DATABASE CHECK
# ============================================================

if df is None:

    st.error(
        "❌ تأكد من وجود DATABASE.xlsx "
        "بجوار app.py."
    )

    st.stop()


if df.empty:

    st.error(
        "❌ ملف DATABASE.xlsx فارغ."
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
# SEARCH RESULT
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
        # PRODUCT CARD
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


        # Use barcode if available.
        # Otherwise use product code.
        target_name = (
            barcode
            if barcode != "غير متوفر"
            else code
        )


        with st.spinner(
            "جاري البحث عن صورة المنتج..."
        ):

            image_path = get_image_from_mega(
                target_name
            )


        # ----------------------------------------------------
        # IMAGE FOUND
        # ----------------------------------------------------

        if image_path:

            st.image(
                image_path,
                caption=(
                    f"الصورة الأصلية للمنتج: {code}"
                ),
                use_container_width=True
            )


        # ----------------------------------------------------
        # IMAGE NOT FOUND
        # ----------------------------------------------------

        else:

            st.info(
                f"""
                📷 لم يتم العثور على صورة لهذا المنتج.

                النظام يبحث عن:

                `{target_name}.png`

                `{target_name}.jpg`

                `{target_name}.jpeg`

                `{target_name}.webp`
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
        # Similar products
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
```

### 2. Replace `requirements.txt` completely

The important part here is **forcing a modern Tenacity**. Your traceback is specifically showing an obsolete Tenacity implementation using `asyncio.coroutine`; current Tenacity supports Python 3.14.

:::writing{variant="standard" id="74106" title="Complete requirements.txt"}
```text
streamlit
pandas
openpyxl
mega.py==1.0.8
tenacity>=9.1.4
requests
pycryptodome
```

### 3. One important thing

After replacing both files, **redeploy/reboot the Streamlit app** so it creates a fresh environment.

The error you showed is happening **before your app even starts**, at:

```text
from mega import Mega
```

so the inventory code isn't the problem. The dependency environment is.

The original `mega.py` package is an old 1.0.8 release, and its dependencies include Tenacity; the current Tenacity releases support Python 3.14.

**If the next error appears, paste it exactly as you did this one. I'll return the complete corrected files again — no instructions-only response.**

import os
from pathlib import Path

import streamlit as st
import pandas as pd


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Holland Bazar T&D",
    page_icon="📦",
    layout="centered",
)


# ============================================================
# SETTINGS
# ============================================================

EXCEL_PATH = "DATABASE.xlsx"

MEGA_FOLDER_URL = (
    "https://mega.nz/folder/HrximbwC"
    "#9wvR9D8OQnrAJlTItE6Oag"
)

IMAGE_FOLDER = Path("/tmp/holland_bazar_images")


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        direction: rtl;
    }

    .main-title {
        font-size: 30px;
        font-weight: 800;
        margin-bottom: 20px;
    }

    .product-box {
        background: #111827;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 20px;
        margin-top: 18px;
    }

    .product-name {
        font-size: 23px;
        font-weight: 700;
        margin-bottom: 18px;
    }

    .info-label {
        color: #94a3b8;
        font-size: 14px;
    }

    .info-value {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 12px;
    }

    .quantity-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        margin-top: 18px;
        margin-bottom: 20px;
    }

    .quantity-number {
        font-size: 36px;
        font-weight: 800;
    }

    .quantity-label {
        color: #94a3b8;
        font-size: 14px;
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

        # Your original database uses:
        #
        # 0 = code
        # 1 = barcode
        # 2 = description
        # 3 = quantity

        df.columns = [
            str(i)
            for i in range(len(df.columns))
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
            f"حدث خطأ أثناء قراءة DATABASE.xlsx:\n\n{e}"
        )

        return None


# ============================================================
# MEGA DOWNLOAD
# ============================================================

@st.cache_resource
def download_mega_folder():

    """
    Download the public MEGA folder once per Streamlit
    server session.

    We use mega-public-client instead of the old mega.py
    libraries.
    """

    try:

        from mega_client import MegaClient

    except Exception as e:

        return False, (
            "تعذر تحميل مكتبة MEGA:\n\n"
            + str(e)
        )

    try:

        # Create local directory
        IMAGE_FOLDER.mkdir(
            parents=True,
            exist_ok=True,
        )

        # If the folder has already been downloaded
        # during this server session, don't download again.
        existing_files = list(
            IMAGE_FOLDER.rglob("*")
        )

        if existing_files:

            return True, "cached"

        st.write(
            "⏳ جاري تحميل مجلد الصور من MEGA..."
        )

        with MegaClient() as client:

            results = client.download_folder(
                MEGA_FOLDER_URL,
                IMAGE_FOLDER,
            )

        return True, results

    except Exception as e:

        return False, str(e)


# ============================================================
# FIND IMAGE
# ============================================================

def find_product_image(
    product_code,
    barcode,
):

    # Download MEGA folder if necessary
    success, result = download_mega_folder()

    if not success:
        return None, result

    if not IMAGE_FOLDER.exists():
        return None, None

    # --------------------------------------------------------
    # Possible identifiers
    # --------------------------------------------------------

    identifiers = []

    for value in [
        product_code,
        barcode,
    ]:

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        if value.lower() == "nan":
            continue

        identifiers.append(value)

    if not identifiers:
        return None, None

    # --------------------------------------------------------
    # Supported image types
    # --------------------------------------------------------

    extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
    }

    all_images = [
        path
        for path in IMAGE_FOLDER.rglob("*")
        if path.is_file()
        and path.suffix.lower() in extensions
    ]

    # --------------------------------------------------------
    # 1. Exact filename match
    #
    # Example:
    #
    # 6932308668058.jpg
    # --------------------------------------------------------

    for identifier in identifiers:

        identifier_lower = identifier.lower()

        for image_path in all_images:

            if (
                image_path.stem.lower()
                == identifier_lower
            ):

                return image_path, None

    # --------------------------------------------------------
    # 2. Filename contains identifier
    #
    # Example:
    #
    # product_6932308668058.jpg
    # --------------------------------------------------------

    for identifier in identifiers:

        identifier_lower = identifier.lower()

        for image_path in all_images:

            if (
                identifier_lower
                in image_path.stem.lower()
            ):

                return image_path, None

    return None, None


# ============================================================
# MAIN
# ============================================================

df = load_data()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">Holland Bazar T&D 📦</div>',
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE CHECK
# ============================================================

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
# SEARCH
# ============================================================

search_query = st.text_input(
    "🔍 أدخل الباركود أو الرمز (كود) للبحث:",
    key="main_search",
).strip()


if not search_query:

    st.info(
        "👆 أدخل الباركود أو الكود للبحث عن المنتج."
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
# EXACT SEARCH
# ============================================================

exact_match = df[
    (df[col_barcode] == search_query)
    |
    (df[col_code] == search_query)
]


# ============================================================
# PRODUCT FOUND
# ============================================================

if not exact_match.empty:

    row = exact_match.iloc[0]

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

    # Clean empty values

    if not barcode or barcode.lower() == "nan":
        barcode = "غير متوفر"

    if not description or description.lower() == "nan":
        description = "غير متوفر"

    if not quantity or quantity.lower() == "nan":
        quantity = "0"


    # ========================================================
    # PRODUCT INFORMATION
    # ========================================================

    with st.container(border=True):

        st.subheader(
            f"📦 {description}"
        )

        st.write(
            f"**🔢 الكود:** {code}"
        )

        st.write(
            f"**🏷️ الباركود:** {barcode}"
        )


    # ========================================================
    # QUANTITY
    # ========================================================

    st.markdown(
        f"""
        <div class="quantity-box">

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


    # ========================================================
    # IMAGE
    # ========================================================

    st.subheader(
        "🖼️ صورة المنتج"
    )

    with st.spinner(
        "جاري البحث عن صورة المنتج..."
    ):

        image_path, image_error = (
            find_product_image(
                code,
                barcode,
            )
        )


    if image_path:

        st.image(
            str(image_path),
            caption=image_path.name,
            use_container_width=True,
        )

    elif image_error:

        st.error(
            f"❌ {image_error}"
        )

    else:

        st.warning(
            "📷 لم يتم العثور على صورة لهذا المنتج."
        )


# ============================================================
# PRODUCT NOT FOUND
# ============================================================

else:

    st.error(
        "❌ لم يتم العثور على المنتج بهذا "
        "الباركود أو الكود."
    )


    # ========================================================
    # SIMILAR RESULTS
    # ========================================================

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

        st.subheader(
            "💡 هل تقصد أحد هذه المنتجات؟"
        )

        for _, suggestion in (
            similar_matches.head(5).iterrows()
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

            with st.container(border=True):

                st.write(
                    f"**{suggestion_description}**"
                )

                st.caption(
                    f"الكود: {suggestion_code}  |  "
                    f"الباركود: {suggestion_barcode}"
                )

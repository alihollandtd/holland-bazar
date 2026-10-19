# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       GLOBAL
       ======================================================== */

    .stApp {
        direction: rtl;
        text-align: right;
        background:
            radial-gradient(
                circle at top right,
                rgba(59, 130, 246, 0.07),
                transparent 30%
            ),
            #f8fafc;
        color: #0f172a;
    }

    .main {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .block-container {
        max-width: 1050px;
        padding-top: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-bottom: 4rem;
    }


    /* ========================================================
       MAIN TITLE
       ======================================================== */

    .main-title {
        font-size: 32px;
        font-weight: 900;
        letter-spacing: -0.7px;
        margin-bottom: 28px;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 10px;
    }


    /* ========================================================
       TEXT INPUT / SEARCH
       ======================================================== */

    div[data-testid="stTextInput"] {
        margin-bottom: 24px;
    }

    div[data-testid="stTextInput"] label {
        font-size: 15px;
        font-weight: 700;
        color: #334155;
        margin-bottom: 8px;
    }

    div[data-testid="stTextInput"] input {
        height: 52px;
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        background: #ffffff;
        color: #0f172a;
        font-size: 16px;
        font-weight: 500;
        padding: 0 16px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        transition:
            border-color 0.2s ease,
            box-shadow 0.2s ease,
            transform 0.2s ease;
    }

    div[data-testid="stTextInput"] input:hover {
        border-color: #94a3b8;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #2563eb;
        box-shadow:
            0 0 0 3px rgba(37, 99, 235, 0.12),
            0 4px 14px rgba(15, 23, 42, 0.06);
        outline: none;
    }


    /* ========================================================
       CONTAINERS / PRODUCT CARDS
       ======================================================== */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        box-shadow:
            0 4px 16px rgba(15, 23, 42, 0.05);
        padding: 4px;
        transition:
            box-shadow 0.2s ease,
            transform 0.2s ease;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow:
            0 8px 26px rgba(15, 23, 42, 0.08);
    }


    /* ========================================================
       HEADINGS
       ======================================================== */

    h1, h2, h3 {
        color: #0f172a !important;
        letter-spacing: -0.3px;
    }

    h3 {
        font-size: 21px !important;
        font-weight: 800 !important;
        margin-top: 4px !important;
        margin-bottom: 14px !important;
    }


    /* ========================================================
       NORMAL TEXT
       ======================================================== */

    p {
        color: #334155;
    }

    strong {
        color: #0f172a;
        font-weight: 750;
    }


    /* ========================================================
       QUANTITY CARD
       ======================================================== */

    .quantity-box {
        position: relative;
        overflow: hidden;
        background:
            linear-gradient(
                135deg,
                #0f172a 0%,
                #1e293b 100%
            );
        border: 1px solid #334155;
        border-radius: 18px;
        padding: 26px 20px;
        text-align: center;
        margin: 22px 0 28px 0;
        box-shadow:
            0 10px 25px rgba(15, 23, 42, 0.15);
    }

    .quantity-box::before {
        content: "";
        position: absolute;
        width: 160px;
        height: 160px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.04);
        top: -85px;
        right: -55px;
    }

    .quantity-box::after {
        content: "";
        position: absolute;
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.025);
        bottom: -70px;
        left: -45px;
    }

    .quantity-number {
        position: relative;
        z-index: 1;
        font-size: 42px;
        line-height: 1.1;
        font-weight: 900;
        color: #ffffff;
        letter-spacing: -1px;
    }

    .quantity-label {
        position: relative;
        z-index: 1;
        color: #cbd5e1;
        font-size: 14px;
        font-weight: 600;
        margin-top: 8px;
    }


    /* ========================================================
       IMAGE AREA
       ======================================================== */

    [data-testid="stImage"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 10px;
        margin-top: 8px;
        margin-bottom: 20px;
    }

    [data-testid="stImage"] img {
        border-radius: 10px;
    }


    /* ========================================================
       ALERTS / INFO / ERROR / WARNING
       ======================================================== */

    div[data-testid="stAlert"] {
        border-radius: 12px;
        border-width: 1px;
        font-size: 14px;
        line-height: 1.7;
    }


    /* ========================================================
       SPINNER
       ======================================================== */

    div[data-testid="stSpinner"] {
        color: #2563eb;
    }


    /* ========================================================
       CAPTIONS
       ======================================================== */

    [data-testid="stCaptionContainer"] {
        color: #64748b;
        font-size: 13px;
    }


    /* ========================================================
       DIVIDERS
       ======================================================== */

    hr {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 24px 0;
    }


    /* ========================================================
       BUTTONS
       ======================================================== */

    button {
        border-radius: 10px !important;
        font-weight: 700 !important;
    }


    /* ========================================================
       SCROLLBAR
       ======================================================== */

    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #f1f5f9;
    }

    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }


    /* ========================================================
       MOBILE / SMALL SCREENS
       ======================================================== */

    @media (max-width: 768px) {

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1.2rem;
        }

        .main-title {
            font-size: 26px;
            margin-bottom: 22px;
        }

        div[data-testid="stTextInput"] input {
            height: 50px;
            font-size: 15px;
        }

        .quantity-box {
            padding: 22px 16px;
        }

        .quantity-number {
            font-size: 36px;
        }

    }


    /* ========================================================
       REDUCE EXCESS STREAMLIT SPACING
       ======================================================== */

    div[data-testid="stVerticalBlock"] {
        gap: 0.75rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


import os
import re
import json
import struct
import base64
from io import BytesIO

import requests
import pandas as pd
import streamlit as st
import streamlit.components.v2 as components
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

SCANNER_HTML = """
<div class="scanner-shell">
    <div class="scanner-top">
        <div>
            <div class="scanner-title">📷 ماسح الباركود</div>
            <div class="scanner-caption">
                استخدم الكاميرا الخلفية وقرّب الباركود داخل الإطار
            </div>
        </div>
        <div id="scanner-status" class="scanner-status">جاهز</div>
    </div>

    <div id="scanner-reader"></div>

    <div class="scanner-actions">
        <button id="scanner-start" class="scanner-primary">
            تشغيل الكاميرا
        </button>
        <button id="scanner-stop" class="scanner-secondary" disabled>
            إيقاف
        </button>
        <button id="scanner-file" class="scanner-secondary">
            قراءة صورة
        </button>
        <input id="scanner-file-input" type="file" accept="image/*" hidden />
    </div>

    <div class="scanner-instructions">
        <b>لأفضل قراءة:</b>
        اجعل الباركود مستقيماً، قريباً، ومضاءً جيداً.
        لا تحتاج إلى الضغط على زر الالتقاط.
    </div>

    <div id="scanner-result" class="scanner-result">
        <div class="scanner-result-label">الباركود المقروء</div>
        <div id="scanner-value"></div>
    </div>

    <div id="scanner-error" class="scanner-error"></div>
</div>
"""

SCANNER_CSS = """
.scanner-shell {
    width: 100%;
    box-sizing: border-box;
    direction: rtl;
    color: var(--st-text-color, #f8fafc);
    font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif;
}
.scanner-top {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    margin-bottom:12px;
}
.scanner-title { font-size:20px; font-weight:850; }
.scanner-caption { color:#94a3b8; font-size:12px; margin-top:4px; }
.scanner-status {
    border:1px solid rgba(34,197,94,.28);
    background:rgba(34,197,94,.08);
    color:#86efac;
    border-radius:999px;
    padding:7px 12px;
    font-size:12px;
    white-space:nowrap;
}
#scanner-reader {
    width:100%;
    min-height:300px;
    overflow:hidden;
    background:#020617;
    border:1px solid #29425e;
    border-radius:16px;
}
#scanner-reader video {
    width:100% !important;
    height:auto !important;
    max-height:560px !important;
    object-fit:cover !important;
    border-radius:15px !important;
}
#scanner-reader__scan_region {
    border:0 !important;
}
#scanner-reader__dashboard,
#scanner-reader__header_message {
    display:none !important;
}
.scanner-actions {
    display:grid;
    grid-template-columns:1.25fr 1fr 1fr;
    gap:8px;
    margin-top:10px;
}
.scanner-actions button {
    min-height:45px;
    border-radius:11px;
    border:1px solid #29425e;
    background:#0b1a2b;
    color:#e5e7eb;
    font-weight:800;
    cursor:pointer;
}
.scanner-actions button:disabled { opacity:.45; cursor:not-allowed; }
.scanner-primary {
    background:linear-gradient(135deg,#22c55e,#15803d) !important;
    color:#fff !important;
    border:0 !important;
}
.scanner-instructions {
    margin-top:10px;
    padding:11px 13px;
    border:1px solid #1c344c;
    background:#081525;
    border-radius:12px;
    color:#94a3b8;
    font-size:12px;
    line-height:1.8;
    text-align:center;
}
.scanner-result {
    display:none;
    margin-top:11px;
    padding:14px;
    border-radius:13px;
    background:rgba(34,197,94,.08);
    border:1px solid rgba(34,197,94,.30);
    text-align:center;
}
.scanner-result.visible { display:block; }
.scanner-result-label { color:#86efac; font-size:12px; }
#scanner-value {
    margin-top:4px;
    color:#fff;
    font-size:25px;
    font-weight:900;
    direction:ltr;
    word-break:break-all;
}
.scanner-error {
    display:none;
    margin-top:10px;
    padding:11px;
    border-radius:11px;
    background:rgba(239,68,68,.08);
    border:1px solid rgba(239,68,68,.30);
    color:#fecaca;
    font-size:12px;
    line-height:1.8;
}
.scanner-error.visible { display:block; }
@media (max-width:650px) {
    .scanner-actions { grid-template-columns:1fr 1fr; }
    .scanner-primary { grid-column:1 / -1; }
}
"""

SCANNER_JS = r"""
export default function(component) {
    const { parentElement, setTriggerValue } = component;

    const reader = parentElement.querySelector("#scanner-reader");
    const startButton = parentElement.querySelector("#scanner-start");
    const stopButton = parentElement.querySelector("#scanner-stop");
    const fileButton = parentElement.querySelector("#scanner-file");
    const fileInput = parentElement.querySelector("#scanner-file-input");
    const status = parentElement.querySelector("#scanner-status");
    const resultBox = parentElement.querySelector("#scanner-result");
    const resultValue = parentElement.querySelector("#scanner-value");
    const errorBox = parentElement.querySelector("#scanner-error");

    let scanner = null;
    let running = false;
    let reported = false;

    const setStatus = value => { status.textContent = value; };

    function showError(value) {
        errorBox.textContent = value;
        errorBox.classList.add("visible");
        setStatus("تعذر التشغيل");
    }

    function clearError() {
        errorBox.textContent = "";
        errorBox.classList.remove("visible");
    }

    function clean(value) {
        return String(value || "").trim().replace(/\s+/g, "");
    }

    function valid(value) {
        if (!value) return false;
        if (/^\d+$/.test(value)) {
            return [8, 12, 13, 14].includes(value.length);
        }
        return value.length >= 4;
    }

    async function loadLibrary() {
        if (window.Html5Qrcode && window.Html5QrcodeSupportedFormats) {
            return;
        }

        const sources = [
            "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js",
            "https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js"
        ];

        for (const src of sources) {
            try {
                await new Promise((resolve, reject) => {
                    const old = document.querySelector(
                        'script[data-holland-scanner="1"]'
                    );

                    if (old) {
                        old.remove();
                    }

                    const script = document.createElement("script");
                    script.src = src;
                    script.async = true;
                    script.dataset.hollandScanner = "1";

                    script.onload = () => {
                        if (
                            window.Html5Qrcode &&
                            window.Html5QrcodeSupportedFormats
                        ) {
                            resolve();
                        } else {
                            reject(new Error("library api missing"));
                        }
                    };

                    script.onerror = () => reject(new Error("cdn failed"));
                    document.head.appendChild(script);
                });

                return;
            } catch (e) {}
        }

        throw new Error("barcode library unavailable");
    }

    function formats() {
        const F = window.Html5QrcodeSupportedFormats;

        return [
            F.EAN_13,
            F.EAN_8,
            F.UPC_A,
            F.UPC_E,
            F.CODE_128,
            F.CODE_39,
            F.CODE_93,
            F.ITF,
            F.CODABAR
        ].filter(v => v !== undefined && v !== null);
    }

    async function stop() {
        if (!scanner || !running) {
            startButton.disabled = false;
            stopButton.disabled = true;
            return;
        }

        try {
            await scanner.stop();
        } catch (e) {}

        try {
            scanner.clear();
        } catch (e) {}

        running = false;
        startButton.disabled = false;
        stopButton.disabled = true;
        setStatus("جاهز");
    }

    async function success(decodedText) {
        if (reported) return;

        const value = clean(decodedText);
        if (!valid(value)) return;

        reported = true;
        resultValue.textContent = value;
        resultBox.classList.add("visible");
        setStatus("تمت القراءة");

        await stop();

        setTriggerValue("barcode", value);
    }

    async function start() {
        if (running) return;

        clearError();
        resultBox.classList.remove("visible");
        resultValue.textContent = "";
        reported = false;

        try {
            setStatus("تحميل محرك القراءة...");
            await loadLibrary();

            // IMPORTANT CHANGE:
            // Do NOT call getCameras()/enumerateDevices().
            // Request the environment camera directly.
            // This avoids camera-enumeration failures on some
            // browsers/hosted Streamlit deployments.
            scanner = new window.Html5Qrcode(
                reader.id,
                {
                    formatsToSupport: formats(),
                    useBarCodeDetectorIfSupported: true,
                    verbose: false
                }
            );

            setStatus("طلب تشغيل الكاميرا...");

            const config = {
                fps: 15,
                aspectRatio: 1.7777778,
                qrbox: function(width, height) {
                    return {
                        width: Math.floor(width * 0.90),
                        height: Math.max(
                            120,
                            Math.min(
                                Math.floor(height * 0.32),
                                240
                            )
                        )
                    };
                },
                disableFlip: true
            };

            await scanner.start(
                { facingMode: { ideal: "environment" } },
                config,
                success,
                function() {}
            );

            running = true;
            startButton.disabled = true;
            stopButton.disabled = false;
            setStatus("وجّه الباركود إلى الإطار");

            // Try continuous autofocus / modest zoom when supported.
            setTimeout(async () => {
                try {
                    const caps =
                        scanner.getRunningTrackCapabilities();

                    const advanced = {};

                    if (
                        caps &&
                        caps.focusMode &&
                        caps.focusMode.includes("continuous")
                    ) {
                        advanced.focusMode = "continuous";
                    }

                    if (
                        caps &&
                        caps.zoom &&
                        caps.zoom.max > caps.zoom.min
                    ) {
                        advanced.zoom =
                            caps.zoom.min +
                            (caps.zoom.max - caps.zoom.min) * 0.20;
                    }

                    if (Object.keys(advanced).length) {
                        await scanner.applyVideoConstraints({
                            advanced: [advanced]
                        });
                    }
                } catch (e) {}
            }, 900);

        } catch (error) {
            console.error("Holland Bazar camera error:", error);

            await stop();

            const msg = String(error || "").toLowerCase();

            if (
                msg.includes("notallowed") ||
                msg.includes("permission") ||
                msg.includes("denied")
            ) {
                showError(
                    "المتصفح رفض الوصول إلى الكاميرا. رغم إعطاء الصلاحية، أعد تحميل الصفحة ثم اضغط تشغيل الكاميرا مرة أخرى."
                );
            } else if (
                msg.includes("notfound") ||
                msg.includes("no camera")
            ) {
                showError(
                    "لم يتم العثور على كاميرا. جرّب فتح الموقع من Chrome وتأكد أن الكاميرا تعمل."
                );
            } else if (
                msg.includes("notreadable") ||
                msg.includes("trackstart")
            ) {
                showError(
                    "الكاميرا مستخدمة من برنامج آخر. أغلق Camera/Teams/Zoom وأعد المحاولة."
                );
            } else if (
                msg.includes("library")
            ) {
                showError(
                    "لم يتم تحميل محرك الباركود. أعد تحميل الصفحة وتأكد من اتصال الإنترنت."
                );
            } else {
                showError(
                    "فشل تشغيل الكاميرا. افتح أدوات المطور في Chrome لرؤية الخطأ التفصيلي."
                );
            }
        }
    }

    async function scanFile(file) {
        if (!file) return;

        clearError();
        reported = false;

        try {
            setStatus("تحليل الصورة...");
            await loadLibrary();

            if (!scanner) {
                scanner = new window.Html5Qrcode(
                    reader.id,
                    {
                        formatsToSupport: formats(),
                        useBarCodeDetectorIfSupported: true,
                        verbose: false
                    }
                );
            }

            const value = await scanner.scanFile(file, false);

            await success(value);

        } catch (error) {
            console.error("Holland Bazar image scan:", error);
            showError(
                "لم يتم العثور على باركود واضح في الصورة. قرّب الملصق وصوّره بشكل مستقيم."
            );
        }
    }

    startButton.addEventListener("click", start);
    stopButton.addEventListener("click", stop);

    fileButton.addEventListener(
        "click",
        () => fileInput.click()
    );

    fileInput.addEventListener(
        "change",
        event => {
            const file =
                event.target.files &&
                event.target.files[0];

            if (file) scanFile(file);
            fileInput.value = "";
        }
    );

    // Preload the library without requesting camera permission.
    loadLibrary()
        .then(() => setStatus("جاهز"))
        .catch(() => setStatus("جاهز"));

    return () => {
        try {
            if (scanner && running) {
                scanner.stop().catch(() => {});
            }
        } catch (e) {}
    };
}
"""

barcode_component = components.component(
    "holland_bazar_barcode_scanner_v3",
    html=SCANNER_HTML,
    css=SCANNER_CSS,
    js=SCANNER_JS,
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

    with st.container(border=True):

        st.subheader("📷 قارئ الباركود")
        st.caption(
            "القارئ يعمل داخل المتصفح مباشرة. "
            "اضغط تشغيل الكاميرا ثم وجّه الكاميرا إلى الباركود."
        )

        result = barcode_component(
            key="warehouse_scanner_v3",
            on_barcode_change=lambda: None,
        )

        scanned = None

        try:
            scanned = result.barcode
        except Exception:
            scanned = None

        if scanned:
            st.success(
                f"تمت قراءة الباركود: {scanned}"
            )

            perform_search(
                scanned
            )

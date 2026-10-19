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
# APP CONFIG
# ============================================================

st.set_page_config(
    page_title="Holland Bazar T&D",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

EXCEL_PATH = "DATABASE.xlsx"

# Keep your existing public MEGA folder here.
MEGA_FOLDER_URL = (
    "https://mega.nz/folder/HrximbwC"
    "#9wvR9D8OQnrAJlTItE6Oag"
)

MEGA_API = "https://g.api.mega.co.nz/cs"


# ============================================================
# PROFESSIONAL UI
# ============================================================

st.markdown(
    """
<style>
:root {
    --bg: #07111f;
    --panel: #0d1b2a;
    --panel-2: #102238;
    --border: #20344d;
    --border-soft: #1a3048;
    --text: #f8fafc;
    --muted: #94a3b8;
    --green: #22c55e;
    --green-dark: #15803d;
    --green-soft: rgba(34,197,94,.10);
    --blue: #38bdf8;
}

.stApp {
    direction: rtl;
    background:
        radial-gradient(
            circle at 88% 0%,
            rgba(34,197,94,.10),
            transparent 27%
        ),
        radial-gradient(
            circle at 4% 18%,
            rgba(56,189,248,.07),
            transparent 25%
        ),
        var(--bg);
    color: var(--text);
}

.block-container {
    max-width: 1180px;
    padding: 28px 22px 60px;
}

.hero {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 18px;
    padding: 26px 30px;
    margin-bottom: 18px;
    border: 1px solid var(--border);
    border-radius: 22px;
    background:
        linear-gradient(
            135deg,
            rgba(16,34,56,.98),
            rgba(8,22,37,.98)
        );
    box-shadow: 0 20px 60px rgba(0,0,0,.25);
}

.hero-title {
    margin: 0;
    font-size: clamp(25px, 4vw, 38px);
    font-weight: 850;
    letter-spacing: -.7px;
}

.hero-subtitle {
    margin-top: 7px;
    color: var(--muted);
    font-size: 14px;
}

.hero-status {
    padding: 9px 14px;
    border-radius: 999px;
    border: 1px solid rgba(34,197,94,.35);
    background: var(--green-soft);
    color: #86efac;
    white-space: nowrap;
    font-size: 13px;
}

.section {
    background: rgba(13,27,42,.94);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 21px;
    margin: 15px 0;
    box-shadow: 0 10px 35px rgba(0,0,0,.10);
}

.section-title {
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 4px;
}

.section-subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 17px;
    line-height: 1.7;
}

.search-label {
    color: #cbd5e1;
    font-size: 13px;
    margin-bottom: 7px;
}

div[data-testid="stTextInput"] input {
    direction: ltr !important;
    text-align: left !important;
    background: #081525 !important;
    border: 1px solid #29425e !important;
    color: #fff !important;
    border-radius: 13px !important;
    min-height: 50px;
    font-size: 17px;
}

div[data-testid="stTextInput"] input:focus {
    border-color: #22c55e !important;
    box-shadow: 0 0 0 2px rgba(34,197,94,.12) !important;
}

.product-card {
    background:
        linear-gradient(
            145deg,
            #102238,
            #0a1828
        );
    border: 1px solid #24415e;
    border-radius: 20px;
    padding: 23px;
    margin-top: 18px;
}

.product-name {
    font-size: 25px;
    line-height: 1.4;
    font-weight: 850;
}

.product-found {
    display: inline-block;
    margin-top: 12px;
    padding: 7px 11px;
    border-radius: 9px;
    background: rgba(34,197,94,.10);
    border: 1px solid rgba(34,197,94,.28);
    color: #bbf7d0;
    font-size: 13px;
}

.stat-card {
    background: #081525;
    border: 1px solid #1e3851;
    border-radius: 15px;
    padding: 16px 13px;
    text-align: center;
    min-height: 90px;
}

.stat-value {
    color: #fff;
    font-size: 20px;
    font-weight: 850;
    overflow-wrap: anywhere;
}

.stat-label {
    color: var(--muted);
    font-size: 12px;
    margin-top: 7px;
}

.tip {
    background: #081525;
    border: 1px solid #1c344c;
    border-radius: 14px;
    padding: 14px 16px;
    color: #cbd5e1;
    font-size: 13px;
    line-height: 1.9;
}

div[data-testid="stTabs"] button {
    font-weight: 750;
}

button[kind="primary"] {
    background: linear-gradient(
        135deg,
        #22c55e,
        #15803d
    ) !important;
    border: none !important;
}

@media (max-width: 700px) {
    .block-container {
        padding: 16px 11px 45px;
    }

    .hero {
        padding: 20px;
        border-radius: 18px;
    }

    .hero-status {
        display: none;
    }

    .section {
        padding: 15px;
        border-radius: 16px;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# BROWSER BARCODE SCANNER - STREAMLIT V2 COMPONENT
#
# This is deliberately browser-side.
# The camera stream does NOT travel through Python.
# html5-qrcode 2.3.8:
#   - camera scanning
#   - BarcodeDetector when supported
#   - ZXing fallback
#   - image-file scanning
#   - camera selection
#   - torch/zoom where supported
# ============================================================

SCANNER_HTML = """
<div id="hb-root">
    <div class="hb-head">
        <div>
            <div class="hb-title">📷 ماسح الباركود</div>
            <div class="hb-subtitle">
                قراءة مباشرة من كاميرا الجهاز
            </div>
        </div>
        <div id="hb-status" class="hb-status">
            جاهز
        </div>
    </div>

    <div id="hb-reader"></div>

    <div class="hb-controls">
        <button id="hb-start" class="hb-primary">
            تشغيل الكاميرا
        </button>

        <button id="hb-stop" class="hb-secondary" disabled>
            إيقاف
        </button>

        <button id="hb-file" class="hb-secondary">
            📁 قراءة صورة
        </button>

        <input
            id="hb-file-input"
            type="file"
            accept="image/*"
            hidden
        />
    </div>

    <div class="hb-help">
        <b>أفضل نتيجة:</b>
        استخدم الكاميرا الخلفية، اقترب من الملصق،
        واجعل الخطوط داخل الإطار الأخضر واضحة.
    </div>

    <div id="hb-result" class="hb-result">
        <div class="hb-result-label">
            تم التعرف على الباركود
        </div>
        <div id="hb-result-value" class="hb-result-value"></div>
    </div>

    <div id="hb-error" class="hb-error"></div>
</div>
"""

SCANNER_CSS = """
#hb-root {
    direction: rtl;
    color: #e5e7eb;
    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

.hb-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}

.hb-title {
    font-size: 19px;
    font-weight: 850;
}

.hb-subtitle {
    color: #94a3b8;
    font-size: 12px;
    margin-top: 3px;
}

.hb-status {
    color: #94a3b8;
    background: #081525;
    border: 1px solid #20344d;
    border-radius: 999px;
    padding: 7px 11px;
    font-size: 12px;
    white-space: nowrap;
}

#hb-reader {
    width: 100%;
    min-height: 290px;
    overflow: hidden;
    border-radius: 17px;
    background: #020617;
    border: 1px solid #20344d;
}

#hb-reader video {
    width: 100% !important;
    border-radius: 16px !important;
    object-fit: cover !important;
}

#hb-reader canvas {
    display: none;
}

.hb-controls {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin-top: 11px;
}

.hb-controls button {
    min-height: 45px;
    border-radius: 11px;
    border: 1px solid #29425e;
    color: #e5e7eb;
    background: #0b1a2b;
    font-weight: 750;
    cursor: pointer;
}

.hb-controls button:disabled {
    opacity: .45;
    cursor: not-allowed;
}

.hb-primary {
    background: linear-gradient(
        135deg,
        #22c55e,
        #15803d
    ) !important;
    border: none !important;
    color: white !important;
}

.hb-help {
    margin-top: 11px;
    padding: 12px 14px;
    border-radius: 12px;
    background: #081525;
    border: 1px solid #1c344c;
    color: #94a3b8;
    font-size: 12px;
    line-height: 1.8;
    text-align: center;
}

.hb-result {
    display: none;
    margin-top: 12px;
    padding: 14px;
    border-radius: 13px;
    background: rgba(34,197,94,.09);
    border: 1px solid rgba(34,197,94,.35);
    text-align: center;
}

.hb-result.show {
    display: block;
}

.hb-result-label {
    color: #86efac;
    font-size: 12px;
}

.hb-result-value {
    color: #fff;
    font-size: 27px;
    font-weight: 900;
    letter-spacing: 1px;
    margin-top: 4px;
    direction: ltr;
    word-break: break-all;
}

.hb-error {
    display: none;
    margin-top: 11px;
    padding: 11px;
    border-radius: 12px;
    color: #fecaca;
    background: rgba(239,68,68,.08);
    border: 1px solid rgba(239,68,68,.25);
    font-size: 12px;
    line-height: 1.7;
}

.hb-error.show {
    display: block;
}

@media (max-width: 600px) {
    .hb-controls {
        grid-template-columns: 1fr 1fr;
    }

    .hb-controls button:last-of-type {
        grid-column: 1 / -1;
    }
}
"""

SCANNER_JS = r"""
export default function(component) {
    const { setTriggerValue, parentElement } = component;

    const root = parentElement.querySelector("#hb-root");
    if (!root) return;

    const reader = parentElement.querySelector("#hb-reader");
    const startBtn = parentElement.querySelector("#hb-start");
    const stopBtn = parentElement.querySelector("#hb-stop");
    const fileBtn = parentElement.querySelector("#hb-file");
    const fileInput = parentElement.querySelector("#hb-file-input");
    const status = parentElement.querySelector("#hb-status");
    const resultBox = parentElement.querySelector("#hb-result");
    const resultValue = parentElement.querySelector("#hb-result-value");
    const errorBox = parentElement.querySelector("#hb-error");

    let scanner = null;
    let scanning = false;
    let reported = false;
    let cameras = [];
    let activeCameraId = null;

    const formats = [
        Html5QrcodeSupportedFormats.EAN_13,
        Html5QrcodeSupportedFormats.EAN_8,
        Html5QrcodeSupportedFormats.UPC_A,
        Html5QrcodeSupportedFormats.UPC_E,
        Html5QrcodeSupportedFormats.CODE_128,
        Html5QrcodeSupportedFormats.CODE_39,
        Html5QrcodeSupportedFormats.CODE_93,
        Html5QrcodeSupportedFormats.ITF,
        Html5QrcodeSupportedFormats.CODABAR
    ];

    function setStatus(text) {
        status.textContent = text;
    }

    function clearError() {
        errorBox.textContent = "";
        errorBox.classList.remove("show");
    }

    function showError(text) {
        errorBox.textContent = text;
        errorBox.classList.add("show");
        setStatus("خطأ");
    }

    function clean(value) {
        return String(value || "")
            .trim()
            .replace(/\s+/g, "");
    }

    function isPlausible(value) {
        if (!value) return false;

        // Retail EAN / UPC.
        if (/^\d+$/.test(value)) {
            return [8, 12, 13, 14].includes(value.length);
        }

        // Warehouse / Code128 / Code39.
        return value.length >= 4;
    }

    async function loadLibrary() {
        if (window.Html5Qrcode) {
            return;
        }

        await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src =
                "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async function ensureScanner() {
        if (!scanner) {
            scanner = new Html5Qrcode(
                reader.id,
                {
                    formatsToSupport: formats,
                    useBarCodeDetectorIfSupported: true,
                    verbose: false
                }
            );
        }
        return scanner;
    }

    function qrBox(width, height) {
        const boxWidth = Math.floor(width * 0.90);
        const boxHeight = Math.max(
            115,
            Math.min(
                Math.floor(height * 0.32),
                255
            )
        );

        return {
            width: boxWidth,
            height: boxHeight
        };
    }

    async function chooseBestCamera() {
        cameras = await Html5Qrcode.getCameras();

        if (!cameras || cameras.length === 0) {
            throw new Error("لم يتم العثور على كاميرا.");
        }

        const backWords = [
            "back",
            "rear",
            "environment",
            "خلف",
            "خلفية"
        ];

        let best = cameras.find(camera => {
            const label =
                (camera.label || "").toLowerCase();

            return backWords.some(word =>
                label.includes(word)
            );
        });

        return best || cameras[cameras.length - 1];
    }

    async function applyCameraEnhancements() {
        try {
            if (!scanner || !scanning) return;

            const capabilities =
                scanner.getRunningTrackCapabilities();

            const constraints = {};

            if (
                capabilities &&
                capabilities.focusMode &&
                capabilities.focusMode.includes("continuous")
            ) {
                constraints.focusMode = "continuous";
            }

            if (
                capabilities &&
                capabilities.zoom
            ) {
                const min =
                    capabilities.zoom.min ?? 1;
                const max =
                    capabilities.zoom.max ?? 1;

                if (max > min) {
                    constraints.zoom =
                        Math.min(
                            max,
                            Math.max(
                                min,
                                min + (max - min) * 0.30
                            )
                        );
                }
            }

            if (Object.keys(constraints).length) {
                await scanner.applyVideoConstraints(
                    { advanced: [constraints] }
                );
            }
        } catch (e) {
            // Camera-specific controls are optional.
        }
    }

    async function stopScanner() {
        if (!scanner || !scanning) {
            return;
        }

        try {
            await scanner.stop();
        } catch (e) {
            // Already stopped.
        }

        scanning = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        setStatus("جاهز");
    }

    async function onSuccess(decodedText) {
        if (reported) return;

        const value = clean(decodedText);

        if (!isPlausible(value)) {
            return;
        }

        reported = true;

        resultValue.textContent = value;
        resultBox.classList.add("show");

        setStatus("تمت القراءة");

        await stopScanner();

        // Trigger exactly one Streamlit rerun.
        setTriggerValue("barcode", value);
    }

    async function startScanner() {
        clearError();

        if (scanning) return;

        reported = false;
        resultBox.classList.remove("show");
        resultValue.textContent = "";

        try {
            setStatus("تحميل محرك القراءة…");

            await loadLibrary();

            const qr = await ensureScanner();

            const camera = await chooseBestCamera();

            activeCameraId = camera.id;

            setStatus("تشغيل الكاميرا…");

            await qr.start(
                activeCameraId,
                {
                    fps: 12,
                    aspectRatio: 16 / 9,
                    qrbox: qrBox,
                    disableFlip: true
                },
                onSuccess,
                function() {
                    // A failed frame is normal. Do not show errors.
                }
            );

            scanning = true;

            startBtn.disabled = true;
            stopBtn.disabled = false;

            setStatus("وجّه الباركود إلى الإطار");

            setTimeout(
                applyCameraEnhancements,
                800
            );

        } catch (error) {
            console.error(error);

            scanning = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;

            const message =
                String(error || "");

            if (
                message
                    .toLowerCase()
                    .includes("permission")
            ) {
                showError(
                    "صلاحية الكاميرا مرفوضة. اسمح للموقع باستخدام الكاميرا ثم اضغط تشغيل الكاميرا مرة أخرى."
                );
            } else if (
                message
                    .toLowerCase()
                    .includes("secure")
            ) {
                showError(
                    "الكاميرا تحتاج إلى HTTPS."
                );
            } else {
                showError(
                    "تعذر تشغيل الكاميرا. تأكد من وجود كاميرا ومنح المتصفح صلاحية استخدامها."
                );
            }
        }
    }

    async function scanFile(file) {
        if (!file) return;

        clearError();
        reported = false;

        try {
            await loadLibrary();

            const qr = await ensureScanner();

            setStatus("تحليل الصورة…");

            const value =
                await qr.scanFile(file, false);

            await onSuccess(value);

        } catch (error) {
            console.error(error);

            showError(
                "لم يتم العثور على باركود واضح في الصورة. صوّر الباركود من مسافة قريبة وبإضاءة جيدة."
            );
        }
    }

    startBtn.onclick = startScanner;
    stopBtn.onclick = stopScanner;

    fileBtn.onclick = function() {
        fileInput.click();
    };

    fileInput.onchange = function(event) {
        const file =
            event.target.files &&
            event.target.files[0];

        if (file) {
            scanFile(file);
        }

        fileInput.value = "";
    };

    // Load the library before the user presses the button,
    // but do NOT request camera permission automatically.
    loadLibrary()
        .then(() => setStatus("جاهز"))
        .catch(() =>
            showError(
                "تعذر تحميل محرك قراءة الباركود. تحقق من اتصال الإنترنت."
            )
        );

    // Component cleanup.
    return () => {
        try {
            if (scanner && scanning) {
                scanner.stop().catch(() => {});
            }
        } catch (e) {}
    };
}
"""

# ============================================================
# REGISTER COMPONENT V2
# ============================================================

barcode_component = components.component(
    "holland_bazar_barcode_scanner",
    html=SCANNER_HTML,
    css=SCANNER_CSS,
    js=SCANNER_JS,
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
    st.error("ملف DATABASE.xlsx غير موجود.")
    st.stop()

if df.empty:
    st.error("ملف DATABASE.xlsx فارغ.")
    st.stop()


# ============================================================
# MEGA IMAGE SUPPORT
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


def decrypt_key(
    encrypted_key,
    key,
):
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


def decrypt_attributes(
    encrypted_attributes,
    key,
):
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
        raise ValueError(
            "Invalid MEGA folder URL"
        )

    return (
        match.group(1),
        match.group(2),
    )


def mega_api_request(
    data,
    folder_handle=None,
):
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
        raise RuntimeError(
            "MEGA returned no data."
        )

    if isinstance(result[0], int):
        raise RuntimeError(
            f"MEGA API error: {result[0]}"
        )

    return result[0]


@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def get_mega_nodes():

    folder_handle, folder_key_text = (
        parse_mega_folder_url(
            MEGA_FOLDER_URL
        )
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

    for node in response.get(
        "f",
        [],
    ):

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
                    encrypted_node_key.split(
                        ":",
                        1,
                    )[1]
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

            filename = attributes.get(
                "n",
                "",
            )

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


def find_mega_image(
    nodes,
    code,
    barcode,
):

    identifiers = []

    for value in (
        barcode,
        code,
    ):

        value = str(
            value or ""
        ).strip().lower()

        if (
            value
            and value != "nan"
        ):
            identifiers.append(
                value
            )

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
        if node["name"]
        .lower()
        .endswith(extensions)
    ]

    # Exact match first.
    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if stem == identifier:
                return node

    # Partial match second.
    for identifier in identifiers:

        for node in files:

            stem = os.path.splitext(
                node["name"]
            )[0].lower()

            if identifier in stem:
                return node

    return None


@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def download_mega_image(
    node_handle,
    node_key,
):

    folder_handle, _ = (
        parse_mega_folder_url(
            MEGA_FOLDER_URL
        )
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
# PRODUCT LOOKUP
# ============================================================

def lookup_product(query):

    query = str(query).strip()

    if not query:
        return None

    return df[
        (df["0"] == query)
        |
        (df["1"] == query)
    ]


def render_product(query):

    matches = lookup_product(query)

    if matches is None or matches.empty:

        st.error(
            "لم يتم العثور على منتج بهذا الباركود أو الكود."
        )

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
        ]

        if not similar.empty:

            st.markdown(
                """
                <div class="section">
                    <div class="section-title">
                        نتائج مشابهة
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for _, row in (
                similar.head(5).iterrows()
            ):

                with st.container(
                    border=True
                ):

                    st.write(
                        f"**{row['2']}**"
                    )

                    st.caption(
                        f"الكود: {row['0']}  •  "
                        f"الباركود: {row['1']}"
                    )

        return

    row = matches.iloc[0]

    code = str(
        row["0"]
    ).strip()

    barcode = str(
        row["1"]
    ).strip()

    description = str(
        row["2"]
    ).strip()

    quantity = str(
        row["3"]
    ).strip()

    if (
        not barcode
        or barcode.lower() == "nan"
    ):
        barcode = "غير متوفر"

    if (
        not description
        or description.lower() == "nan"
    ):
        description = "غير متوفر"

    if (
        not quantity
        or quantity.lower() == "nan"
    ):
        quantity = "0"

    st.markdown(
        f"""
        <div class="product-card">

            <div class="product-name">
                {description}
            </div>

            <div class="product-found">
                ✓ تم العثور على المنتج
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-value">
                    {code}
                </div>
                <div class="stat-label">
                    كود المنتج
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-value">
                    {barcode}
                </div>
                <div class="stat-label">
                    الباركود
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-value">
                    {quantity}
                </div>
                <div class="stat-label">
                    الكمية الحالية
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="section">
            <div class="section-title">
                🖼️ صورة المنتج
            </div>
            <div class="section-subtitle">
                الصورة المرتبطة بكود المنتج أو الباركود.
            </div>
        """,
        unsafe_allow_html=True,
    )

    try:

        with st.spinner(
            "جاري تحميل صورة المنتج..."
        ):

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

            image_bytes = (
                download_mega_image(
                    image_node["handle"],
                    image_node["key"],
                )
            )

            image = Image.open(
                BytesIO(image_bytes)
            )

            st.image(
                image,
                width="stretch",
            )

    except Exception as e:

        st.warning(
            f"تعذر تحميل صورة المنتج: {e}"
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">

        <div>
            <div class="hero-title">
                Holland Bazar T&D 📦
            </div>

            <div class="hero-subtitle">
                نظام البحث عن المنتجات والمخزون
            </div>
        </div>

        <div class="hero-status">
            ● النظام جاهز
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# NAVIGATION
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

    st.markdown(
        """
        <div class="section">

            <div class="section-title">
                البحث عن منتج
            </div>

            <div class="section-subtitle">
                أدخل الباركود أو كود المنتج للوصول
                إلى بيانات المخزون والصورة.
            </div>

        """,
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "الباركود أو كود المنتج",
        placeholder="مثال: 6820468232713",
        label_visibility="collapsed",
        key="manual_search",
    )

    if query:
        render_product(query)

    else:

        st.markdown(
            """
            <div class="tip">
                💡 اكتب الباركود أو الكود يدوياً،
                أو استخدم تبويب <b>مسح الباركود</b>
                مع كاميرا الهاتف.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# SCANNER
# ============================================================

with scanner_tab:

    st.markdown(
        """
        <div class="section">

            <div class="section-title">
                ماسح الباركود
            </div>

            <div class="section-subtitle">
                الماسح يعمل داخل متصفح الجهاز مباشرة.
                لا يتم إرسال فيديو الكاميرا إلى Python.
            </div>

        """,
        unsafe_allow_html=True,
    )

    scan_result = barcode_component(
        key="warehouse_barcode_scanner",
        default={"barcode": None},
        on_barcode_change=lambda: None,
    )

    barcode = None

    if scan_result:

        try:
            barcode = scan_result.barcode
        except Exception:
            barcode = None

    if barcode:

        st.markdown(
            f"""
            <div class="product-found">
                ✓ تمت قراءة الباركود:
                <b dir="ltr">{barcode}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_product(
            barcode
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

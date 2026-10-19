
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
                وجّه الكاميرا إلى الباركود
            </div>
        </div>
        <div id="scanner-status" class="scanner-status">
            جاهز
        </div>
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

        <input
            id="scanner-file-input"
            type="file"
            accept="image/*"
            hidden
        />
    </div>

    <div class="scanner-instructions">
        <b>نصيحة:</b>
        استخدم الكاميرا الخلفية، قرّب الهاتف من الباركود،
        وتأكد أن جميع الخطوط ظاهرة بوضوح.
    </div>

    <div id="scanner-result" class="scanner-result">
        <div class="scanner-result-label">
            الباركود المقروء
        </div>
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
    font-family:
        Inter,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    color: var(--st-text-color, #f8fafc);
}

.scanner-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
    margin-bottom: 12px;
}

.scanner-title {
    font-size: 19px;
    font-weight: 850;
}

.scanner-caption {
    color: var(--st-secondary-text-color, #94a3b8);
    font-size: 12px;
    margin-top: 3px;
}

.scanner-status {
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(34,197,94,.08);
    border: 1px solid rgba(34,197,94,.25);
    color: #86efac;
    font-size: 12px;
    white-space: nowrap;
}

#scanner-reader {
    width: 100%;
    min-height: 285px;
    overflow: hidden;
    border-radius: 16px;
    background: #020617;
    border: 1px solid #20344d;
}

#scanner-reader video {
    width: 100% !important;
    max-height: 520px !important;
    object-fit: cover !important;
    border-radius: 15px !important;
}

#scanner-reader img {
    max-width: 100%;
}

.scanner-actions {
    display: grid;
    grid-template-columns: 1.2fr 1fr 1fr;
    gap: 8px;
    margin-top: 10px;
}

.scanner-actions button {
    min-height: 44px;
    border-radius: 11px;
    border: 1px solid #29425e;
    background: #0b1a2b;
    color: #e5e7eb;
    font-weight: 750;
    cursor: pointer;
}

.scanner-actions button:disabled {
    opacity: .45;
    cursor: not-allowed;
}

.scanner-primary {
    background: linear-gradient(
        135deg,
        #22c55e,
        #15803d
    ) !important;
    color: white !important;
    border: none !important;
}

.scanner-instructions {
    margin-top: 10px;
    padding: 12px 14px;
    border-radius: 12px;
    background: #081525;
    border: 1px solid #1c344c;
    color: #94a3b8;
    font-size: 12px;
    line-height: 1.8;
    text-align: center;
}

.scanner-result {
    display: none;
    margin-top: 11px;
    padding: 14px;
    border-radius: 13px;
    background: rgba(34,197,94,.08);
    border: 1px solid rgba(34,197,94,.30);
    text-align: center;
}

.scanner-result.visible {
    display: block;
}

.scanner-result-label {
    color: #86efac;
    font-size: 12px;
}

#scanner-value {
    margin-top: 4px;
    color: white;
    font-size: 25px;
    font-weight: 900;
    direction: ltr;
    word-break: break-all;
}

.scanner-error {
    display: none;
    margin-top: 10px;
    padding: 11px;
    border-radius: 11px;
    background: rgba(239,68,68,.08);
    border: 1px solid rgba(239,68,68,.25);
    color: #fecaca;
    font-size: 12px;
    line-height: 1.7;
}

.scanner-error.visible {
    display: block;
}

@media (max-width: 650px) {
    .scanner-actions {
        grid-template-columns: 1fr 1fr;
    }

    .scanner-primary {
        grid-column: 1 / -1;
    }
}
"""

SCANNER_JS = r"""
export default function(component) {
    const {
        parentElement,
        setTriggerValue,
    } = component;

    const root =
        parentElement.querySelector(".scanner-shell");

    if (!root) {
        return;
    }

    const reader =
        parentElement.querySelector("#scanner-reader");

    const startButton =
        parentElement.querySelector("#scanner-start");

    const stopButton =
        parentElement.querySelector("#scanner-stop");

    const fileButton =
        parentElement.querySelector("#scanner-file");

    const fileInput =
        parentElement.querySelector("#scanner-file-input");

    const status =
        parentElement.querySelector("#scanner-status");

    const resultBox =
        parentElement.querySelector("#scanner-result");

    const resultValue =
        parentElement.querySelector("#scanner-value");

    const errorBox =
        parentElement.querySelector("#scanner-error");

    let scanner = null;
    let running = false;
    let reported = false;

    function setStatus(value) {
        status.textContent = value;
    }

    function clearError() {
        errorBox.textContent = "";
        errorBox.classList.remove("visible");
    }

    function showError(value) {
        errorBox.textContent = value;
        errorBox.classList.add("visible");
        setStatus("تعذر التشغيل");
    }

    function cleanValue(value) {
        return String(value || "")
            .trim()
            .replace(/\s+/g, "");
    }

    function plausibleBarcode(value) {
        if (!value) {
            return false;
        }

        if (/^\d+$/.test(value)) {
            return (
                value.length === 8 ||
                value.length === 12 ||
                value.length === 13 ||
                value.length === 14
            );
        }

        return value.length >= 4;
    }

    function loadHtml5QrCode() {
        if (
            window.Html5Qrcode &&
            window.Html5QrcodeSupportedFormats
        ) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            const existing =
                document.querySelector(
                    'script[data-holland-h5qr="1"]'
                );

            if (existing) {
                const timer = setInterval(() => {
                    if (
                        window.Html5Qrcode &&
                        window.Html5QrcodeSupportedFormats
                    ) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 50);

                setTimeout(() => {
                    clearInterval(timer);

                    if (
                        window.Html5Qrcode &&
                        window.Html5QrcodeSupportedFormats
                    ) {
                        resolve();
                    } else {
                        reject(
                            new Error(
                                "Barcode library timeout"
                            )
                        );
                    }
                }, 15000);

                return;
            }

            const script =
                document.createElement("script");

            script.src =
                "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js";

            script.async = true;

            script.dataset.hollandH5qr = "1";

            script.onload = () => {
                if (
                    window.Html5Qrcode &&
                    window.Html5QrcodeSupportedFormats
                ) {
                    resolve();
                } else {
                    reject(
                        new Error(
                            "Barcode library loaded without API"
                        )
                    );
                }
            };

            script.onerror = () => {
                reject(
                    new Error(
                        "Could not load barcode library"
                    )
                );
            };

            document.head.appendChild(script);
        });
    }

    function supportedFormats() {
        const F =
            window.Html5QrcodeSupportedFormats;

        // IMPORTANT:
        // Read this ONLY after loadHtml5QrCode() completes.
        return [
            F.EAN_13,
            F.EAN_8,
            F.UPC_A,
            F.UPC_E,
            F.CODE_128,
            F.CODE_39,
            F.CODE_93,
            F.ITF,
            F.CODABAR,
        ].filter(
            value =>
                value !== undefined &&
                value !== null
        );
    }

    function scanBox(width, height) {
        const boxWidth =
            Math.floor(width * 0.90);

        const boxHeight =
            Math.max(
                110,
                Math.min(
                    Math.floor(height * 0.28),
                    220
                )
            );

        return {
            width: boxWidth,
            height: boxHeight,
        };
    }

    async function stop() {
        if (!scanner || !running) {
            return;
        }

        try {
            await scanner.stop();
        } catch (e) {
            // Already stopped.
        }

        running = false;
        startButton.disabled = false;
        stopButton.disabled = true;
        setStatus("جاهز");
    }

    async function success(decodedText) {
        if (reported) {
            return;
        }

        const value =
            cleanValue(decodedText);

        if (!plausibleBarcode(value)) {
            return;
        }

        reported = true;

        resultValue.textContent = value;
        resultBox.classList.add("visible");

        setStatus("تمت القراءة");

        await stop();

        // One event -> one Streamlit rerun.
        setTriggerValue(
            "barcode",
            value
        );
    }

    async function start() {
        if (running) {
            return;
        }

        clearError();

        resultBox.classList.remove(
            "visible"
        );

        resultValue.textContent = "";

        reported = false;

        try {
            setStatus(
                "جاري تحميل القارئ..."
            );

            // FIX FOR THE PREVIOUS ERROR:
            // We wait for the script BEFORE accessing
            // Html5QrcodeSupportedFormats.
            await loadHtml5QrCode();

            const formats =
                supportedFormats();

            scanner =
                new window.Html5Qrcode(
                    reader.id,
                    {
                        formatsToSupport:
                            formats,
                        useBarCodeDetectorIfSupported:
                            true,
                        verbose: false,
                    }
                );

            setStatus(
                "جاري العثور على الكاميرا..."
            );

            const cameras =
                await window.Html5Qrcode.getCameras();

            if (
                !cameras ||
                cameras.length === 0
            ) {
                throw new Error(
                    "No camera found"
                );
            }

            // Prefer rear/environment camera.
            const preferred =
                cameras.find(
                    camera => {
                        const label =
                            (
                                camera.label ||
                                ""
                            ).toLowerCase();

                        return (
                            label.includes("back") ||
                            label.includes("rear") ||
                            label.includes("environment") ||
                            label.includes("خلف")
                        );
                    }
                ) ||
                cameras[cameras.length - 1];

            setStatus(
                "وجّه الباركود إلى الإطار"
            );

            await scanner.start(
                preferred.id,
                {
                    fps: 12,
                    aspectRatio: 1.7777778,
                    qrbox: scanBox,
                    disableFlip: true,
                },
                success,
                function() {
                    // Normal frame misses are ignored.
                }
            );

            running = true;

            startButton.disabled = true;
            stopButton.disabled = false;

            setStatus(
                "امسح الباركود الآن"
            );

            // Give the browser a moment to expose
            // the active camera track.
            setTimeout(
                async () => {
                    try {
                        const capabilities =
                            scanner.getRunningTrackCapabilities();

                        const advanced = {};

                        if (
                            capabilities &&
                            capabilities.focusMode &&
                            capabilities.focusMode.includes(
                                "continuous"
                            )
                        ) {
                            advanced.focusMode =
                                "continuous";
                        }

                        if (
                            capabilities &&
                            capabilities.zoom &&
                            capabilities.zoom.max >
                                capabilities.zoom.min
                        ) {
                            advanced.zoom =
                                Math.min(
                                    capabilities.zoom.max,
                                    Math.max(
                                        capabilities.zoom.min,
                                        capabilities.zoom.min +
                                        (
                                            capabilities.zoom.max -
                                            capabilities.zoom.min
                                        ) * 0.25
                                    )
                                );
                        }

                        if (
                            Object.keys(
                                advanced
                            ).length
                        ) {
                            await scanner.applyVideoConstraints(
                                {
                                    advanced: [
                                        advanced
                                    ]
                                }
                            );
                        }
                    } catch (e) {
                        // Focus/zoom is optional.
                    }
                },
                800
            );

        } catch (error) {
            console.error(
                "Holland Bazar scanner:",
                error
            );

            await stop();

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
                    "الكاميرا تحتاج إلى اتصال HTTPS."
                );
            } else if (
                message
                    .toLowerCase()
                    .includes("no camera")
            ) {
                showError(
                    "لم يتم العثور على كاميرا في هذا الجهاز."
                );
            } else if (
                message
                    .toLowerCase()
                    .includes("barcode library")
            ) {
                showError(
                    "تعذر تحميل محرك قراءة الباركود. تحقق من اتصال الإنترنت ثم أعد تحميل الصفحة."
                );
            } else {
                showError(
                    "تعذر تشغيل قارئ الباركود. افتح صلاحيات الكاميرا في المتصفح ثم جرّب مرة أخرى."
                );
            }
        }
    }

    async function scanFile(file) {
        if (!file) {
            return;
        }

        clearError();

        reported = false;

        try {
            setStatus(
                "تحليل الصورة..."
            );

            await loadHtml5QrCode();

            if (!scanner) {
                scanner =
                    new window.Html5Qrcode(
                        reader.id,
                        {
                            formatsToSupport:
                                supportedFormats(),
                            useBarCodeDetectorIfSupported:
                                true,
                            verbose: false,
                        }
                    );
            }

            const value =
                await scanner.scanFile(
                    file,
                    false
                );

            await success(value);

        } catch (error) {
            console.error(error);

            showError(
                "لم يتم العثور على باركود واضح في الصورة. صوّر الملصق من قريب وبإضاءة جيدة."
            );
        }
    }

    startButton.addEventListener(
        "click",
        start
    );

    stopButton.addEventListener(
        "click",
        stop
    );

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

            if (file) {
                scanFile(file);
            }

            fileInput.value = "";
        }
    );

    // Do not request camera permission automatically.
    loadHtml5QrCode()
        .then(() => {
            setStatus("جاهز");
        })
        .catch(() => {
            // The user can still retry through the button.
            setStatus("جاهز");
        });

    return () => {
        try {
            if (scanner && running) {
                scanner.stop().catch(
                    () => {}
                );
            }
        } catch (e) {}
    };
}
"""

barcode_component = components.component(
    "holland_bazar_barcode_scanner_v2",
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
            key="warehouse_scanner_v2",
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

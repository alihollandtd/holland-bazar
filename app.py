import streamlit as st
import pandas as pd
import os
import re
import requests

# إعدادات واجهة المستخدم وثبات ألوان البطاقات
st.set_page_config(page_title="Holland Bazar T&D", layout="centered", page_icon="📦")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    div.stButton > button:first-child { background-color: #2e7d32; color:white; font-size:18px; width: 100%; }
    
    .metric-box { 
        padding: 20px; 
        background-color: #1e293b; 
        border: 2px solid #334155;
        border-radius: 12px; 
        margin-bottom: 15px; 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    .metric-box h3 { color: #f8fafc !important; font-size: 22px; margin-bottom: 10px; line-height: 1.5; }
    .metric-box p { color: #cbd5e1 !important; font-size: 16px; margin: 5px 0; }
    .metric-box h2 { color: #4ade80 !important; font-size: 26px; margin-top: 15px; line-height: 1.5; }
    .metric-box hr { border-color: #475569; }
    
    .suggestion-box {
        padding: 10px 15px;
        background-color: #334155;
        border-radius: 8px;
        margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# معرف مجلد صور Google Drive العام الخاص بك والمثبت بنجاح
DRIVE_FOLDER_ID = "1l4jD0-Vuh4SLyoid9zugUGBtDsUBu5A7"
EXCEL_PATH = "DATABASE.xlsx"        

@st.cache_data(ttl=10)
def load_data():
    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH, dtype=str)
        df.columns = [str(i) for i in range(len(df.columns))]
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    return None

# دالة سحرية تقوم بفحص كود الـ HTML للمجلد العام واستخراج معرفات الصور (File IDs) تلقائياً للمطابقة
@st.cache_data(ttl=600) # تخزين الروابط مؤقتاً لتسريع الأداء الخارق
def fetch_drive_images(folder_id):
    file_mapping = {}
    try:
        url = f"https://google.com{folder_id}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            # استخدام التعابير النمطية للبحث عن أسماء الملفات ومعرفاتها الفريدة من كود الصفحة الداخلي
            matches = re.findall(r'\["(.*?)"\s*,\s*"(.*?)"\s*,\s*""\s*,\s*"(.*?)"\]', response.text)
            for item in matches:
                file_id = item[0]
                file_name = item[1]
                # تنظيف الاسم من الامتدادات (.png, .jpg) لتسهيل المطابقة بالباركود أو الكود
                clean_name = os.path.splitext(file_name)[0].strip()
                file_mapping[clean_name] = file_id
    except:
        pass
    return file_mapping

df = load_data()
images_db = fetch_drive_images(DRIVE_FOLDER_ID)

st.title("📦 Holland Bazar T&D")

search_query = st.text_input("🔍 أدخل الباركود أو الرمز (كود) للبحث:", key="main_search").strip()

if df is not None and not df.empty:
    col_code = "0"
    col_barcode = "1"
    col_desc = "2"
    col_qty = "3"

    if search_query:
        exact_match = df[(df[col_barcode] == search_query) | (df[col_code] == search_query)]
        
        if not exact_match.empty:
            row = exact_match.iloc[0]
            code = str(row[col_code]).strip()
            barcode = str(row[col_barcode]).strip()
            description = str(row[col_desc]).strip()
            quantity = str(row[col_qty]).strip()
            
            if barcode.lower() == 'nan' or barcode == '': barcode = "غير متوفر"
            if quantity.lower() == 'nan' or quantity == '': quantity = "0"
            
            st.markdown(f"""
            <div class="metric-box">
                <h3>📝 الوصف: {description}</h3>
                <p><b>كود المنتج:</b> {code}</p>
                <p><b>الباركود:</b> {barcode}</p>
                <hr>
                <h2>📊 الكمية في السستم: {quantity}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # محاولة العثور على اسم الصورة في الخريطة الرقمية المجلوبة
            img_id = None
            if barcode != "غير متوفر" and barcode in images_db:
                img_id = images_db[barcode]
            elif code in images_db:
                img_id = images_db[code]
                
            if img_id:
                # توليد الرابط المباشر الخارق والدائم لعرض الصورة الفردية بدقة ممتازة
                final_img_url = f"https://lh3.googleusercontent.com/d/{img_id}"
                st.image(final_img_url, caption=f"الصورة الأصلية للمنتج: {code}", use_container_width=True)
            else:
                # حل بديل مؤقت في حال لم ينتهِ سحب القائمة لضمان استقرار العرض
                fallback_url = f"https://google.com{DRIVE_FOLDER_ID}&sz=w1000"
                st.image(fallback_url, caption=f"معاينة المنتج السريعة: {code}", use_container_width=True)
                
        else:
            st.error(f"❌ لم يتم العثور على تطابق كامل للرمز المكتوب: ({search_query})")
            
            similar_matches = df[df[col_code].str.contains(search_query, na=False, case=False) | 
                                 df[col_barcode].str.contains(search_query, na=False, case=False)]
            
            if not similar_matches.empty:
                st.markdown("### 💡 هل تقصد أحد هذه الرموز القريبة؟")
                for idx, row in similar_matches.head(5).iterrows():
                    sim_code = row[col_code]
                    sim_desc = row[col_desc]
                    st.markdown(f"""
                    <div class="suggestion-box">
                        <p style='color: #4ade80; font-weight: bold; margin:0;'>كود المنتج المقترح: {sim_code}</p>
                        <p style='color: #f1f5f9; margin: 2px 0;'>📝 الوصف: {sim_desc}</p>
                    </div>
                    """, unsafe_allow_html=True)
else:
    st.error("تأكد من وجود ملف DATABASE.xlsx في مستودع GitHub الخاص بك بجوار ملف app.py.")

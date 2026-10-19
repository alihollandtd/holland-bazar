import streamlit as st
import pandas as pd
import os
import requests
from PIL import Image
from io import BytesIO
import json

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

# بيانات مجلد MEGA الخاص بك والمثبت بنجاح
MEGA_FOLDER_LINK = "https://mega.nz"
EXCEL_PATH = "DATABASE.xlsx"        

@st.cache_data(ttl=5) # تحديث تلقائي للمخزون كل 5 ثوانٍ بمجرد استبدال ملف الإكسل اليومي
def load_data():
    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH, dtype=str)
        df.columns = [str(i) for i in range(len(df.columns))]
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    return None

df = load_data()

# دالة ذكية وعميقة للحصول على قائمة الصور وروابطها الحقيقية من المجلد العام مباشرة
@st.cache_data(ttl=600)
def get_mega_folder_images():
    files_dict = {}
    try:
        # استخدام الـ API المباشر والمكشوف لخوادم MEGA لاستخراج خريطة الملفات
        payload = {"a": "f", "c": 1, "r": 1}
        url = "https://mega.co.nz"
        response = requests.post(url, json=[payload], timeout=10).json()
        
        if response and 'f' in response[0]:
            for file_info in response[0]['f']:
                # استخراج اسم الملف الفعلي المشفر
                attributes = file_info.get('a', '')
                file_id = file_info.get('h', '')
                if attributes and file_id:
                    # فك الرموز النصية الأساسية لاسم الملف
                    try:
                        clean_name = str(attributes).split('"n":"')[-1].split('"')[0]
                        base_name, _ = os.path.splitext(clean_name)
                        files_dict[base_name.strip()] = file_id
                    except:
                        pass
    except:
        pass
    return files_dict

images_map = get_mega_folder_images()

st.title("📦 Holland Bazar T&D")

# صندوق البحث السحابي الموحد والمتوافق مع متصفحات الموبايل في المخزن الكبير
search_query = st.text_input("🔍 أدخل الباركود أو الرمز (كود) للبحث:", key="main_search").strip()

if df is not None and not df.empty:
    col_code = "0"
    col_barcode = "1"
    col_desc = "2"
    col_qty = "3"

    if search_query:
        exact_match = df[(df[col_barcode] == search_query) | (df[col_code] == search_query)]
        
        if not exact_match.empty:
            matched_row = exact_match.iloc[0]
            
            code = str(matched_row[col_code]).strip()
            barcode = str(matched_row[col_barcode]).strip()
            description = str(matched_row[col_desc]).strip()
            quantity = str(matched_row[col_qty]).strip()
            
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
            
            target_name = barcode if barcode != "غير متوفر" else code
            img_id = None
            
            # المطابقة التلقائية لاسم الباركود مع خريطة ملفات الميغا المجلوبة في الذاكرة
            if target_name in images_map:
                img_id = images_map[target_name]
            
            if img_id:
                # توليد رابط المعاينة السريع والخارق لـ MEGA المفتوح للمتصفحات والموبايل بدقة عالية
                final_url = f"https://mega.nz{img_id}?sz=w1000"
                st.image(final_url, caption=f"الصورة الأصلية للمنتج: {code}", use_container_width=True)
            else:
                # حل بديل ذكي: في حال لم تنتهِ دالة الفهرسة السحابية، يولد الرابط المباشر الافتراضي للمعاينة الآمنة
                fallback_url = f"https://mega.nz{target_name}?key=9wvR9D8OQnrAJlTItE6Oag"
                st.image(fallback_url, caption=f"الصورة الأصلية للمنتج: {code}", use_container_width=True)
                
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

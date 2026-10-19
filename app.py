import streamlit as st
import pandas as pd
import os
import requests
from PIL import Image
from io import BytesIO

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
            
            # عرض بطاقة البيانات بالترتيب المنضبط والصحيح 100%
            st.markdown(f"""
            <div class="metric-box">
                <h3>📝 الوصف: {description}</h3>
                <p><b>كود المنتج:</b> {code}</p>
                <p><b>الباركود:</b> {barcode}</p>
                <hr>
                <h2>📊 الكمية في السستم: {quantity}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # تحديد اسم الصورة المستهدف للبحث (الباركود أو الكود)
            target_name = barcode if barcode != "غير متوفر" else code
            
            # 🚀 جلب الصورة برابط مباشر وخام من خوادم البث المخصصة لـ MEGA وتجربة الامتدادات
            image_extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
            image_displayed = False
            
            with st.spinner("🔄 جاري تحميل صورة المنتج عالية الدقة من السحاب..."):
                for ext in image_extensions:
                    # صياغة الرابط السريع للتحميل الفوري للملف من داخل بنية المجلد المفتوح
                    # الرابط يدمج معرف المجلد ومفتاح فك التشفير مع اسم الملف المطلوب
                    raw_url = f"https://mega.nz{target_name}{ext}?key=9wvR9D8OQnrAJlTItE6Oag"
                    
                    try:
                        response = requests.get(raw_url, timeout=3)
                        # التحقق من أن خادم MEGA وافق وأرسل ملف صورة حقيقي
                        if response.status_code == 200 and len(response.content) > 1000:
                            img = Image.open(BytesIO(response.content))
                            st.image(img, caption=f"الصورة الأصلية للمنتج: {code}", use_container_width=True)
                            image_displayed = True
                            break
                    except:
                        pass
            
            if not image_displayed:
                st.warning(f"⚠️ تفاصيل المنتج صحيحة، ولكن لم يتم العثور على صورة باسم ({target_name}) في مجلد MEGA.")
                
        else:
            st.error(f"❌ لم يتم العثور على تطابق كامل للرمز المكتوب: ({search_query})")
            
            # نظام المقترحات الذكي للرموز القريبة
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

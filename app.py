import streamlit as st
import pandas as pd
import os
from googleapiclient.discovery import build

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

# معرّف مجلد صور Google Drive العام الخاص بك والمثبت بنجاح
DRIVE_FOLDER_ID = "1l4jD0-Vuh4SLyoid9zugUGBtDsUBu5A7"
EXCEL_PATH = "DATABASE.xlsx"        

@st.cache_data(ttl=5) # تحديث تلقائي للمخزون كل 5 ثوانٍ بمجرد رفع الإكسل الجديد
def load_data():
    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH, dtype=str)
        df.columns = [str(i) for i in range(len(df.columns))]
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    return None

# دالة ذكية للبحث السحابي الفوري داخل مجلد جوجل درايف العام وجلب معرف الصورة المطابقة بدون حظر
def find_image_in_drive(search_name, folder_id):
    try:
        # بناء اتصال عام ومفتوح للبحث في الملفات العامة بدون حظر القيود
        drive_service = build('drive', 'v3', developerKey=None, authentication=None)
        
        # صياغة استعلام بحث متطور يبحث عن اسم الملف داخل مجلدك المشترك
        query = f"'{folder_id}' in parents and name contains '{search_name}' and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        if items:
            # إرجاع معرّف أول صورة مطابقة تماماً للاسم
            return items[0]['id']
    except:
        pass
    return None

df = load_data()

st.title("📦 Holland Bazar T&D")

# صندوق البحث السحابي الموحد والمتوافق مع متصفحات الموبايل في المخزن الكبير
search_query = st.text_input("🔍 أدخل الباركود أو الرمز (كود) للبحث:", key="main_search").strip()

if df is not None and not df.empty:
    # الترتيب الفيزيائي للأعمدة في ملف DATABASE.xlsx:
    # عمود 0 = كود | عمود 1 = الباركود | عمود 2 = الوصف | عمود 3 = الكمية
    col_code = "0"
    col_barcode = "1"
    col_desc = "2"
    col_qty = "3"

    if search_query:
        # البحث المباشر في عمودي الباركود والكود معاً
        exact_match = df[(df[col_barcode] == search_query) | (df[col_code] == search_query)]
        
        if not exact_match.empty:
            row = exact_match.iloc[0]
            code = str(row[col_code]).strip()
            barcode = str(row[col_barcode]).strip()
            description = str(row[col_desc]).strip()
            quantity = str(row[col_qty]).strip()
            
            if barcode.lower() == 'nan' or barcode == '': barcode = "غير متوفر"
            if quantity.lower() == 'nan' or quantity == '': quantity = "0"
            
            # عرض بطاقة البيانات بالترتيب المنضبط
            st.markdown(f"""
            <div class="metric-box">
                <h3>📝 الوصف: {description}</h3>
                <p><b>كود المنتج:</b> {code}</p>
                <p><b>الباركود:</b> {barcode}</p>
                <hr>
                <h2>📊 الكمية في السستم: {quantity}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # 🚀 رحلة البحث الذكية عن الصورة داخل المجلد السحابي بـ 3 محاولات
            img_id = None
            
            # محاولة 1: البحث باسم الباركود الكامل المكتوب
            if barcode != "غير متوفر":
                img_id = find_image_in_drive(barcode, DRIVE_FOLDER_ID)
                
            # محاولة 2: إذا لم يجدها، يبحث بكود المنتج القصير (مثل GR-55-8)
            if not img_id and code != "غير متوفر":
                img_id = find_image_in_drive(code, DRIVE_FOLDER_ID)
            
            # عرض الصورة فور العثور عليها وتوليد الرابط المباشر الصحيح
            if img_id:
                # رابط المعاينة السحابي بدقة كاملة وعالية واضحة للمتصفحات والموبايل
                final_img_url = f"https://google.com{img_id}&sz=w1000"
                st.image(final_img_url, caption=f"الصورة الأصلية للمنتج: {code}", use_container_width=True)
            else:
                st.warning(f"⚠️ تفاصيل المنتج صحيحة، ولكن لم يعثر النظام على ملف صورة باسم ({barcode}) أو ({code}) داخل مجلد Google Drive.")
                
        else:
            st.error(f"❌ لم يتم العثور على تطابق كامل للرمز المكتوب: ({search_query})")
            
            # نظام المقترحات الذكي
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

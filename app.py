import streamlit as st
import pandas as pd
import os
from mega import Mega

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

# مسار مجلد MEGA الخاص بك والمثبت بنجاح
MEGA_URL = "https://mega.nz"
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
            
            # عرض بطاقة البيانات بالترتيب المنضبط والصحيح 100% بدون أخطاء
            st.markdown(f"""
            <div class="metric-box">
                <h3>📝 الوصف: {description}</h3>
                <p><b>كود المنتج:</b> {code}</p>
                <p><b>الباركود:</b> {barcode}</p>
                <hr>
                <h2>📊 الكمية في السستم: {quantity}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # تحديد اسم الصورة المستهدف البحث عنه (الباركود أو الكود)
            target_name = barcode if barcode != "غير متوفر" else code
            
            # 🚀 استدعاء الصورة وفك تشفيرها تلقائياً ولحظياً من مجلد MEGA الخاص بك
            with st.spinner("🔄 جاري سحب صورة المنتج عالية الدقة من خادم MEGA..."):
                try:
                    mega = Mega()
                    # الاتصال بالمجلد العام وتفحص محتوياته
                    folder = mega.login_anonymous(MEGA_URL)
                    files = folder.get_files()
                    
                    img_file = None
                    image_extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
                    
                    # البحث عن الملف المطابق لاسم الباركود أو الكود مع الامتدادات المختلفة
                    for file_id, file_info in files.items():
                        file_name = file_info.get('a', {}).get('n', '')
                        for ext in image_extensions:
                            if file_name == f"{target_name}{ext}":
                                img_file = (file_id, file_name)
                                break
                        if img_file:
                            break
                    
                    if img_file:
                        # تحميل الملف مؤقتاً في الذاكرة الحية وعرضه
                        temp_path = folder.download_file(img_file[0], dest_filename=img_file[1])
                        if os.path.exists(temp_path):
                            st.image(temp_path, caption=f"الصورة الأصلية للمنتج: {code}", use_container_width=True)
                            # حذف الملف المؤقت فوراً بعد العرض لحماية مساحة السيرفر
                            os.remove(temp_path)
                    else:
                        st.warning(f"⚠️ تفاصيل المنتج صحيحة، ولكن لم يعثر النظام على ملف صورة باسم ({target_name}) داخل مجلد MEGA.")
                except Exception as e:
                    st.warning("⚠️ المنتج مسجل، ولكن واجه النظام صعوبة مؤقتة في فك تشفير خادم MEGA الصوري.")
                
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

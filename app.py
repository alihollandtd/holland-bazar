import streamlit as st
import pandas as pd
import os
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

# دمج معرّف مجلد صور Google Drive الخاص بك تلقائياً بنجاح
DRIVE_FOLDER_ID = "1l4jD0-Vuh4SLyoid9zugUGBtDsUBu5A7"
EXCEL_PATH = "DATABASE.xlsx"        

@st.cache_data(ttl=5) # تحديث تلقائي للمخزون والجرد كل 5 ثوانٍ بمجرد استبدال ملف الإكسل
def load_data():
    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH, dtype=str)
        return df
    return None

df = load_data()

st.title("📦 Holland Bazar T&D")

# صندوق البحث المتطور المتوافق مع الهواتف في الممرات البعيدة للمستودع
search_query = st.text_input("🔍 أدخل الباركود أو الرمز (كود) للبحث:", key="main_search").strip()

if df is not None and not df.empty:
    df.columns = [str(c).strip() for c in df.columns]
    
    col_code_name = df.columns     
    col_barcode_name = df.columns  
    col_desc_name = df.columns     
    col_qty_name = df.columns      

    df[col_code_name] = df[col_code_name].astype(str).str.strip()
    df[col_barcode_name] = df[col_barcode_name].astype(str).str.strip()

    if search_query:
        exact_match = df[(df[col_barcode_name] == search_query) | (df[col_code_name] == search_query)]
        
        if not exact_match.empty:
            row = exact_match.iloc[0]
            code = str(row[col_code_name]).strip()
            barcode = str(row[col_barcode_name]).strip()
            description = str(row[col_desc_name]).strip()
            quantity = str(row[col_qty_name]).strip()
            
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
            
            # تحديد اسم الصورة المستهدف البحث عنه سحابياً (الأولوية للباركود ثم الكود)
            target_image_name = barcode if barcode != "غير متوفر" else code
            
            # آلية ذكية للتحقق برمجياً من صيغة الصورة المتوفرة في Google Drive وعرضها فوراً
            image_extensions = ['jpeg', 'png', 'jpg', 'PNG', 'JPG']
            img_url_to_use = None
            
            for ext in image_extensions:
                # توليد وتجربة الرابط المباشر لكل صيغة بدقة أصلية كاملة
                test_url = f"https://google.com{DRIVE_FOLDER_ID}&sz=w1000"
                
                # فحص سريع لضمان عمل الرابط وعدم كسر الصورة
                try:
                    response = requests.head(test_url, timeout=2)
                    if response.status_code == 200:
                        img_url_to_use = test_url
                        break
                except:
                    pass
            
            # إذا لم ينجح فحص الـ Thumbnail المباشر، نعتمد على الرابط الافتراضي المستقر للعرض السحابي
            if not img_url_to_use:
                img_url_to_use = f"https://google.com{DRIVE_FOLDER_ID}&sz=w1000"
            
            st.image(img_url_to_use, caption=f"الصورة الأصلية للمنتج عالية الدقة: {target_image_name}", use_container_width=True)
                
        else:
            st.error(f"❌ لم يتم العثور على تطابق كامل للرمز المكتوب: ({search_query})")
            
            similar_matches = df[df[col_code_name].str.contains(search_query, na=False, case=False) | 
                                 df[col_barcode_name].str.contains(search_query, na=False, case=False)]
            
            if not similar_matches.empty:
                st.markdown("### 💡 هل تقصد أحد هذه الرموز القريبة؟")
                for idx, row in similar_matches.head(5).iterrows():
                    sim_code = row[col_code_name]
                    sim_desc = row[col_desc_name]
                    st.markdown(f"""
                    <div class="suggestion-box">
                        <p style='color: #4ade80; font-weight: bold; margin:0;'>كود المنتج المقترح: {sim_code}</p>
                        <p style='color: #f1f5f9; margin: 2px 0;'>📝 الوصف: {sim_desc}</p>
                    </div>
                    """, unsafe_allow_html=True)
else:
    st.error("تأكد من وجود ملف DATABASE.xlsx بجوار ملف app.py في مستودع GitHub.")

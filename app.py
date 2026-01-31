import streamlit as st
import pandas as pd
import random
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- إعدادات الصفحة ---
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🏥")

# --- تنسيق CSS (لجعل التطبيق عربي من اليمين لليسار) ---
st.markdown("""
<style>
    .main {
        direction: rtl;
        text-align: right;
    }
    div.stButton > button:first-child {
        background-color: #009688;
        color: white;
        width: 100%;
        border-radius: 10px;
    }
    .stTextInput > label, .stNumberInput > label, .stSelectbox > label {
        font-family: 'Tajawal', sans-serif;
        text-align: right;
        direction: rtl;
    }
    /* إخفاء القائمة العلوية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- دالة الاتصال بقوقل شيت ---
def connect_to_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["service_account"], scope)
        client = gspread.authorize(creds)
        sheet = client.open("Clinic_Data").sheet1
        return sheet
    except Exception as e:
        st.error(f"حدث خطأ في الاتصال بقاعدة البيانات: {e}")
        return None

# --- إدارة حالة الجلسة (Login Session) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ==========================================
# القائمة الجانبية (تسجيل الدخول للأخصائي)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063823.png", width=100)
    st.title("بوابة الموظفين")
    
    if not st.session_state['logged_in']:
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول"):
            if username == "admin" and password == "1234":
                st.session_state['logged_in'] = True
                st.success("تم الدخول بنجاح")
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة")
    else:
        st.success("مرحباً بك يا دكتورة 👋")
        if st.button("تسجيل خروج"):
            st.session_state['logged_in'] = False
            st.rerun()

# ==========================================
# المحتوى الرئيسي
# ==========================================

# 1. إذا كان المستخدم "أخصائي" (مسجل دخول) -> نعرض له الجدول من قوقل شيت
if st.session_state['logged_in']:
    st.title("لوحة تحكم الأخصائي 👩‍⚕️")
    st.info("هنا تظهر بيانات المرضى المحفوظة في Google Sheets مباشرة")
    
    # جلب البيانات
    sheet = connect_to_sheet()
    if sheet:
        data = sheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            # عرض الجدول التفاعلي
            st.dataframe(df, use_container_width=True)
            
            # زر تحديث البيانات
            if st.button("تحديث القائمة 🔄"):
                st.rerun()
        else:
            st.warning("لا يوجد مرضى مسجلين حتى الآن.")

# 2. إذا كان المستخدم "مريض" (غير مسجل دخول) -> نعرض نموذج التسجيل
else:
    st.title("مرحباً بك في العيادة الإلكترونية 🩺")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("تسجيل ملف جديد")
        with st.form("patient_form"):
            name = st.text_input("الاسم الثلاثي")
            phone = st.text_input("رقم الجوال")
            age = st.number_input("العمر", min_value=1, max_value=120, step=1)
            gender = st.selectbox("الجنس", ["أنثى", "ذكر"])
            weight = st.number_input("الوزن الحالي (كجم)", min_value=10.0, format="%.1f")
            target = st.text_input("الهدف الصحي (مثلاً: إنقاص وزن، لياقة)")
            
            submitted = st.form_submit_button("إرسال البيانات ✅")
            
            if submitted:
                if name and phone:
                    sheet = connect_to_sheet()
                    if sheet:
                        # تجهيز البيانات بنفس ترتيب ملف الإكسل
                        # الترتيب: file_no | Name | Age | Gender | Weight | Target | Status | phone
                        file_no = str(random.randint(1000, 9999))
                        status = "جديد"
                        
                        row = [file_no, name, age, gender, weight, target, status, phone]
                        
                        sheet.append_row(row)
                        
                        st.balloons()
                        st.success(f"تم تسجيلك بنجاح! رقم ملفك هو: {file_no}")
                else:
                    st.error("الرجاء تعبئة الاسم ورقم الجوال.")

    with col2:
        st.image("https://img.freepik.com/free-vector/doctor-character-background_1270-84.jpg", width=300)
        st.info("💡 ملاحظة: عند التسجيل، سيتم حفظ بياناتك فوراً في قاعدة البيانات وتظهر عند الأخصائي.")

import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- إعدادات الصفحة ---
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🏥")

# --- تنسيق CSS (لجعل التطبيق عربي وأنيق) ---
st.markdown("""
<style>
    .main {
        direction: rtl;
        text-align: right;
    }
    div.stButton > button:first-child {
        background-color: #009688;
        color: white;
        border-radius: 12px;
        padding: 10px;
        font-size: 18px;
    }
    .stTextInput > label, .stNumberInput > label, .stSelectbox > label, .stRadio > label {
        font-family: 'Tajawal', sans-serif;
        text-align: right;
        direction: rtl;
        font-weight: bold;
    }
    .stAlert {
        direction: rtl;
        text-align: right;
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
        return None

# --- إدارة حالة الجلسة ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ==========================================
# 1. القائمة الجانبية (للموظفين فقط)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063823.png", width=80)
    st.markdown("### 🔒 الدخول الإداري")
    
    if not st.session_state['logged_in']:
        with st.expander("تسجيل دخول الأخصائي"):
            username = st.text_input("اسم المستخدم", key="user")
            password = st.text_input("كلمة المرور", type="password", key="pass")
            if st.button("دخول"):
                if username == "admin" and password == "1234":
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("بيانات خاطئة")
    else:
        st.success("أهلاً دكتورة 👋")
        if st.button("تسجيل خروج"):
            st.session_state['logged_in'] = False
            st.rerun()

# ==========================================
# 2. المحتوى الرئيسي
# ==========================================

# --- سيناريو 1: إذا كان الأخصائي مسجل دخول (لوحة التحكم) ---
if st.session_state['logged_in']:
    st.title("لوحة تحكم العيادة 👩‍⚕️")
    st.info("بيانات المرضى المسجلة في Google Sheets:")
    
    sheet = connect_to_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                st.download_button("تحميل البيانات كملف Excel", df.to_csv().encode('utf-8'), "clinic_data.csv")
            else:
                st.warning("لا توجد بيانات حتى الآن.")
        except:
            st.error("حدث خطأ في جلب البيانات، تأكدي من أسماء الأعمدة في ملف الشيت.")
    
    if st.button("تحديث الصفحة 🔄"):
        st.rerun()

# --- سيناريو 2: واجهة المرضى (الشاشة الرئيسية) ---
else:
    st.title("مرحباً بكِ في العيادة الإلكترونية 🩺")
    st.markdown("##### يرجى اختيار نوع التسجيل للمتابعة:")
    
    # الخيار الرئيسي (مريض جديد vs مراجع)
    patient_type = st.radio(
        "",
        ["👤 تسجيل مريض جديد", "🗓️ دخول المراجعين (متابعة / استلام جدول)"],
        horizontal=True
    )
    
    st.markdown("---")

    # >>> خيار 1: تسجيل مريض جديد <<<
    if patient_type == "👤 تسجيل مريض جديد":
        st.subheader("📝 فتح ملف جديد")
        with st.form("new_patient_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("الاسم الثلاثي")
                phone = st.text_input("رقم الجوال (للمتابعة)")
                gender = st.selectbox("الجنس", ["أنثى", "ذكر"])
            with col2:
                age = st.number_input("العمر", min_value=1, max_value=100)
                weight = st.number_input("الوزن (kg)", min_value=10.0)
                target = st.selectbox("الهدف", ["إنقاص وزن", "زيادة وزن", "حياة صحية", "متابعة طبية"])
            
            submit_new = st.form_submit_button("حفظ البيانات وفتح الملف ✅")
            
            if submit_new:
                if name and phone:
                    sheet = connect_to_sheet()
                    if sheet:
                        try:
                            # توليد رقم ملف عشوائي
                            file_no = str(random.randint(1000, 9999))
                            status = "انتظار"
                            # الترتيب مطابق لملف الإكسل
                            row = [file_no, name, age, gender, weight, target, status, phone]
                            sheet.append_row(row)
                            
                            st.balloons()
                            st.success(f"تم فتح الملف بنجاح! 🎉 رقم ملفك هو: {file_no}")
                            st.info("يمكنك الآن الدخول لقسم المراجعين باستخدام رقم الجوال.")
                        except Exception as e:
                            st.error(f"حدث خطأ في الاتصال: {e}")
                else:
                    st.warning("الرجاء تعبئة الاسم ورقم الجوال.")

    # >>> خيار 2: دخول المراجعين <<<
    else:
        st.subheader("🔎 متابعة حالة الملف والجدول")
        search_phone = st.text_input("أدخل رقم الجوال المسجل للبحث:", placeholder="05xxxxxxxx")
        
        if st.button("بحث عن ملفي"):
            if search_phone:
                sheet = connect_to_sheet()
                if sheet:
                    try:
                        # جلب كل البيانات والبحث فيها
                        data = sheet.get_all_records()
                        df = pd.DataFrame(data)
                        
                        # التأكد من أن عمود phone موجود ويتم التعامل معه كنص
                        df['phone'] = df['phone'].astype(str)
                        patient_record = df[df['phone'] == search_phone]
                        
                        if not patient_record.empty:
                            name_found = patient_record.iloc[0]['Name']
                            file_found = patient_record.iloc[0]['file_no']
                            
                            st.success(f"أهلاً بك، {name_found} (ملف رقم: {file_found})")
                            
                            # عرض بطاقة الموعد (وهمية حالياً للتجربة)
                            st.info(f"📅 موعدك القادم: {datetime.now().strftime('%Y-%m-%d')} - الساعة 4:30 عصراً")
                            st.markdown("### خطتك الحالية:")
                            st.table(patient_record[['Weight', 'Target', 'Status']])
                        else:
                            st.error("لم يتم العثور على ملف بهذا الرقم. تأكد من الرقم أو قم بتسجيل ملف جديد.")
                    except Exception as e:
                        st.error(f"حدث خطأ فني: {e}")

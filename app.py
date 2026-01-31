import streamlit as st
import pandas as pd
import random
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- إعدادات الصفحة ---
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🩺")

# --- تنسيق CSS (تعريب وتجميل) ---
st.markdown("""
<style>
    .main { direction: rtl; text-align: right; }
    div.stButton > button:first-child {
        background-color: #009688; color: white; border-radius: 12px; width: 100%; padding: 10px; font-size: 18px;
    }
    .stTextInput > label, .stNumberInput > label, .stSelectbox > label, .stRadio > label {
        font-family: 'Tajawal', sans-serif; text-align: right; direction: rtl; font-weight: bold;
    }
    .stAlert { direction: rtl; text-align: right; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
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
        st.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        return None

# --- إدارة الحالة (Session State) ---
if 'step' not in st.session_state: st.session_state.step = 0
if 'user_type' not in st.session_state: st.session_state.user_type = None
if 'patient_data' not in st.session_state: st.session_state.patient_data = {}

# دوال التنقل
def next_step(): st.session_state.step += 1
def restart():
    st.session_state.step = 0
    st.session_state.user_type = None
    st.session_state.patient_data = {}

# ==========================================
# 🔐 القائمة الجانبية (بوابة الأخصائية)
# ==========================================
is_admin = False
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063823.png", width=60)
    st.markdown("### 🔒 بوابة الموظفين")
    
    with st.expander("تسجيل دخول الأخصائي"):
        access_code = st.text_input("الرمز السري", type="password")
        if access_code == "admin123":
            is_admin = True
            st.success("مرحباً دكتورة! 👋")

# ==========================================
# 👩‍⚕️ المسار 1: لوحة التحكم (Admin)
# ==========================================
if is_admin:
    st.title("👩‍⚕️ لوحة إدارة العيادة")
    
    sheet = connect_to_sheet()
    if sheet:
        data = sheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            st.markdown(f"### 📂 عدد الملفات المسجلة: {len(df)}")
            st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            st.info("💡 لمراجعة الإيصالات: حالياً جوجل شيت لا يعرض الصور، يجب التأكد من الإيصال عبر التواصل مع المريض أو طلب إرساله واتساب.")
        else:
            st.warning("لا توجد بيانات حتى الآن.")

# ==========================================
# 📱 المسار 2: واجهة المرضى
# ==========================================
else:
    # الشاشة الرئيسية
    if st.session_state.step == 0:
        st.title("مرحباً بك في العيادة الإلكترونية 🩺")
        st.markdown("##### يرجى اختيار نوع الخدمة:")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 فتح ملف جديد", use_container_width=True):
                st.session_state.user_type = 'new'; st.session_state.step = 1; st.rerun()
        with col2:
            if st.button("🔎 دخول المراجعين (متابعة)", use_container_width=True):
                st.session_state.user_type = 'returning'; st.session_state.step = 1; st.rerun()

    # ------------------------------------------------
    # (أ) مسار تسجيل مريض جديد (الخطوات)
    # ------------------------------------------------
    elif st.session_state.user_type == 'new':
        
        # خطوة 1: المعلومات الشخصية
        if st.session_state.step == 1:
            st.markdown("### 👤 أولاً: نتعرف عليك")
            name = st.text_input("الاسم الثلاثي")
            phone = st.text_input("رقم الجوال (سيتم استخدامه للدخول لاحقاً)")
            
            c1, c2 = st.columns(2)
            age = c1.number_input("العمر", 10, 100, 25)
            gender = c2.radio("الجنس", ["أنثى", "ذكر"], horizontal=True)
            
            c3, c4 = st.columns(2)
            height = c3.number_input("الطول (سم)", 100, 220, 160)
            weight = c4.number_input("الوزن (كجم)", 30.0, 200.0, 70.0)
            
            target = st.text_input("ما هو هدفك الصحي؟ (مثلاً: إنقاص وزن، لياقة..)")
            
            if st.button("التالي: النشاط والعادات ⬅️"):
                if name and phone:
                    st.session_state.patient_data.update({
                        'name': name, 'phone': phone, 'age': age, 'gender': gender,
                        'height': height, 'weight': weight, 'target': target
                    })
                    next_step(); st.rerun()
                else:
                    st.error("الرجاء كتابة الاسم ورقم الجوال للمتابعة.")

        # خطوة 2: النشاط والروتين
        elif st.session_state.step == 2:
            st.markdown("### ⚡ ثانياً: نمط حياتك")
            notes = st.text_area("اكتبي لنا باختصار عن نظامك الغذائي الحالي، هل لديك حساسية؟ أو ملاحظات؟")
            
            if st.button("التالي: الدفع والتأكيد ⬅️"):
                st.session_state.patient_data.update({'notes': notes})
                next_step(); st.rerun()

        # خطوة 3: الدفع (المعدلة)
        elif st.session_state.step == 3:
            st.markdown("### 💳 أخيراً: إتمام الاشتراك")
            st.info("قيمة الاشتراك في البرنامج: **350 ريال**")
            
            st.write("اختر طريقة الدفع المناسبة:")
            payment_method = st.radio("", [" Apple Pay", "🏦 تحويل بنكي"], horizontal=True)
            
            st.markdown("---")
            
            if payment_method == " Apple Pay":
                st.markdown("""
                #### 📲 الدفع عبر Apple Pay
                الرجاء التحويل على الرقم التالي:
                ## **0500000000**
                *(باسم: د. أثير)*
                """)
            
            else:
                st.markdown("""
                #### 🏦 التحويل البنكي (الراجحي)
                رقم الآيبان:
                ## **SA00000000000000000000**
                *(باسم: عيادة أثير)*
                """)
            
            st.markdown("---")
            st.markdown("**📸 خطوة ضرورية: يرجى إرفاق صورة الإيصال أو الشاشة لإتمام التسجيل**")
            uploaded_receipt = st.file_uploader("ارفع الصورة هنا", type=['png', 'jpg', 'jpeg', 'pdf'])
            
            if st.button("✅ تأكيد الدفع وفتح الملف"):
                if uploaded_receipt:
                    # عملية الحفظ في قوقل شيت
                    sheet = connect_to_sheet()
                    if sheet:
                        try:
                            # توليد رقم ملف
                            file_no = str(random.randint(1000, 9999))
                            p = st.session_state.patient_data
                            
                            # ترتيب البيانات حسب أعمدة الإكسل
                            # file_no | Name | phone | Age | Gender | Weight | Target | notes | Status | Payment_Type
                            row = [
                                file_no,
                                p['name'],
                                p['phone'],
                                p['age'],
                                p['gender'],
                                p['weight'],
                                p['target'],
                                p['notes'],
                                "جديد (بانتظار التأكيد)",
                                payment_method
                            ]
                            
                            sheet.append_row(row)
                            
                            # نجاح العملية
                            st.balloons()
                            st.success(f"تم التسجيل بنجاح يا {p['name']}! 🎉")
                            st.markdown(f"### رقم ملفك الطبي هو: `{file_no}`")
                            st.info("سيتم مراجعة الإيصال وتفعيل حسابك، وسنرسل الجدول قريباً.")
                            
                            if st.button("عودة للرئيسية"): restart(); st.rerun()
                            
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء الحفظ، حاولي مرة أخرى: {e}")
                else:
                    st.error("⚠️ عذراً، لا يمكن إتمام التسجيل بدون إرفاق صورة الإيصال.")

    # ------------------------------------------------
    # (ب) مسار المراجعين (تسجيل الدخول بالجوال)
    # ------------------------------------------------
    elif st.session_state.user_type == 'returning':
        
        # شاشة تسجيل الدخول
        if st.session_state.step == 1:
            st.markdown("### 🔎 متابعة المراجعين")
            phone_input = st.text_input("أدخلي رقم الجوال المسجل للبحث عن ملفك:", placeholder="05xxxxxxxx")
            
            if st.button("دخول"):
                if phone_input:
                    sheet = connect_to_sheet()
                    if sheet:
                        try:
                            # جلب البيانات والبحث
                            data = sheet.get_all_records()
                            df = pd.DataFrame(data)
                            
                            # تحويل عمود الجوال لنص للمقارنة
                            df['phone'] = df['phone'].astype(str)
                            
                            # البحث عن الرقم
                            user_record = df[df['phone'] == phone_input]
                            
                            if not user_record.empty:
                                st.session_state.current_user = user_record.iloc[0]
                                next_step(); st.rerun()
                            else:
                                st.error("❌ لم يتم العثور على ملف بهذا الرقم. تأكدي من الرقم أو سجلي ملف جديد.")
                        except Exception as e:
                            st.error(f"خطأ: {e}")
                else:
                    st.warning("الرجاء كتابة الرقم.")

        # لوحة المريض بعد الدخول
        elif st.session_state.step == 2:
            user = st.session_state.current_user
            st.markdown(f"## أهلاً بكِ، {user['Name']} 👋")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("رقم الملف", user['file_no'])
            col2.metric("حالة الملف", user['Status'])
            col3.metric("الوزن المسجل", f"{user['Weight']} kg")
            
            st.markdown("---")
            
            if "جديد" in str(user['Status']):
                st.info("⏳ ملفك قيد المراجعة، سيتم تصميم الجدول وإرساله قريباً.")
            else:
                st.success("✅ ملفك نشط!")
                st.write("هنا ستظهر الجداول ومواعيد المراجعة مستقبلاً.")
            
            st.markdown("---")
            if st.button("تسجيل خروج"): restart(); st.rerun()

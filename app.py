import streamlit as st
import pandas as pd
import random
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- إعدادات الصفحة (الأساسيات) ---
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🩺")

# --- تنسيق CSS (نفس التنسيق الأصلي) ---
st.markdown("""
<style>
    .main { direction: rtl; text-align: right; }
    div.stButton > button:first-child {
        background-color: #009688; color: white; border-radius: 12px; width: 100%; padding: 10px; font-size: 18px;
    }
    .stTextInput > label, .stNumberInput > label, .stSelectbox > label, .stRadio > label, .stTextArea > label {
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

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1
def restart():
    st.session_state.step = 0
    st.session_state.user_type = None
    st.session_state.patient_data = {}

# ==========================================
# 🔐 القائمة الجانبية (بوابة الأخصائية)
# ==========================================
is_admin = False
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063823.png", width=50)
    st.markdown("### العيادة الإلكترونية")
    st.markdown("---")
    
    access_code = st.text_input("الدخول الإداري 🔒", type="password", placeholder="الرمز السري")
    
    if access_code == "admin123":
        is_admin = True
        st.success("مرحباً دكتورة! 👋")
        st.info("وضع المسؤول مفعل")
    else:
        st.caption("للمساعدة والاستفسار: تواصل معنا")

# ==========================================
# 👩‍⚕️ المسار 1: واجهة الأخصائية (التصميم الأصلي)
# ==========================================
if is_admin:
    st.title("👩‍⚕️ لوحة إدارة العيادة والملفات")
    
    sheet = connect_to_sheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                # معالجة العناوين لتجنب المشاكل
                raw_headers = all_values[0]
                rows = all_values[1:]
                headers = [str(h).strip().lower() for h in raw_headers]
                # إزالة التكرار في العناوين
                seen = {}; final_headers = []
                for h in headers:
                    if h in seen: seen[h]+=1; final_headers.append(f"{h}_{seen[h]}")
                    else: seen[h]=0; final_headers.append(h)

                df = pd.DataFrame(rows, columns=final_headers)
                
                # التأكد من الأعمدة
                if 'diet_plan' not in df.columns: df['diet_plan'] = ""
                if 'hidden_details' not in df.columns: df['hidden_details'] = ""

                # فلترة المرضى (اللي ما عندهم رابط دايت)
                pending_patients = df[df['diet_plan'].str.len() < 5] # أقل من 5 حروف يعني غالباً فاضي
                
                tab1, tab2 = st.tabs(["🆕 طلبات بانتظار التصميم", "📂 أرشيف المرضى"])
                
                with tab1:
                    if not pending_patients.empty:
                        st.write(f"لديك ({len(pending_patients)}) مريض بانتظار الجدول.")
                        
                        for index, pt in pending_patients.iterrows():
                            pt_name = pt.get('name', 'غير معروف')
                            pt_file = pt.get('file_no', '#')
                            
                            with st.expander(f"ملف: {pt_name} (#{pt_file})", expanded=True):
                                # 1. البيانات الأساسية من أعمدة الإكسل
                                c1, c2 = st.columns(2)
                                c1.info(f"**الهدف:** {pt.get('target', '-')}")
                                c2.warning(f"**الوزن:** {pt.get('weight', '-')} | **الطول:** {pt.get('height', '-')}")
                                
                                st.markdown("---")
                                # 2. التفاصيل الكاملة (من العمود المخفي)
                                st.markdown("##### 📝 تفاصيل الحالة:")
                                details = pt.get('hidden_details', 'لا توجد تفاصيل')
                                st.text_area("بيانات المريض:", value=details, height=150, disabled=True, key=f"det_{pt_file}")
                                
                                st.markdown("---")
                                # 3. خانة إرسال الجدول
                                st.markdown("##### 📤 إرسال الجدول:")
                                with st.form(key=f"diet_f_{pt_file}"):
                                    diet_link = st.text_input("رابط الجدول (Drive/PDF Link):", placeholder="https://...")
                                    if st.form_submit_button("إرسال واعتماد ✅"):
                                        try:
                                            cell = sheet.find(str(pt_file))
                                            if cell:
                                                # تحديث عمود diet_plan فقط
                                                if 'diet_plan' in headers:
                                                    col_idx = headers.index('diet_plan') + 1
                                                    sheet.update_cell(cell.row, col_idx, diet_link)
                                                    st.success(f"تم إرسال الجدول لـ {pt_name}")
                                                    st.rerun()
                                        except Exception as e:
                                            st.error(f"خطأ: {e}")
                    else:
                        st.success("🎉 لا توجد طلبات معلقة.")

                with tab2:
                    st.dataframe(df, use_container_width=True)
            else:
                st.info("لا توجد بيانات.")
        except Exception as e:
            st.error(f"خطأ في القراءة: {e}")

# ==========================================
# 📱 المسار 2: واجهة المريض (التصميم الأصلي)
# ==========================================
else:
    if st.session_state.step == 0:
        st.title("مرحباً بك في العيادة الإلكترونية 🩺")
        st.markdown("يرجى اختيار نوع التسجيل للمتابعة:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 تسجيل مريض جديد", use_container_width=True):
                st.session_state.user_type = 'new'; st.session_state.step = 1; st.rerun()
        with col2:
            if st.button("📂 دخول المراجعين", use_container_width=True):
                st.session_state.user_type = 'returning'; st.session_state.step = 1; st.rerun()

    # --- تسجيل مريض جديد ---
    elif st.session_state.user_type == 'new':
        
        # خطوة 1: شخصي
        if st.session_state.step == 1:
            st.markdown("### 👤 الخطوة 1: المعلومات الشخصية")
            name = st.text_input("الاسم الثلاثي")
            phone = st.text_input("رقم الجوال")
            c1, c2 = st.columns(2)
            age = c1.number_input("العمر", 10, 100, 25)
            gender = c2.radio("الجنس", ["ذكر", "أنثى"], horizontal=True)
            c3, c4 = st.columns(2)
            height = c3.number_input("الطول (سم)", 100, 220, 160)
            weight = c4.number_input("الوزن (كجم)", 30.0, 200.0, 70.0)
            target = st.number_input("الوزن المستهدف", 30.0, 200.0, 60.0)
            st.markdown("---")
            goals = st.multiselect("الأهداف", ["خسارة وزن", "زيادة عضل", "صحة عامة"])
            
            if st.button("التالي ⬅️"):
                if name and phone:
                    st.session_state.patient_data.update({'name': name, 'phone': phone, 'age': age, 'gender': gender, 'height': height, 'weight': weight, 'target': target, 'goals': goals})
                    next_step(); st.rerun()
                else: st.error("الاسم والجوال مطلوبان")

        # خطوة 2: النشاط
        elif st.session_state.step == 2:
            st.markdown("### ⚡ الخطوة 2: النشاط")
            activity = st.radio("مستوى النشاط", ["خامل", "متوسط", "عالي"])
            gym = st.radio("مكان التمرين", ["منزل", "نادي"])
            days = st.slider("أيام التمرين", 0, 7, 3)
            type_ex = st.multiselect("نوع الرياضة", ["مقاومة", "كارديو", "سباحة"])
            
            c1, c2 = st.columns([1,1])
            with c1: 
                if st.button("التالي ⬅️"):
                    st.session_state.patient_data.update({'activity': activity, 'gym': gym, 'days': days, 'type_ex': type_ex})
                    next_step(); st.rerun()
            with c2:
                if st.button("رجوع"): prev_step(); st.rerun()

        # خطوة 3: التغذية
        elif st.session_state.step == 3:
            st.markdown("### 🍽️ الخطوة 3: العادات الغذائية")
            meals = st.selectbox("عدد الوجبات", ["1", "2", "3", "4+"])
            time = st.radio("وقت ثابت للوجبات؟", ["نعم", "لا"])
            allergies = st.text_input("حساسية طعام؟")
            dislikes = st.text_input("أكل ما تحبه؟")
            
            c1, c2 = st.columns([1,1])
            with c1: 
                if st.button("التالي ⬅️"):
                    st.session_state.patient_data.update({'meals': meals, 'time': time, 'allergies': allergies, 'dislikes': dislikes})
                    next_step(); st.rerun()
            with c2:
                if st.button("رجوع"): prev_step(); st.rerun()

        # خطوة 4: الروتين
        elif st.session_state.step == 4:
            st.markdown("### 📝 الخطوة 4: الروتين اليومي")
            routine = st.text_area("اوصف يومك بالتفصيل:", height=150)
            notes = st.text_area("ملاحظات إضافية:")
            
            c1, c2 = st.columns([1,1])
            with c1: 
                if st.button("التالي ⬅️"):
                    st.session_state.patient_data.update({'routine': routine, 'notes': notes})
                    next_step(); st.rerun()
            with c2:
                if st.button("رجوع"): prev_step(); st.rerun()

        # خطوة 5: الدفع والحفظ
        elif st.session_state.step == 5:
            st.markdown("### 💳 الخطوة الأخيرة: الدفع")
            st.info("التحويل البنكي - مصرف الراجحي")
            st.code("SA0000000000000000000000")
            uploaded = st.file_uploader("إرفاق الإيصال", type=['png', 'jpg', 'pdf'])
            
            c1, c2 = st.columns([1,1])
            with c1:
                if st.button("✅ تأكيد التسجيل"):
                    if uploaded:
                        try:
                            sheet = connect_to_sheet()
                            if sheet:
                                # تجهيز البيانات حسب الترتيب الجديد
                                p = st.session_state.patient_data
                                new_file = str(random.randint(10000, 99999))
                                
                                # تجميع التفاصيل الإضافية في نص واحد للعمود المخفي
                                hidden_details = f"""
                                الأهداف: {p.get('goals')}
                                النشاط: {p.get('activity')} ({p.get('gym')}) - {p.get('days')} أيام - {p.get('type_ex')}
                                التغذية: {p.get('meals')} وجبات (وقت ثابت: {p.get('time')})
                                الحساسية: {p.get('allergies')} | الممنوعات: {p.get('dislikes')}
                                الروتين: {p.get('routine')}
                                ملاحظات: {p.get('notes')}
                                """.strip()

                                # الصف الجديد (9 أعمدة ظاهرة + 1 مخفي)
                                row = [
                                    new_file,           # file_no
                                    p.get('name'),      # Name
                                    str(p.get('phone')),# Phone
                                    p.get('gender'),    # Gender
                                    p.get('weight'),    # Weight
                                    p.get('target'),    # Target
                                    p.get('height'),    # Height
                                    p.get('age'),       # Age
                                    "",                 # diet_plan (فاضي)
                                    hidden_details      # Hidden_Details
                                ]
                                
                                sheet.append_row(row)
                                st.session_state.new_file_number = new_file
                                next_step(); st.rerun()
                        except Exception as e:
                            st.error(f"خطأ: {e}")
                    else:
                        st.error("مطلوب الإيصال")
            with c2:
                if st.button("رجوع"): prev_step(); st.rerun()

        elif st.session_state.step == 6:
            st.balloons()
            st.success(f"تم التسجيل! رقم ملفك: {st.session_state.new_file_number}")
            if st.button("عودة"): restart(); st.rerun()

    # --- دخول المراجعين ---
    elif st.session_state.user_type == 'returning':
        if st.session_state.step == 1:
            st.markdown("### 🔐 دخول المشتركين")
            phone = st.text_input("رقم الجوال")
            if st.button("دخول"):
                sheet = connect_to_sheet()
                if sheet:
                    try:
                        vals = sheet.get_all_values()
                        if len(vals) > 1:
                            headers = [str(h).strip().lower() for h in vals[0]]
                            df = pd.DataFrame(vals[1:], columns=headers)
                            phone_col = next((c for c in df.columns if 'phone' in c), None)
                            
                            if phone_col:
                                clean_in = str(phone).strip()
                                df['clean'] = df[phone_col].astype(str).apply(lambda x: x.split('.')[0].strip())
                                user = df[(df['clean'] == clean_in) | (df['clean'] == clean_in.lstrip('0'))]
                                
                                if not user.empty:
                                    st.session_state.patient_data = user.iloc[0].to_dict()
                                    next_step(); st.rerun()
                                else: st.error("غير مسجل")
                    except Exception as e: st.error(f"خطأ: {e}")

        elif st.session_state.step == 2:
            user = st.session_state.patient_data
            st.title(f"أهلاً {user.get('name')} 👋")
            
            diet = user.get('diet_plan', '')
            if diet and len(diet) > 5:
                st.success("✅ الجدول جاهز!")
                st.link_button("📄 فتح الجدول", diet)
            else:
                st.info("⏳ الجدول قيد التصميم")
            
            st.divider()
            if st.button("خروج"): restart(); st.rerun()

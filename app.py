import streamlit as st
import pandas as pd
import random
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- إعدادات الصفحة ---
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🩺")

# --- تنسيق CSS ---
st.markdown("""
<style>
    .main { direction: rtl; text-align: right; }
    div.stButton > button:first-child {
        background-color: #009688; color: white; border-radius: 12px; width: 100%; padding: 10px; font-size: 18px;
    }
    div.stButton > button.secondary-button {
        background-color: #f44336; color: white;
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

# --- إدارة الحالة ---
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
# 🔐 القائمة الجانبية (الأخصائية)
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
    else:
        st.caption("للمساعدة والاستفسار: تواصل معنا")

# ==========================================
# 👩‍⚕️ المسار 1: واجهة الأخصائية (Admin)
# ==========================================
if is_admin:
    st.title("👩‍⚕️ لوحة إدارة العيادة والملفات")
    
    sheet = connect_to_sheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            
            if len(all_values) > 1:
                # معالجة العناوين وتكرارها
                raw_headers = all_values[0]
                rows = all_values[1:]
                
                # تنظيف العناوين
                headers = [str(h).strip().lower() for h in raw_headers]
                # معالجة التكرار
                seen = {}
                final_headers = []
                for h in headers:
                    if h in seen: seen[h]+=1; final_headers.append(f"{h}_{seen[h]}")
                    else: seen[h]=0; final_headers.append(h)

                df = pd.DataFrame(rows, columns=final_headers)
                
                # التأكد من وجود الأعمدة
                if 'diet_plan' not in df.columns: df['diet_plan'] = ""
                if 'details' not in df.columns: df['details'] = "" # هنا كل التفاصيل المخفية

                st.markdown("### 📂 سجل المرضى")
                st.info("اضغطي على الملف لعرض التفاصيل الكاملة وإرسال الجدول.")
                
                for index, pt in df.iterrows():
                    pt_name = pt.get('name', 'غير محدد')
                    pt_file = pt.get('file_no', '---')
                    diet_status = pt.get('diet_plan', '')
                    
                    # أيقونة الحالة
                    icon = "✅" if diet_status and len(str(diet_status)) > 5 else "🆕"
                    
                    with st.expander(f"{icon} ملف: {pt_name} (#{pt_file})", expanded=False):
                        # 1. البيانات الأساسية من أعمدة الإكسل
                        c1, c2, c3 = st.columns(3)
                        c1.info(f"**الوزن:** {pt.get('weight')} | **الطول:** {pt.get('height')}")
                        c2.warning(f"**الهدف:** {pt.get('target')}")
                        c3.write(f"**العمر:** {pt.get('age')} | **الجنس:** {pt.get('gender')}")
                        
                        st.markdown("---")
                        
                        # 2. التفاصيل الكاملة (جلبناها من العمود المدمج Details)
                        st.markdown("### 📝 تفاصيل المريض الكاملة:")
                        details_text = pt.get('details', 'لا توجد تفاصيل إضافية')
                        # عرض التفاصيل داخل مربع نص للقراءة
                        st.text_area("بيانات الاستبيان (الروتين، النشاط، الأكل...):", value=details_text, height=200, disabled=True)
                        
                        st.markdown("---")
                        
                        # 3. خانة إرسال الجدول
                        st.markdown("### 📤 إرسال الجدول الغذائي")
                        st.write(f"الحالة الحالية: {'تم الإرسال' if icon == '✅' else 'بانتظار الإرسال'}")
                        
                        with st.form(key=f"form_{pt_file}"):
                            new_link = st.text_input("رابط الجدول (Drive/Canva/PDF Link):", value=diet_status, placeholder="https://...")
                            
                            if st.form_submit_button("إرسال واعتماد ✅"):
                                try:
                                    cell = sheet.find(str(pt_file))
                                    if cell:
                                        # تحديث عمود diet_plan فقط
                                        if 'diet_plan' in headers:
                                            col_idx = headers.index('diet_plan') + 1
                                            sheet.update_cell(cell.row, col_idx, new_link)
                                            st.success(f"تم حفظ الرابط وإرساله للمريض {pt_name}!")
                                            st.rerun()
                                except Exception as e:
                                    st.error(f"خطأ: {e}")

            else:
                st.info("لا توجد بيانات مسجلة بعد.")
        except Exception as e:
            st.error(f"حدث خطأ في قراءة البيانات: {e}")

# ==========================================
# 📱 المسار 2: واجهة المريض
# ==========================================
else:
    if st.session_state.step == 0:
        st.title("مرحباً بك في العيادة الإلكترونية 🩺")
        st.markdown("يرجى اختيار نوع التسجيل للمتابعة:")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("👤 تسجيل مريض جديد", use_container_width=True):
                st.session_state.user_type = 'new'; st.session_state.step = 1; st.rerun()
        with c2:
            if st.button("📂 دخول المراجعين", use_container_width=True):
                st.session_state.user_type = 'returning'; st.session_state.step = 1; st.rerun()

    # --- تسجيل مريض جديد ---
    elif st.session_state.user_type == 'new':
        if st.session_state.step == 1:
            st.markdown("### 👤 الخطوة 1: المعلومات الشخصية")
            name = st.text_input("الاسم الثلاثي")
            phone = st.text_input("رقم الجوال") 
            c1, c2 = st.columns(2)
            age = c1.number_input("العمر", 10, 100, 25)
            gender = c2.radio("الجنس", ["ذكر", "أنثى"], horizontal=True)
            c3, c4 = st.columns(2)
            height = c3.number_input("الطول (سم)", 100, 220, 160)
            weight = c4.number_input("الوزن الحالي (كجم)", 30.0, 200.0, 70.0)
            target_weight = st.number_input("الوزن المستهدف (كجم)", 30.0, 200.0, 60.0)
            st.markdown("---")
            goals = st.multiselect("الأهداف", ["خسارة وزن", "زيادة عضل", "صحة عامة"])
            
            c_back, c_next = st.columns([1, 2])
            with c_next:
                if st.button("التالي ⬅️", use_container_width=True):
                    if name and phone:
                        st.session_state.patient_data.update({'name': name, 'phone': phone, 'gender': gender, 'height': height, 'weight': weight, 'target_weight': target_weight, 'age': age, 'goals': str(goals)})
                        next_step(); st.rerun()
                    else: st.error("الاسم والجوال مطلوبان")
            with c_back:
                if st.button("🏠 إلغاء", use_container_width=True): restart(); st.rerun()

        elif st.session_state.step == 2:
            st.markdown("### ⚡ الخطوة 2: النشاط والروتين")
            activity = st.radio("النشاط", ["خامل", "متوسط", "عالي"])
            gym = st.radio("المكان", ["بيت", "نادي"])
            days = st.slider("أيام التمرين", 0, 7, 3)
            type_ex = st.multiselect("نوع التمرين", ["كارديو", "مقاومة"])
            c_back, c_next = st.columns([1, 2])
            with c_next:
                if st.button("التالي ⬅️", use_container_width=True):
                    st.session_state.patient_data.update({'activity': activity, 'gym': gym, 'days': days, 'type': str(type_ex)})
                    next_step(); st.rerun()
            with c_back:
                if st.button("رجوع"): prev_step(); st.rerun()

        elif st.session_state.step == 3:
            st.markdown("### 🍽️ الخطوة 3: التغذية")
            meals = st.selectbox("عدد الوجبات", ["1", "2", "3", "4+"])
            time = st.radio("وقت ثابت؟", ["نعم", "لا"])
            allergies = st.text_input("حساسية؟")
            dislikes = st.text_input("أكل ما تحبه؟")
            c_back, c_next = st.columns([1, 2])
            with c_next:
                if st.button("التالي ⬅️", use_container_width=True):
                    st.session_state.patient_data.update({'meals': meals, 'time': time, 'allergies': allergies, 'dislikes': dislikes})
                    next_step(); st.rerun()
            with c_back:
                if st.button("رجوع"): prev_step(); st.rerun()
        
        elif st.session_state.step == 4:
            st.markdown("### 📝 الخطوة 4: الروتين اليومي")
            routine = st.text_area("اوصف يومك بالتفصيل (من الصحيان للنوم):", height=200)
            notes = st.text_area("أي ملاحظات صحية أو أدوية؟")
            c_back, c_next = st.columns([1, 2])
            with c_next:
                if st.button("التالي: الدفع ⬅️", use_container_width=True):
                    st.session_state.patient_data.update({'routine': routine, 'notes': notes})
                    next_step(); st.rerun()
            with c_back:
                if st.button("رجوع"): prev_step(); st.rerun()

        elif st.session_state.step == 5:
            st.markdown("### 💳 الخطوة الأخيرة: الدفع")
            st.info("قيمة الاشتراك: 350 ر.س - تحويل بنكي (الراجحي)")
            st.code("SA0000000000000000000000")
            uploaded = st.file_uploader("إرفاق الإيصال", type=['png', 'jpg', 'pdf'])
            
            c_back, c_next = st.columns([1, 2])
            with c_next:
                if st.button("✅ تأكيد التسجيل", use_container_width=True):
                    if uploaded:
                        try:
                            sheet = connect_to_sheet()
                            if sheet:
                                # تجهيز البيانات
                                p = st.session_state.patient_data
                                new_file = str(random.randint(10000, 99999))
                                
                                # --- هنا السحر: تجميع التفاصيل في نص واحد ---
                                details_blob = f"""
                                الأهداف: {p.get('goals')}
                                النشاط: {p.get('activity')} ({p.get('gym')}) - {p.get('days')} أيام
                                التمارين: {p.get('type')}
                                الوجبات: {p.get('meals')} (وقت ثابت: {p.get('time')})
                                الحساسية: {p.get('allergies')} | الممنوعات: {p.get('dislikes')}
                                الروتين اليومي: {p.get('routine')}
                                ملاحظات/أدوية: {p.get('notes')}
                                """.strip()

                                # الحفظ حسب ترتيب الأعمدة الجديد والمختصر
                                # file_no | Name | Phone | Gender | Weight | Target | Height | Age | diet_plan | Details
                                row = [
                                    new_file,
                                    p.get('name'),
                                    str(p.get('phone')),
                                    p.get('gender'),
                                    p.get('weight'),
                                    p.get('target_weight'), # Target
                                    p.get('height'),
                                    p.get('age'),
                                    "", # diet_plan (فاضي بالبداية)
                                    details_blob # Details (كل المعلومات هنا)
                                ]
                                
                                sheet.append_row(row)
                                st.session_state.new_file_number = new_file
                                next_step(); st.rerun()
                        except Exception as e:
                            st.error(f"خطأ: {e}")
                    else:
                        st.error("مطلوب الإيصال")
            with c_back:
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
            c1, c2 = st.columns([2, 1])
            with c1:
                if st.button("دخول", use_container_width=True):
                    sheet = connect_to_sheet()
                    if sheet:
                        try:
                            vals = sheet.get_all_values()
                            if len(vals) > 1:
                                headers = [str(h).strip().lower() for h in vals[0]]
                                df = pd.DataFrame(vals[1:], columns=headers)
                                
                                # البحث عن الجوال
                                phone_col = next((c for c in df.columns if 'phone' in c), None)
                                if phone_col:
                                    clean_in = str(phone).strip()
                                    df['clean'] = df[phone_col].astype(str).apply(lambda x: x.split('.')[0].strip())
                                    
                                    user = df[
                                        (df['clean'] == clean_in) | 
                                        (df['clean'] == clean_in.lstrip('0')) | 
                                        (df['clean'].str.lstrip('0') == clean_in.lstrip('0'))
                                    ]
                                    
                                    if not user.empty:
                                        st.session_state.patient_data = user.iloc[0].to_dict()
                                        next_step(); st.rerun()
                                    else: st.error("غير مسجل")
                                else: st.error("خطأ تقني في الأعمدة")
                        except Exception as e: st.error(f"خطأ: {e}")
            with c2:
                if st.button("رجوع", use_container_width=True): restart(); st.rerun()

        elif st.session_state.step == 2:
            user = st.session_state.patient_data
            st.title(f"أهلاً {user.get('name')} 👋")
            
            diet_link = user.get('diet_plan', '')
            st.subheader("📥 جدولك الغذائي")
            
            if diet_link and len(diet_link) > 5:
                st.success("✅ الجدول جاهز!")
                st.link_button("📄 فتح الجدول (PDF/Link)", diet_link)
            else:
                st.info("⏳ جاري تصميم جدولك... يرجى الانتظار.")
            
            st.divider()
            if st.button("خروج"): restart(); st.rerun()

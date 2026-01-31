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
        st.info("وضع المسؤول مفعل")
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
                # --- إصلاح مشكلة تكرار الأعمدة ---
                raw_headers = all_values[0]
                rows = all_values[1:]
                
                # تنظيف العناوين: إزالة المسافات وجعلها فريدة
                seen = {}
                headers = []
                for h in raw_headers:
                    h_clean = str(h).strip().lower()
                    if not h_clean: h_clean = "unknown" # للأعمدة الفارغة
                    if h_clean in seen:
                        seen[h_clean] += 1
                        headers.append(f"{h_clean}_{seen[h_clean]}")
                    else:
                        seen[h_clean] = 0
                        headers.append(h_clean)

                df = pd.DataFrame(rows, columns=headers)
                
                # التأكد من وجود الأعمدة الضرورية
                if 'diet_plan_sent' not in df.columns: df['diet_plan_sent'] = "FALSE"
                if 'diet_link' not in df.columns: df['diet_link'] = ""

                # تنظيف عمود الحالة للمقارنة
                df['diet_sent_clean'] = df['diet_plan_sent'].astype(str).str.upper().str.strip()
                pending_patients = df[df['diet_sent_clean'] != "TRUE"]
                
                tab1, tab2 = st.tabs(["🆕 طلبات بانتظار التصميم", "📂 أرشيف المرضى"])
                
                with tab1:
                    if not pending_patients.empty:
                        st.write(f"لديك ({len(pending_patients)}) مريض بانتظار استلام الجدول.")
                        
                        for index, pt in pending_patients.iterrows():
                            # قراءة البيانات مع التعامل مع القيم المفقودة
                            pt_name = pt.get('name', 'غير محدد')
                            pt_file = pt.get('file_no', '---')
                            
                            with st.expander(f"ملف: {pt_name} (#{pt_file})", expanded=True):
                                c1, c2 = st.columns(2)
                                # هنا نربط Target بالهدف كما هو في ملفك
                                c1.info(f"**الهدف:** {pt.get('target', pt.get('goals', ''))}")
                                c2.warning(f"**الوزن:** {pt.get('weight', '')} كجم | **الطول:** {pt.get('hight', pt.get('height', ''))} سم")
                                
                                st.markdown("---")
                                st.write(f"**📱 الجوال:** {pt.get('phone', '')}")
                                st.write(f"**🏋️ النشاط:** {pt.get('activity', '')}")
                                st.write(f"**🥗 العادات:** {pt.get('meals_count', '')} وجبات")
                                st.write(f"**📝 الروتين:** {pt.get('daily_routine', 'لا يوجد')}")
                                
                                st.markdown("---")
                                st.markdown("### 📤 إرسال الجدول الغذائي")
                                st.info("بما أن قوقل شيت لا يحفظ الملفات، يرجى لصق رابط الجدول (Drive/Canva) هنا:")
                                
                                # خانة لوضع رابط الجدول
                                diet_link_input = st.text_input("رابط الجدول:", key=f"link_{pt_file}")
                                
                                if st.button(f"✅ إرسال الرابط وتحديث الحالة لـ {pt_name}", key=f"send_{pt_file}"):
                                    try:
                                        cell = sheet.find(str(pt_file))
                                        if cell:
                                            # تحديث حالة الإرسال (TRUE)
                                            # البحث عن مكان العمود بدقة
                                            # 1. تحديث diet_plan_sent
                                            col_sent_idx = headers.index("diet_plan_sent") + 1
                                            sheet.update_cell(cell.row, col_sent_idx, "TRUE")
                                            
                                            # 2. تحديث diet_link (إذا وجد الرابط)
                                            if diet_link_input:
                                                if "diet_link" in headers:
                                                    col_link_idx = headers.index("diet_link") + 1
                                                    sheet.update_cell(cell.row, col_link_idx, diet_link_input)
                                            
                                            st.success(f"تم إرسال الجدول للمريض {pt_name} بنجاح!")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"حدث خطأ: {e}")
                    else:
                        st.success("🎉 جميع الجداول تم إرسالها.")

                with tab2:
                    st.dataframe(df, use_container_width=True)
            else:
                st.info("لا توجد بيانات مسجلة بعد.")
        except Exception as e:
            st.error(f"حدث خطأ في قراءة البيانات: {e}")

# ==========================================
# 📱 المسار 2: واجهة المريض
# ==========================================
else:
    # الشاشة الرئيسية
    if st.session_state.step == 0:
        st.title("مرحباً بك في العيادة الإلكترونية 🩺")
        st.markdown("يرجى اختيار نوع التسجيل للمتابعة:")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 تسجيل جديد", use_container_width=True):
                st.session_state.user_type = 'new'; st.session_state.step = 1; st.rerun()
        with col2:
            if st.button("📂 دخول المراجعين ", use_container_width=True):
                st.session_state.user_type = 'returning'; st.session_state.step = 1; st.rerun()

    # ------------------------------------------------
    # (أ) مسار المريض الجديد
    # ------------------------------------------------
    elif st.session_state.user_type == 'new':
        
        # صفحة 1: شخصي
        if st.session_state.step == 1:
            st.markdown("### 👤 الخطوة 1: المعلومات الشخصية")
            name = st.text_input("الاسم الثلاثي")
            phone = st.text_input("رقم الجوال (مهم للدخول لاحقاً)") 
            
            c1, c2 = st.columns(2)
            age = c1.number_input("العمر", 10, 100, 25)
            gender = c2.radio("الجنس", ["ذكر", "أنثى"], horizontal=True)
            c3, c4 = st.columns(2)
            height = c3.number_input("الطول (سم)", 100, 220, 160)
            weight = c4.number_input("الوزن الحالي (كجم)", 30.0, 200.0, 70.0)
            target_weight = st.number_input("الوزن المستهدف (كجم)", 30.0, 200.0, 60.0)
            st.markdown("---")
            goals = st.multiselect("ما هي أهدافك؟", ["خسارة وزن", "زيادة عضل", "تحسين الصحة", "غير ذلك"])
            other_goal_text = st.text_input("توضيح الهدف الإضافي:") if "غير ذلك" in goals else ""
            
            st.markdown("---")
            btn_col1, btn_col2 = st.columns([2, 1])
            with btn_col1:
                if st.button("التالي: النشاط البدني ⬅️", use_container_width=True):
                    if name and phone:
                        st.session_state.patient_data.update({'name': name, 'phone': phone, 'gender': gender, 'height': height, 'weight': weight, 'target_weight': target_weight, 'goals': str(goals), 'other_goal': other_goal_text})
                        next_step(); st.rerun()
                    else: st.error("الرجاء كتابة الاسم ورقم الجوال.")
            with btn_col2:
                if st.button("🏠 إلغاء ورجوع", use_container_width=True):
                    restart(); st.rerun()

        # صفحة 2: النشاط
        elif st.session_state.step == 2:
            st.markdown("### ⚡ الخطوة 2: النشاط البدني")
            activity_level = st.radio("معدل النشاط اليومي:", ["قليل (عمل مكتبي)", "متوسط (مشي)", "عالي (تمارين مكثفة)"])
            gym_home = st.radio("أين تمارس نشاطك العالي؟", ["🏋️ نادي رياضي (Gym)", "🏠 تمرين منزلي"]) if "عالي" in activity_level else ""
            st.markdown("---")
            exercise_days = st.slider("عدد أيام التمرين أسبوعياً", 0, 7, 3)
            exercise_type = st.multiselect("نوع التمارين:", ["كارديو", "مقاومة", "مختلط", "لا يوجد"])
            
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("التالي: العادات الغذائية ⬅️"):
                    st.session_state.patient_data.update({'activity': activity_level, 'gym_home': gym_home, 'exercise_days': exercise_days, 'exercise_type': str(exercise_type)})
                    next_step(); st.rerun()
            with c2: 
                if st.button("رجوع"): prev_step(); st.rerun()

        # صفحة 3: التغذية
        elif st.session_state.step == 3:
            st.markdown("### 🍽️ الخطوة 3: العادات الغذائية والصحية")
            with st.form("new_pt_step3"):
                st.markdown("**العادات الغذائية:**")
                meals_count = st.radio("عدد الوجبات اليومية", ["وجبة واحدة", "وجبتين", "3 وجبات", "4 وجبات أو أكثر"], horizontal=True)
                fixed_time = st.radio("هل يوجد وقت محدد للوجبات؟", ["نعم", "لا"], horizontal=True)
                allergies = st.text_input("حساسية طعام؟ (اكتب لا إن لم يوجد)")
                dislikes = st.text_input("أطعمة لا تحبها:")
                st.divider()
                st.markdown("**💧 العادات الصحية:**")
                water = st.radio("معدل شرب الماء:", ["1 - 3 أكواب (قليل)", "4 - 7 أكواب (متوسط)", "8 أكواب أو أكثر (ممتاز)"])
                sleep = st.radio("معدل النوم:", ["أقل من 5 ساعات", "5-7 ساعات", "أكثر من 7 ساعات"])
                meds = st.text_area("مشاكل صحية أو أدوية؟")
                
                c1, c2 = st.columns([1,1])
                with c1: submit = st.form_submit_button("التالي: الروتين اليومي ⬅️")
                with c2: back = st.form_submit_button("رجوع")
                if back: prev_step(); st.rerun()
                if submit: 
                    st.session_state.patient_data.update({'meals_count': meals_count, 'fixed_time': fixed_time, 'allergies': allergies, 'dislikes': dislikes, 'water': water, 'sleep': sleep, 'meds': meds})
                    next_step(); st.rerun()

        # صفحة 4: الروتين
        elif st.session_state.step == 4:
            st.markdown("### 📝 الخطوة 4: وصف اليوم الكامل")
            st.info("اكتب بالتفصيل من الاستيقاظ للنوم.")
            with st.form("routine_form"):
                daily_routine = st.text_area("وصف اليوم:", height=300)
                notes = st.text_area("ملاحظات إضافية:")
                c1, c2 = st.columns([1,1])
                with c1: submit = st.form_submit_button("التالي: الدفع 💳")
                with c2: back = st.form_submit_button("رجوع")
                if back: prev_step(); st.rerun()
                if submit:
                    if daily_routine:
                        st.session_state.patient_data.update({'daily_routine': daily_routine, 'notes': notes})
                        next_step(); st.rerun()
                    else: st.error("الرجاء كتابة الروتين.")

        # صفحة 5: الدفع
        elif st.session_state.step == 5:
            st.markdown("### 💳 الخطوة الأخيرة: إتمام الاشتراك")
            st.info("قيمة الاشتراك: 200 ريال")
            st.markdown("""
            #### 🏦 التحويل البنكي
            **اسم البنك:** مصرف الراجحي
            **الآيبان:** `SA0000000000000000000000
            """)
            st.divider()
            uploaded_receipt = st.file_uploader("إرفاق إيصال التحويل (مطلوب):", type=['png', 'jpg', 'pdf'])
            payment_method = "تحويل بنكي"
            
            c1, c2 = st.columns([2, 1])
            with c1:
                if st.button("✅ تأكيد الدفع وإرسال الطلب", use_container_width=True):
                    if uploaded_receipt:
                        try:
                            sheet = connect_to_sheet()
                            if sheet:
                                try: current_headers = sheet.row_values(1)
                                except: current_headers = []

                                expected_headers = [
                                    'file_no', 'Name', 'Phone', 'Gender', 'Weight', 'Target', 'Hight', 
                                    'Age','diet_plan'
                                ]
                                
                                if not current_headers:
                                    sheet.append_row(expected_headers)
                                
                                new_file_num = str(random.randint(10000, 99999))
                                p = st.session_state.patient_data
                                
                                row = [
                                    new_file_num,
                                    p.get('name', ''),
                                    str(p.get('phone', '')),
                                    p.get('gender', ''),
                                    p.get('weight', ''),
                                    p.get('target_weight', ''), # This maps to Target in your sheet logic
                                    p.get('height', ''),
                                    p.get('age', ''),
                                    p.get('goals', ''),
                                    p.get('activity', ''),
                                    p.get('gym_home', ''),
                                    p.get('exercise_days', ''),
                                    p.get('exercise_type', ''),
                                    p.get('meals_count', ''),
                                    p.get('fixed_time', ''),
                                    p.get('allergies', ''),
                                    p.get('dislikes', ''),
                                    p.get('water', ''),
                                    p.get('sleep', ''),
                                    p.get('meds', ''),
                                    p.get('daily_routine', ''),
                                    p.get('notes', ''),
                                    payment_method,
                                    "FALSE",
                                    ""
                                ]
                                sheet.append_row(row)
                                st.session_state.new_file_number = new_file_num
                                next_step(); st.rerun()
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء الحفظ: {e}")
                    else: st.error("الرجاء إرفاق الإيصال.")
            with c2:
                if st.button("رجوع"): prev_step(); st.rerun()

        # صفحة 6: التهنئة
        elif st.session_state.step == 6:
            st.balloons()
            st.success("✅ تم استلام طلبك بنجاح!")
            st.markdown(f"### رقم ملفك الطبي: `{st.session_state.new_file_number}`")
            if st.button("العودة للرئيسية"): restart(); st.rerun()

    # ------------------------------------------------
    # (ب) مسار المراجع (دخول آمن)
    # ------------------------------------------------
    elif st.session_state.user_type == 'returning':
        if st.session_state.step == 1:
            st.markdown("### 🔐 دخول المشتركين")
            phone_input = st.text_input("رقم الجوال المسجل")
            
            c1, c2 = st.columns([2, 1])
            with c1:
                if st.button("دخول", use_container_width=True):
                    sheet = connect_to_sheet()
                    if sheet:
                        try:
                            all_values = sheet.get_all_values()
                            if len(all_values) > 1:
                                raw_headers = all_values[0]
                                rows = all_values[1:]
                                # تنظيف العناوين عند القراءة
                                headers = [str(h).strip().lower() for h in raw_headers]
                                # معالجة التكرار
                                final_headers = []
                                seen = {}
                                for h in headers:
                                    if h in seen:
                                        seen[h] += 1
                                        final_headers.append(f"{h}_{seen[h]}")
                                    else:
                                        seen[h] = 0
                                        final_headers.append(h)

                                df = pd.DataFrame(rows, columns=final_headers)
                                
                                phone_col_name = None
                                for col in df.columns:
                                    if "phone" in str(col):
                                        phone_col_name = col
                                        break
                                
                                if phone_col_name:
                                    clean_input = str(phone_input).strip().replace(" ", "")
                                    df['clean_phone'] = df[phone_col_name].astype(str).apply(lambda x: x.split('.')[0].strip().replace(" ", ""))
                                    
                                    user_record = df[
                                        (df['clean_phone'] == clean_input) | 
                                        (df['clean_phone'] == clean_input.lstrip('0')) | 
                                        (df['clean_phone'].str.lstrip('0') == clean_input.lstrip('0'))
                                    ]
                                    
                                    if not user_record.empty:
                                        user_dict = user_record.iloc[0].to_dict()
                                        st.session_state.patient_data = user_dict
                                        next_step(); st.rerun()
                                    else:
                                        st.error("رقم الجوال غير مسجل لدينا.")
                                else:
                                    st.error("خطأ: لم يتم العثور على الجوال.")
                        except Exception as e:
                            st.error(f"حدث خطأ فني: {e}")
            with c2:
                if st.button("🏠 رجوع", use_container_width=True): restart(); st.rerun()

        # لوحة المريض
        elif st.session_state.step == 2:
            user = st.session_state.patient_data
            name_display = user.get('name', 'مشترك')
            
            st.title(f"أهلاً بك {name_display} 👋")
            st.markdown("### 📥 جدولك الغذائي")
            
            sent_status = str(user.get('diet_plan_sent', 'FALSE'))
            is_sent = sent_status.upper().strip() == "TRUE"
            diet_link = user.get('diet_link', '')
            
            if is_sent:
                st.success("✅ تم إصدار جدولك الجديد!")
                if diet_link and diet_link.startswith("http"):
                    st.link_button("📄 اضغط هنا لتحميل/مشاهدة الجدول", diet_link)
                else:
                    st.info("الجدول جاهز! يرجى التواصل مع الأخصائية لاستلامه.")
            else:
                st.info("⏳ جاري تصميم جدولك... يرجى الانتظار (يستغرق 3 أيام عمل).")
            
            st.divider()
            st.subheader("📊 المتابعة الأسبوعية")
            if st.button("بدء المتابعة الأسبوعية ⬅️"): next_step(); st.rerun() 
            if st.button("خروج"): restart(); st.rerun()

        elif st.session_state.step == 3:
            st.markdown("### 📝 تسجيل قياسات الأسبوع")
            with st.form("update_w"):
                prev_w = st.session_state.patient_data.get('weight', 70)
                try: prev_w = float(prev_w)
                except: prev_w = 70.0
                st.metric("الوزن السابق", f"{prev_w} كجم")
                current_w = st.number_input("الوزن الحالي", 30.0, 200.0, prev_w)
                if st.form_submit_button("التالي ⬅️"):
                    st.session_state.patient_data['current_w'] = current_w
                    next_step(); st.rerun()

        elif st.session_state.step == 4:
            st.markdown("### 📊 تقييم الأداء")
            with st.form("eval_form"):
                st.radio("كيف كان النظام؟", ["سهل", "متوسط", "صعب"])
                st.slider("نسبة الالتزام %", 0, 100, 80)
                st.text_input("سبب عدم الالتزام:")
                st.multiselect("أعراض ظهرت:", ["دوخة", "خمول", "جوع", "لا يوجد"])
                if st.form_submit_button("إرسال التقرير 🚀"):
                    st.balloons()
                    st.success("تم إرسال التقرير!")
                    if st.button("عودة"): restart(); st.rerun()

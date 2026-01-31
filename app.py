import streamlit as st
import pandas as pd
import random
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- إعدادات الصفحة ---
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🩺")

# --- تنسيق CSS (نفس التنسيق الأصلي الذي أعجبك) ---
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

# دوال التنقل
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
    
    if access_code == "admin123": # كلمة المرور
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
                # معالجة العناوين
                raw_headers = all_values[0]
                rows = all_values[1:]
                # تنظيف العناوين لتوحيد التعامل
                headers = [str(h).strip().lower() for h in raw_headers]
                
                # إنشاء DataFrame
                # معالجة التكرار في العناوين إن وجد
                seen = {}
                final_headers = []
                for h in headers:
                    if h in seen: seen[h]+=1; final_headers.append(f"{h}_{seen[h]}")
                    else: seen[h]=0; final_headers.append(h)

                df = pd.DataFrame(rows, columns=final_headers)
                
                # التأكد من وجود الأعمدة المطلوبة
                if 'diet_plan' not in df.columns: df['diet_plan'] = ""
                if 'hidden_details' not in df.columns: df['hidden_details'] = ""

                st.markdown("### 📂 الملفات المسجلة")
                
                for index, pt in df.iterrows():
                    pt_name = pt.get('name', 'غير محدد')
                    pt_file = pt.get('file_no', '#')
                    diet_status = pt.get('diet_plan', '')
                    
                    # حالة الملف
                    icon = "✅" if len(str(diet_status)) > 5 else "🆕"
                    
                    with st.expander(f"{icon} ملف: {pt_name} (#{pt_file})", expanded=False):
                        # 1. عرض البيانات الأساسية (من أعمدة الإكسل)
                        c1, c2 = st.columns(2)
                        c1.info(f"**الهدف:** {pt.get('target', '-')}")
                        c2.warning(f"**الوزن:** {pt.get('weight', '-')} | **الطول:** {pt.get('height', '-')}")
                        
                        st.markdown("---")
                        # 2. عرض التفاصيل الكاملة (من العمود المخفي Hidden_Details)
                        st.markdown("##### 📝 تفاصيل المريض الكاملة:")
                        # هنا نعرض النص الطويل الذي دمجناه سابقاً
                        full_details = pt.get('hidden_details', 'لا توجد تفاصيل')
                        st.text_area("بيانات الاستبيان:", value=full_details, height=200, disabled=True, key=f"d_{pt_file}")
                        
                        st.markdown("---")
                        # 3. إرسال الجدول (حفظ الرابط في عمود diet_plan)
                        st.markdown("##### 📤 إرسال الجدول:")
                        with st.form(key=f"f_{pt_file}"):
                            link_input = st.text_input("رابط الجدول (PDF/Drive):", value=diet_status)
                            if st.form_submit_button("حفظ وإرسال ✅"):
                                try:
                                    cell = sheet.find(str(pt_file))
                                    if cell:
                                        # تحديث عمود diet_plan (رقم 9 حسب ترتيبك)
                                        # نبحث عن مكانه برمجياً للأمان
                                        if 'diet_plan' in headers:
                                            col_idx = headers.index('diet_plan') + 1
                                            sheet.update_cell(cell.row, col_idx, link_input)
                                            st.success("تم الحفظ!")
                                            st.rerun()
                                except Exception as e:
                                    st.error(f"خطأ: {e}")
            else:
                st.info("لا توجد بيانات.")
        except Exception as e:
            st.error(f"خطأ تقني: {e}")

# ==========================================
# 📱 المسار 2: واجهة المريض (نفس كودك الأصلي)
# ==========================================
else:
    # الشاشة الرئيسية
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

    # ------------------------------------------------
    # (أ) مسار المريض الجديد
    # ------------------------------------------------
    elif st.session_state.user_type == 'new':
        
        # صفحة 1: شخصي
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
            goals = st.multiselect("ما هي أهدافك؟", ["خسارة وزن", "زيادة عضل", "تحسين الصحة", "غير ذلك"])
            other_goal_text = st.text_input("توضيح الهدف الإضافي:") if "غير ذلك" in goals else ""
            
            if st.button("التالي: النشاط البدني ⬅️"):
                if name and phone:
                    st.session_state.patient_data.update({'name': name, 'phone': phone, 'gender': gender, 'height': height, 'weight': weight, 'target_weight': target_weight, 'age': age, 'goals': goals, 'other_goal': other_goal_text})
                    next_step(); st.rerun()
                else: st.error("الاسم ورقم الجوال مطلوبان.")

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
                    st.session_state.patient_data.update({'activity': activity_level, 'gym_home': gym_home, 'exercise_days': exercise_days, 'exercise_type': exercise_type})
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
            st.info("اكتب بالتفصيل الممل من الاستيقاظ للنوم.")
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

        # صفحة 5: الدفع والحفظ في قوقل شيت
        elif st.session_state.step == 5:
            st.markdown("### 💳 الخطوة الأخيرة: إتمام الاشتراك")
            st.info("المبلغ: 350 ر.س")
            st.markdown("""
            #### 🏦 التحويل البنكي
            **اسم البنك:** مصرف الراجحي
            **الآيبان:** `SA0000000000000000000000`
            **اسم المستفيد:** عيادة أثير
            """)
            st.divider()
            uploaded_receipt = st.file_uploader("إرفاق إيصال التحويل:", type=['png', 'jpg', 'pdf'])
            
            if st.button("تأكيد الدفع والتسجيل ✅"):
                if uploaded_receipt:
                    try:
                        sheet = connect_to_sheet()
                        if sheet:
                            # 1. تجهيز البيانات
                            p = st.session_state.patient_data
                            new_file_num = str(random.randint(10000, 99999))
                            
                            # 2. دمج التفاصيل الكثيرة في نص واحد (Hidden Details)
                            # هنا نجمع كل الحقول التي لا نريد لها أعمدة في الإكسل
                            hidden_details_text = f"""
                            الأهداف: {p.get('goals')} - {p.get('other_goal')}
                            النشاط: {p.get('activity')} ({p.get('gym_home')}) - {p.get('exercise_days')} أيام ({p.get('exercise_type')})
                            الوجبات: {p.get('meals_count')} (وقت ثابت: {p.get('fixed_time')})
                            الحساسية: {p.get('allergies')} | الممنوعات: {p.get('dislikes')}
                            الماء: {p.get('water')} | النوم: {p.get('sleep')}
                            مشاكل صحية: {p.get('meds')}
                            الروتين: {p.get('daily_routine')}
                            ملاحظات: {p.get('notes')}
                            """.strip()

                            # 3. تجهيز الصف (10 أعمدة فقط حسب طلبك)
                            # file_no | Name | Phone | Gender | Weight | Target | Height | Age | diet_plan | Hidden_Details
                            row = [
                                new_file_num,
                                p.get('name', ''),
                                str(p.get('phone', '')),
                                p.get('gender', ''),
                                p.get('weight', ''),
                                p.get('target_weight', ''), # Target
                                p.get('height', ''),
                                p.get('age', ''),
                                "", # diet_plan فارغ في البداية
                                hidden_details_text # كل التفاصيل هنا
                            ]
                            
                            sheet.append_row(row)
                            
                            st.session_state.new_file_number = new_file_num
                            next_step(); st.rerun()
                    except Exception as e:
                        st.error(f"خطأ في الحفظ: {e}")
                else: st.error("الرجاء إرفاق الإيصال.")

        # صفحة 6: التهنئة
        elif st.session_state.step == 6:
            gender_title = "يا بطل" if st.session_state.patient_data.get('gender') == "ذكر" else "يا بطلة"
            st.balloons()
            st.success("✅ تم الاشتراك وتوثيق البيانات بنجاح!")
            st.markdown(f"### رقم ملفك الطبي: `{st.session_state.new_file_number}`")
            if st.button("العودة للرئيسية"): restart(); st.rerun()

    # ------------------------------------------------
    # (ب) مسار المراجع
    # ------------------------------------------------
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
            
            diet_link = user.get('diet_plan', '')
            st.markdown("### 📥 جدولك الغذائي")
            
            if diet_link and len(str(diet_link)) > 5:
                st.success("✅ الجدول جاهز!")
                st.link_button("📄 فتح الجدول", diet_link)
            else:
                st.info("⏳ جاري التصميم...")
            
            st.divider()
            # هنا ممكن تضيفين باقي أزرار المتابعة الأسبوعية إذا أردتِ
            if st.button("خروج"): restart(); st.rerun()

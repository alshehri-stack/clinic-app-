import streamlit as st
import pandas as pd
import random
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- إعدادات الصفحة ---
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🩺")

# --- تنسيق CSS (لجعل التطبيق عربي وأنيق) ---
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
# 🔐 القائمة الجانبية (بوابة الأخصائية السرية)
# ==========================================
is_admin = False
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063823.png", width=50)
    st.markdown("### العيادة الإلكترونية")
    st.markdown("---")
    
    # الكلمة السرية للدخول كأخصائية
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
        # --- التعديل الجذري للقراءة الآمنة ---
        try:
            # نجلب كل القيم كقائمة بدلاً من سجلات (أكثر أماناً من الأخطاء)
            all_values = sheet.get_all_values()
            
            if len(all_values) > 1:
                # الصف الأول هو العناوين، والباقي بيانات
                headers = all_values[0]
                rows = all_values[1:]
                df = pd.DataFrame(rows, columns=headers)
                
                if not df.empty:
                    # تصفية المرضى الذين لم يتم إرسال الجدول لهم
                    if 'diet_plan_sent' not in df.columns:
                        df['diet_plan_sent'] = "FALSE"
                    
                    pending_patients = df[df['diet_plan_sent'].astype(str) != "TRUE"]
                    
                    tab1, tab2 = st.tabs(["🆕 طلبات بانتظار التصميم", "📂 أرشيف المرضى"])
                    
                    with tab1:
                        if not pending_patients.empty:
                            st.write(f"لديك ({len(pending_patients)}) مريض بانتظار استلام الجدول.")
                            
                            for index, pt in pending_patients.iterrows():
                                with st.expander(f"ملف: {pt['name']} (#{pt['file_no']})", expanded=True):
                                    c1, c2 = st.columns(2)
                                    c1.info(f"**الهدف:** {pt['goals']}")
                                    c2.warning(f"**الوزن:** {pt['weight']} كجم | **الطول:** {pt['height']} سم")
                                    
                                    st.markdown("---")
                                    st.write(f"**📱 الجوال:** {pt['phone']}")
                                    st.write(f"**🏋️ النشاط:** {pt['activity']} ({pt['gym_home']})")
                                    st.write(f"**🥗 العادات:** {pt['meals_count']} وجبات")
                                    
                                    if pt['allergies']: st.error(f"⚠️ حساسية: {pt['allergies']}")
                                    if pt['dislikes']: st.write(f"❌ لا يحب: {pt['dislikes']}")
                                    
                                    st.markdown("**📝 الروتين اليومي:**")
                                    st.text(pt['daily_routine'])
                                    st.markdown(f"**💳 طريقة الدفع:** {pt.get('payment_method', 'غير محدد')}")
                                    
                                    st.markdown("---")
                                    st.markdown("### 📤 إرسال الجدول الغذائي")
                                    st.info("اضغطي هنا لتغيير حالة الملف إلى 'تم الإرسال'")
                                    
                                    if st.button(f"✅ اعتماد وإرسال لـ {pt['name']}", key=f"send_{pt['file_no']}"):
                                        try:
                                            # نحدد رقم الصف الحقيقي في الشيت (index + 2)
                                            cell_row = index + 2
                                            # نبحث عن رقم عمود diet_plan_sent
                                            try:
                                                col_index = headers.index("diet_plan_sent") + 1
                                                sheet.update_cell(cell_row, col_index, "TRUE")
                                                st.success(f"تم تحديث حالة الملف للمريض {pt['name']} بنجاح!")
                                                st.rerun()
                                            except:
                                                st.error("لم يتم العثور على عمود diet_plan_sent في الإكسل")
                                        except Exception as e:
                                            st.error(f"حدث خطأ في التحديث: {e}")
                        else:
                            st.success("🎉 جميع الجداول تم إرسالها.")

                    with tab2:
                        st.dataframe(df, use_container_width=True)
            else:
                st.info("ملف الإكسل يحتوي على العناوين فقط، لا توجد بيانات.")
        except Exception as e:
            st.error(f"حدث خطأ أثناء قراءة البيانات: {e}")

# ==========================================
# 📱 المسار 2: واجهة المريض (التفصيلية القديمة)
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
            if st.button("📂 دخول المراجعين (متابعة / استلام جدول)", use_container_width=True):
                st.session_state.user_type = 'returning'; st.session_state.step = 1; st.rerun()

    # ------------------------------------------------
    # (أ) مسار المريض الجديد (نفس تصميمك المفضل)
    # ------------------------------------------------
    elif st.session_state.user_type == 'new':
        
        # صفحة 1: شخصي
        if st.session_state.step == 1:
            st.markdown("### 👤 الخطوة 1: المعلومات الشخصية والأهداف")
            name = st.text_input("الاسم الثلاثي")
            phone = st.text_input("رقم الجوال (مهم جداً للدخول لاحقاً)") 
            
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
                    st.session_state.patient_data.update({'name': name, 'phone': phone, 'gender': gender, 'height': height, 'weight': weight, 'target_weight': target_weight, 'goals': str(goals), 'other_goal': other_goal_text})
                    next_step(); st.rerun()
                else: st.error("الرجاء كتابة الاسم ورقم الجوال.")

        # صفحة 2: النشاط (تفصيلي)
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

        # صفحة 3: التغذية (تفصيلي)
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

        # صفحة 5: الدفع
        elif st.session_state.step == 5:
            st.markdown("### 💳 الخطوة الأخيرة: إتمام الاشتراك")
            st.info("قيمة الاشتراك: 350 ر.س")
            
            payment_method = st.radio("اختر طريقة الدفع:", [" Apple Pay", "🏦 تحويل بنكي"], horizontal=True)
            
            st.markdown("---")
            if payment_method == " Apple Pay":
                st.markdown("### **0500000000** (د. أثير)")
            else:
                st.markdown("### **IBAN: SA0000000000000000** (مصرف الراجحي)")
            st.markdown("---")

            uploaded_receipt = st.file_uploader("إرفاق الإيصال (مطلوب):", type=['png', 'jpg', 'pdf'])
            
            if st.button("تأكيد الدفع والتسجيل ✅"):
                if uploaded_receipt:
                    try:
                        sheet = connect_to_sheet()
                        if sheet:
                            # 1. التأكد من وجود العناوين في الشيت، إذا لا، نضيفها
                            # هذه خطوة احتياطية لمنع الأخطاء
                            current_headers = sheet.row_values(1)
                            expected_headers = [
                                'file_no', 'name', 'phone', 'age', 'gender', 'height', 'weight', 
                                'target_weight', 'goals', 'activity', 'gym_home', 'exercise_days', 
                                'exercise_type', 'meals_count', 'fixed_time', 'allergies', 'dislikes', 
                                'water', 'sleep', 'meds', 'daily_routine', 'notes', 'payment_method', 'diet_plan_sent'
                            ]
                            
                            if not current_headers:
                                sheet.append_row(expected_headers)
                            
                            # 2. تجهيز البيانات
                            new_file_num = str(random.randint(10000, 99999))
                            p = st.session_state.patient_data
                            
                            row = [
                                new_file_num,
                                p['name'],
                                p['phone'],
                                p.get('age', ''),
                                p.get('gender', ''),
                                p.get('height', ''),
                                p.get('weight', ''),
                                p.get('target_weight', ''),
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
                                "FALSE"
                            ]
                            
                            sheet.append_row(row)
                            
                            st.session_state.new_file_number = new_file_num
                            next_step(); st.rerun()
                            
                    except Exception as e:
                        st.error(f"حدث خطأ أثناء الحفظ: {e}")
                else:
                    st.error("الرجاء إرفاق الإيصال لإكمال التسجيل.")

        # صفحة 6: التهنئة
        elif st.session_state.step == 6:
            gender_title = "يا بطل" if st.session_state.patient_data.get('gender') == "ذكر" else "يا بطلة"
            st.balloons()
            st.success("✅ تم الاشتراك وتوثيق البيانات بنجاح!")
            st.markdown(f"""
            ### تهانينا {gender_title}! 🎉
            سيتم مراجعة الإيصال وتفعيل اشتراكك وإرسال الجدول خلال 3 أيام.
            
            **رقم ملفك الطبي:**
            # 📂 `{st.session_state.new_file_number}`
            """)
            st.warning("⚠️ احفظ رقم الملف، ولكن يمكنك الدخول لاحقاً برقم جوالك أيضاً.")
            if st.button("العودة للرئيسية"): restart(); st.rerun()

    # ------------------------------------------------
    # (ب) مسار المراجع (تم التعديل جذرياً لمنع الخطأ)
    # ------------------------------------------------
    elif st.session_state.user_type == 'returning':
        
        # دخول برقم الجوال
        if st.session_state.step == 1:
            st.markdown("### 🔐 دخول المشتركين")
            phone_input = st.text_input("رقم الجوال المسجل")
            if st.button("دخول"):
                sheet = connect_to_sheet()
                if sheet:
                    try:
                        # --- التعديل هنا: استخدام get_all_values بدلاً من get_all_records ---
                        all_values = sheet.get_all_values()
                        
                        # نتأكد أن فيه بيانات غير العناوين
                        if len(all_values) > 1:
                            headers = all_values[0] # الصف الأول عناوين
                            rows = all_values[1:]   # الباقي بيانات
                            
                            # إنشاء DataFrame آمن
                            df = pd.DataFrame(rows, columns=headers)
                            
                            # التأكد من أن عمود phone موجود
                            if 'phone' in df.columns:
                                # تحويل عمود الجوال لنص ومقارنته
                                df['phone'] = df['phone'].astype(str)
                                user_record = df[df['phone'] == phone_input]
                                
                                if not user_record.empty:
                                    # نجح الدخول
                                    st.session_state.patient_data = user_record.iloc[0].to_dict()
                                    next_step(); st.rerun()
                                else:
                                    st.error("رقم الجوال غير مسجل لدينا.")
                            else:
                                st.error("عذراً، يوجد مشكلة في تسمية الأعمدة في ملف الإكسل (تأكدي أن عمود الجوال اسمه phone).")
                        else:
                            st.warning("لا توجد بيانات مسجلة في النظام.")
                            
                    except Exception as e:
                        st.error(f"حدث خطأ فني: {e}")

        # لوحة تحكم المريض
        elif st.session_state.step == 2:
            user = st.session_state.patient_data
            st.title(f"أهلاً بك {user['name']} 👋")
            
            st.markdown("### 📥 جدولك الغذائي")
            
            # التحقق من حالة الإرسال
            is_sent = str(user.get('diet_plan_sent')).upper() == "TRUE"
            
            if is_sent:
                st.success("✅ تم إصدار جدولك الجديد!")
                st.info("تم إرسال الجدول إليك (أو يمكنك التواصل مع الأخصائية لاستلامه).")
            else:
                st.info("⏳ جاري تصميم جدولك... يرجى الانتظار (يستغرق 3 أيام عمل).")
            
            st.divider()
            
            st.subheader("📊 المتابعة الأسبوعية")
            st.write("هل انتهى أسبوعك وتريد تسجيل النتائج؟")
            
            if st.button("بدء المتابعة الأسبوعية ⬅️"):
                next_step(); st.rerun() 
            
            if st.button("خروج"): restart(); st.rerun()

        # أسئلة المتابعة
        elif st.session_state.step == 3:
            st.markdown("### 📝 تسجيل قياسات الأسبوع")
            with st.form("update_w"):
                col1, col2 = st.columns(2)
                # استخدام get مع قيمة افتراضية لتجنب الاخطاء اذا كان الحقل فارغ
                prev_w = st.session_state.patient_data.get('weight')
                if not prev_w: prev_w = 70.0 # قيمة افتراضية
                
                col1.metric("الوزن السابق", f"{prev_w} كجم")
                current_w = col2.number_input("الوزن الحالي", 30.0, 200.0, float(prev_w))
                submit = st.form_submit_button("التالي ⬅️")
                if submit:
                    st.session_state.patient_data['current_w'] = current_w
                    next_step(); st.rerun()

        elif st.session_state.step == 4:
            st.markdown("### 📊 تقييم الأداء")
            with st.form("eval_form"):
                diet_diff = st.radio("كيف كان النظام؟", ["سهل ومريح", "متوسط", "صعب جداً"])
                adherence = st.slider("نسبة الالتزام %", 0, 100, 80)
                fail_reason = st.text_input("سبب عدم الالتزام (إن وجد):")
                symptoms = st.multiselect("أعراض ظهرت:", ["دوخة", "خمول", "جوع شديد", "إمساك", "لا يوجد"])
                change_req = st.radio("ماذا تريد للأسبوع القادم؟", ["تغيير كامل", "تعديل بسيط", "استمرار نفس الجدول"])
                
                if st.form_submit_button("إرسال التقرير 🚀"):
                    st.balloons()
                    st.success("تم إرسال تقرير المتابعة للأخصائية بنجاح!")
                    if st.button("عودة"): restart(); st.rerun()
                
                if st.form_submit_button("إرسال التقرير 🚀"):
                    st.balloons()
                    st.success("تم إرسال تقرير المتابعة للأخصائية بنجاح!")
                    if st.button("عودة"): restart(); st.rerun()

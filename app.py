import streamlit as st
import datetime
import pandas as pd
import random
from datetime import datetime

# إعداد الصفحة
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🩺")

# --- محاكاة قاعدة البيانات (Database) ---
# هنا تتخزن ملفات المرضى وترتبط برقم الملف
if 'db_patients' not in st.session_state:
    st.session_state.db_patients = {} 

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
    
    # تصفية المرضى الذين ينتظرون الجدول (لم يتم إرسال الجدول لهم بعد)
    pending_patients = [p for p in st.session_state.db_patients.values() if not p.get('diet_plan_sent')]
    
    tab1, tab2 = st.tabs(["🆕 طلبات بانتظار التصميم", "📂 أرشيف المرضى"])
    
    with tab1:
        if pending_patients:
            st.write(f"لديك ({len(pending_patients)}) مريض بانتظار استلام الجدول.")
            
            for pt in pending_patients:
                # عرض تفاصيل المريض (نفس البيانات التفصيلية التي أدخلها)
                with st.expander(f"ملف: {pt['name']} (#{pt['file_no']})", expanded=True):
                    
                    c1, c2 = st.columns(2)
                    c1.info(f"**الهدف:** {', '.join(pt.get('goals', []))} - {pt.get('other_goal','')}")
                    c2.warning(f"**الوزن:** {pt.get('weight')} كجم | **الطول:** {pt.get('height')} سم")
                    
                    st.markdown("---")
                    st.write(f"**🏋️ النشاط:** {pt.get('activity')} ({pt.get('gym_home', '')})")
                    st.write(f"**🥗 العادات:** {pt.get('meals_count')} وجبات | وقت محدد: {pt.get('fixed_time')}")
                    st.write(f"**💧 الماء:** {pt.get('water')} | **😴 النوم:** {pt.get('sleep')}")
                    
                    if pt.get('allergies'): st.error(f"⚠️ حساسية: {pt['allergies']}")
                    if pt.get('dislikes'): st.write(f"❌ لا يحب: {pt['dislikes']}")
                    
                    st.markdown("**📝 الروتين اليومي:**")
                    st.text(pt.get('daily_routine', 'لا يوجد'))
                    
                    st.markdown("---")
                    st.markdown("### 📤 إرسال الجدول الغذائي")
                    st.write("بعد تصميم الجدول، ارفعيه هنا ليظهر للمريض:")
                    
                    # زر رفع الملف الخاص بهذا المريض
                    uploaded_file = st.file_uploader(f"رفع ملف PDF/صورة للمريض {pt['file_no']}", key=f"up_{pt['file_no']}")
                    
                    if st.button(f"✅ اعتماد وإرسال لـ {pt['name']}", key=f"send_{pt['file_no']}"):
                        if uploaded_file:
                            # حفظ الملف في "داتا" المريض
                            st.session_state.db_patients[pt['file_no']]['diet_plan_file'] = uploaded_file
                            st.session_state.db_patients[pt['file_no']]['diet_plan_sent'] = True
                            st.success(f"تم إرسال الجدول للمريض {pt['name']} بنجاح!")
                            st.rerun()
                        else:
                            st.error("الرجاء رفع الملف أولاً.")
        else:
            st.success("🎉 لا توجد طلبات معلقة! جميع الجداول تم إرسالها.")

    with tab2:
        st.write("قاعدة بيانات جميع المرضى المسجلين:")
        if st.session_state.db_patients:
            # عرض جدول سريع
            df = pd.DataFrame(st.session_state.db_patients.values())
            st.dataframe(df[['file_no', 'name', 'weight', 'gender', 'diet_plan_sent']], use_container_width=True)
        else:
            st.info("لا يوجد مرضى مسجلين حتى الآن.")

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
    # (أ) مسار المريض الجديد (النسخة التفصيلية كما طلبتِ)
    # ------------------------------------------------
    elif st.session_state.user_type == 'new':
        
        # صفحة 1: شخصي
        if st.session_state.step == 1:
            st.markdown("### 👤 الخطوة 1: المعلومات الشخصية والأهداف")
            name = st.text_input("الاسم الثلاثي")
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
                if name:
                    st.session_state.patient_data.update({'name': name, 'gender': gender, 'height': height, 'weight': weight, 'target_weight': target_weight, 'goals': goals, 'other_goal': other_goal_text})
                    next_step(); st.rerun()
                else: st.error("الرجاء كتابة الاسم.")

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
                    st.session_state.patient_data.update({'activity': activity_level, 'gym_home': gym_home, 'exercise_days': exercise_days, 'exercise_type': exercise_type})
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
            st.info("المبلغ: 350 ر.س")
            uploaded_receipt = st.file_uploader("إرفاق الإيصال:", type=['png', 'jpg', 'pdf'])
            if st.button("تأكيد الدفع والتسجيل ✅"):
                if uploaded_receipt:
                    # توليد رقم الملف وحفظ البيانات في قاعدة البيانات
                    new_file_num = str(random.randint(10000, 99999))
                    final_data = st.session_state.patient_data
                    final_data['file_no'] = new_file_num
                    final_data['receipt_img'] = uploaded_receipt
                    final_data['diet_plan_sent'] = False # لم يرسل الجدول بعد
                    
                    # حفظ في DB
                    st.session_state.db_patients[new_file_num] = final_data
                    
                    # حفظ رقم الملف للعرض
                    st.session_state.new_file_number = new_file_num
                    
                    next_step(); st.rerun()
                else: st.error("الرجاء إرفاق الإيصال.")

        # صفحة 6: التهنئة
        elif st.session_state.step == 6:
            gender_title = "يا بطل" if st.session_state.patient_data.get('gender') == "ذكر" else "يا بطلة"
            st.balloons()
            st.success("✅ تم الاشتراك وتوثيق البيانات بنجاح!")
            st.markdown(f"""
            ### تهانينا {gender_title}! 🎉
            سيتم إرسال الجدول خلال 3 أيام.
            
            **رقم ملفك الطبي:**
            # 📂 `{st.session_state.new_file_number}`
            """)
            st.warning("⚠️ احفظ هذا الرقم للدخول لاحقاً واستلام الجدول.")
            if st.button("العودة للرئيسية"): restart(); st.rerun()

    # ------------------------------------------------
    # (ب) مسار المراجع (استلام الجدول + المتابعة)
    # ------------------------------------------------
    elif st.session_state.user_type == 'returning':
        
        # دخول برقم الملف
        if st.session_state.step == 1:
            st.markdown("### 🔐 دخول المشتركين")
            file_no = st.text_input("رقم الملف الطبي")
            if st.button("دخول"):
                if file_no in st.session_state.db_patients:
                    # سحب بيانات المريض من قاعدة البيانات
                    st.session_state.patient_data = st.session_state.db_patients[file_no]
                    next_step(); st.rerun()
                else: st.error("رقم الملف غير صحيح.")

        # لوحة تحكم المريض (استلام الجدول + بدء المتابعة)
        elif st.session_state.step == 2:
            user = st.session_state.patient_data
            st.title(f"أهلاً بك {user['name']} 👋")
            
            # 1. قسم استلام الجدول (الجديد)
            st.markdown("### 📥 جدولك الغذائي")
            if user.get('diet_plan_sent'):
                st.success("✅ تم إصدار جدولك الجديد!")
                st.download_button(
                    label="📄 تحميل النظام الغذائي (اضغط هنا)",
                    data=user['diet_plan_file'],
                    file_name=f"Diet_Plan_{user['file_no']}.png",
                    mime="image/png"
                )
            else:
                st.info("⏳ جاري تصميم جدولك... يرجى الانتظار (يستغرق 3 أيام عمل).")
            
            st.divider()
            
            # 2. خيار المتابعة الأسبوعية
            st.subheader("📊 المتابعة الأسبوعية")
            st.write("هل انتهى أسبوعك وتريد تسجيل النتائج؟")
            
            if st.button("بدء المتابعة الأسبوعية ⬅️"):
                next_step(); st.rerun() # ينتقل لأسئلة المتابعة
            
            if st.button("خروج"): restart(); st.rerun()

        # أسئلة المتابعة (نفس النسخة السابقة)
        elif st.session_state.step == 3:
            st.markdown("### 📝 تسجيل قياسات الأسبوع")
            with st.form("update_w"):
                col1, col2 = st.columns(2)
                col1.metric("الوزن السابق", f"{st.session_state.patient_data['weight']} كجم")
                current_w = col2.number_input("الوزن الحالي", 30.0, 200.0, st.session_state.patient_data['weight'])
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

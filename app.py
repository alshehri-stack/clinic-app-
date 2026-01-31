import streamlit as st
import pandas as pd
import random
import base64
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
    .stTextInput > label, .stNumberInput > label, .stSelectbox > label, .stRadio > label, .stTextArea > label, .stFileUploader > label, .stMultiselect > label {
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
                # معالجة العناوين
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
                if 'diet_code' not in df.columns: df['diet_code'] = ""
                if 'details' not in df.columns: df['details'] = ""

                # --- الفرز: ملفات جديدة (بدون كود PDF) vs أرشيف (مع PDF) ---
                # نعتبر الملف مكتمل إذا كان عمود diet_code يحتوي على بيانات طويلة (Base64)
                df['is_completed'] = df['diet_code'].astype(str).str.len() > 50
                
                new_patients = df[~df['is_completed']]
                archived_patients = df[df['is_completed']]

                tab1, tab2 = st.tabs([f"🆕 مرضى جدد ({len(new_patients)})", "📂 الأرشيف والمكتملة"])
                
                # --- تبويب 1: المرضى الجدد ---
                with tab1:
                    if not new_patients.empty:
                        for index, pt in new_patients.iterrows():
                            pt_name = pt.get('name', 'غير محدد')
                            pt_file = pt.get('file_no', '---')
                            
                            with st.expander(f"ملف: {pt_name} (#{pt_file})", expanded=False):
                                # عرض البيانات
                                c1, c2 = st.columns(2)
                                c1.info(f"**الهدف:** {pt.get('target')}")
                                c2.warning(f"**الوزن:** {pt.get('weight')} | **الطول:** {pt.get('height')}")
                                
                                st.markdown("---")
                                st.markdown("##### 📝 التفاصيل:")
                                st.text_area("بيانات المريض:", value=pt.get('details'), height=150, disabled=True, key=f"d_{pt_file}")
                                
                                st.markdown("---")
                                st.markdown("### 📤 رفع النظام الغذائي (PDF)")
                                st.info("بمجرد رفع الملف، سينتقل المريض للأرشيف ويظهر الملف في حسابه.")
                                
                                with st.form(key=f"upload_{pt_file}"):
                                    diet_name = st.text_input("اسم النظام (مثلاً: لو كارب):", key=f"dn_{pt_file}")
                                    uploaded_pdf = st.file_uploader("ارفعي ملف الـ PDF هنا:", type=['pdf'], key=f"up_{pt_file}")
                                    
                                    if st.form_submit_button("حفظ وإرسال ✅"):
                                        if uploaded_pdf and diet_name:
                                            try:
                                                cell = sheet.find(str(pt_file))
                                                if cell:
                                                    # تحويل PDF إلى Base64
                                                    bytes_data = uploaded_pdf.getvalue()
                                                    b64_str = base64.b64encode(bytes_data).decode()
                                                    
                                                    # تحديث الاسم والكود
                                                    if 'diet_plan' in headers:
                                                        sheet.update_cell(cell.row, headers.index('diet_plan')+1, diet_name)
                                                    if 'diet_code' in headers:
                                                        sheet.update_cell(cell.row, headers.index('diet_code')+1, b64_str)
                                                    
                                                    st.success("تم الإرسال بنجاح! انتقل الملف للأرشيف.")
                                                    st.rerun()
                                            except Exception as e:
                                                st.error(f"خطأ: {e}")
                                        else:
                                            st.error("يرجى كتابة الاسم ورفع الملف.")
                    else:
                        st.success("🎉 لا توجد ملفات جديدة.")

                # --- تبويب 2: الأرشيف ---
                with tab2:
                    if not archived_patients.empty:
                        for index, pt in archived_patients.iterrows():
                            pt_name = pt.get('name', 'غير محدد')
                            pt_file = pt.get('file_no', '---')
                            
                            with st.expander(f"✅ {pt_name} (#{pt_file}) - مكتمل", expanded=False):
                                st.write(f"**النظام:** {pt.get('diet_plan')}")
                                st.write(f"**الجوال:** {pt.get('phone')}")
                                st.text_area("سجل المتابعة والتفاصيل:", value=pt.get('details'), height=200, disabled=True, key=f"arch_{pt_file}")
                    else:
                        st.info("الأرشيف فارغ.")

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
            
            # --- التعديل المطلوب: النشاط العالي فقط يظهر الخيارات ---
            activity = st.radio("مستوى النشاط", ["خامل", "متوسط", "عالي"])
            gym = "غير محدد"
            if activity == "عالي":
                gym = st.radio("مكان التمرين", ["منزل", "نادي رياضي"])
            
            days = st.slider("أيام التمرين", 0, 7, 3)
            # --- التعديل المطلوب: أنواع التمارين ---
            type_ex = st.multiselect("نوع التمرين", ["كارديو", "مقاومة", "مختلط", "لا يوجد"])
            
            c_back, c_next = st.columns([1, 2])
            with c_next:
                if st.button("التالي ⬅️", use_container_width=True):
                    st.session_state.patient_data.update({'activity': activity, 'gym': gym, 'days': days, 'type_ex': str(type_ex)})
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
            routine = st.text_area("اوصف يومك بالتفصيل:", height=200)
            notes = st.text_area("ملاحظات إضافية:")
            c_back, c_next = st.columns([1, 2])
            with c_next:
                if st.button("التالي: الدفع ⬅️", use_container_width=True):
                    st.session_state.patient_data.update({'routine': routine, 'notes': notes})
                    next_step(); st.rerun()
            with c_back:
                if st.button("رجوع"): prev_step(); st.rerun()

        elif st.session_state.step == 5:
            st.markdown("### 💳 الخطوة الأخيرة: الدفع")
            # --- التعديل المطلوب: السعر 200 ورسالة الراجحي ---
            st.info("قيمة الاشتراك: 200 ريال")
            st.markdown("""
            #### 🏦 التحويل البنكي
            **اسم البنك:** مصرف الراجحي
            **الآيبان:** `SA0000000000000000000000`
            **اسم المستفيد:** عيادة أثير
            """)
            st.divider()
            uploaded = st.file_uploader("إرفاق الإيصال (صورة/PDF)", type=['png', 'jpg', 'pdf'])
            
            c_back, c_next = st.columns([1, 2])
            with c_next:
                if st.button("✅ تأكيد الاشتراك"):
                    if uploaded:
                        try:
                            sheet = connect_to_sheet()
                            if sheet:
                                p = st.session_state.patient_data
                                new_file = str(random.randint(10000, 99999))
                                
                                # تجميع التفاصيل
                                details_blob = f"""
                                [تسجيل جديد: {datetime.now().strftime('%Y-%m-%d')}]
                                الأهداف: {p.get('goals')}
                                النشاط: {p.get('activity')} ({p.get('gym')}) - {p.get('days')} أيام
                                نوع التمرين: {p.get('type_ex')}
                                التغذية: {p.get('meals')} وجبات (وقت ثابت: {p.get('time')})
                                الحساسية: {p.get('allergies')} | الممنوعات: {p.get('dislikes')}
                                الروتين: {p.get('routine')}
                                ملاحظات: {p.get('notes')}
                                """.strip()

                                # الحفظ في الإكسل
                                row = [
                                    new_file,
                                    p.get('name'),
                                    str(p.get('phone')),
                                    p.get('gender'),
                                    p.get('weight'),
                                    p.get('target_weight'),
                                    p.get('height'),
                                    p.get('age'),
                                    "",             # diet_plan
                                    "",             # diet_code
                                    details_blob    # Details
                                ]
                                
                                sheet.append_row(row)
                                st.session_state.new_file_number = new_file
                                next_step(); st.rerun()
                        except Exception as e:
                            st.error(f"خطأ: {e}")
                    else:
                        st.error("الرجاء إرفاق الإيصال.")
            with c_back:
                if st.button("رجوع"): prev_step(); st.rerun()

        elif st.session_state.step == 6:
            st.balloons()
            # --- التعديل المطلوب: رسالة يا بطل/بطلة ---
            gender_msg = "يا بطل" if st.session_state.patient_data.get('gender') == "ذكر" else "يا بطلة"
            st.success(f"تم الاشتراك {gender_msg}! 🎉")
            st.info("سيتم إرسال نظامك الغذائي خلال 3 أيام عمل في ملفك الشخصي.")
            st.markdown(f"### رقم ملفك: `{st.session_state.new_file_number}`")
            if st.button("عودة للرئيسية"): restart(); st.rerun()

    # --- دخول المراجعين (الواجهة الجديدة) ---
    elif st.session_state.user_type == 'returning':
        if st.session_state.step == 1:
            st.markdown("### 🔐 دخول المراجعين")
            phone = st.text_input("أدخل رقم الجوال:")
            c1, c2 = st.columns([2, 1])
            with c1:
                if st.button("دخول", use_container_width=True):
                    sheet = connect_to_sheet()
                    if sheet:
                        try:
                            vals = sheet.get_all_values()
                            if len(vals) > 1:
                                headers = [str(h).strip().lower() for h in vals[0]]
                                # معالجة تكرار الأعمدة
                                seen = {}; final_headers = []
                                for h in headers:
                                    if h in seen: seen[h]+=1; final_headers.append(f"{h}_{seen[h]}")
                                    else: seen[h]=0; final_headers.append(h)

                                df = pd.DataFrame(vals[1:], columns=final_headers)
                                phone_col = next((c for c in df.columns if 'phone' in c), None)
                                
                                if phone_col:
                                    clean_in = str(phone).strip()
                                    df['clean'] = df[phone_col].astype(str).apply(lambda x: x.split('.')[0].strip())
                                    user = df[(df['clean'] == clean_in) | (df['clean'] == clean_in.lstrip('0'))]
                                    
                                    if not user.empty:
                                        st.session_state.patient_data = user.iloc[0].to_dict()
                                        next_step(); st.rerun()
                                    else: st.error("رقم الجوال غير مسجل.")
                        except Exception as e: st.error(f"خطأ: {e}")
            with c2:
                if st.button("رجوع"): restart(); st.rerun()

        elif st.session_state.step == 2:
            user = st.session_state.patient_data
            pt_file = user.get('file_no', '')
            st.title(f"أهلاً {user.get('name')} 👋")
            
            # --- قسم الجدول الغذائي ---
            st.markdown("### 📥 جدولك الغذائي")
            diet_code = user.get('diet_code', '')
            diet_name = user.get('diet_plan', '')
            
            if diet_code and len(str(diet_code)) > 50:
                st.success(f"نظامك الحالي: **{diet_name}**")
                try:
                    b64_bytes = base64.b64decode(diet_code)
                    st.download_button(
                        label="📄 تحميل النظام الغذائي (PDF)",
                        data=b64_bytes,
                        file_name="My_Diet_Plan.pdf",
                        mime="application/pdf"
                    )
                except:
                    st.error("ملف الدايت تالف.")
            else:
                st.info("⏳ جاري إعداد جدولك، سيظهر هنا خلال 3 أيام.")
            
            st.divider()
            
            # --- قسم المتابعة الأسبوعية الجديد ---
            st.subheader("📊 المتابعة الأسبوعية")
            with st.expander("اضغط هنا لتعبئة نموذج المتابعة"):
                with st.form("weekly_form"):
                    q1 = st.radio("كيف كان النظام؟", ["سهل", "متوسط", "صعب"])
                    q2 = st.text_area("هل توجد ملاحظات؟")
                    q3 = st.text_input("هل شعرت بأعراض؟ (دوخة، خمول..)")
                    q4 = st.radio("هل تريد تغيير الجدول؟", ["لا، استمرار", "تعديل بسيط", "تغيير كامل"])
                    q5 = st.slider("نسبة الالتزام %", 0, 100, 80)
                    q6 = st.text_input("إذا كان الالتزام أقل من 100%، ما السبب؟")
                    
                    if st.form_submit_button("إرسال التقرير 🚀"):
                        try:
                            sheet = connect_to_sheet()
                            if sheet:
                                cell = sheet.find(str(pt_file))
                                if cell:
                                    # ندمج الملاحظات الجديدة مع القديمة في عمود Details
                                    # نحتاج معرفة رقم عمود Details
                                    headers = sheet.row_values(1)
                                    headers_lower = [str(h).strip().lower() for h in headers]
                                    if 'details' in headers_lower:
                                        col_idx = headers_lower.index('details') + 1
                                        old_details = sheet.cell(cell.row, col_idx).value
                                        
                                        new_report = f"""
                                        \n--- [متابعة: {datetime.now().strftime('%Y-%m-%d')}] ---
                                        النظام: {q1} | التزام: {q5}%
                                        تغيير: {q4}
                                        أعراض: {q3} | السبب: {q6}
                                        ملاحظات: {q2}
                                        """
                                        
                                        sheet.update_cell(cell.row, col_idx, old_details + new_report)
                                        st.success("تم إرسال التقرير للأخصائية بنجاح!")
                                    else:
                                        st.error("لم يتم العثور على خانة التفاصيل.")
                        except Exception as e:
                            st.error(f"خطأ في الارسال: {e}")

            if st.button("تسجيل خروج"): restart(); st.rerun()

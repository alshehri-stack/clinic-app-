import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- إعدادات الصفحة ---
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🩺")

# --- تنسيق CSS (التصميم الذي تحبينه) ---
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
    /* تحسين شكل التبويبات */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 10px;
        color: #000;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #009688;
        color: #fff;
    }
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
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063823.png", width=60)
    st.markdown("### العيادة الإلكترونية")
    st.markdown("---")
    
    access_code = st.text_input("الدخول الإداري 🔒", type="password", placeholder="الرمز السري")
    
    if access_code == "admin123":
        is_admin = True
        st.success("مرحباً دكتورة! 👋")
    else:
        st.caption("للمساعدة والاستفسار: تواصل معنا")

# ==========================================
# 👩‍⚕️ المسار 1: واجهة الأخصائية (التصميم المقسم)
# ==========================================
if is_admin:
    st.title("👩‍⚕️ لوحة إدارة العيادة والملفات")
    
    sheet = connect_to_sheet()
    if sheet:
        try:
            all_values = sheet.get_all_values()
            
            if len(all_values) > 1:
                # 1. تجهيز البيانات
                raw_headers = all_values[0]
                rows = all_values[1:]
                headers = [str(h).strip().lower() for h in raw_headers]
                
                # منع تكرار الأعمدة
                seen = {}; final_headers = []
                for h in headers:
                    if h in seen: seen[h]+=1; final_headers.append(f"{h}_{seen[h]}")
                    else: seen[h]=0; final_headers.append(h)

                df = pd.DataFrame(rows, columns=final_headers)
                
                # التأكد من وجود الأعمدة
                if 'diet_plan' not in df.columns: df['diet_plan'] = ""
                if 'details' not in df.columns: df['details'] = ""

                # 2. تقسيم الملفات (جديد vs أرشيف)
                # نعتبر الملف "جديد" إذا كان عمود diet_plan فارغاً أو قصيراً جداً
                df['is_completed'] = df['diet_plan'].astype(str).str.len() > 5
                
                new_requests = df[~df['is_completed']]
                archive_files = df[df['is_completed']]
                
                # 3. عرض التبويبات
                tab1, tab2 = st.tabs([f"🆕 طلبات جديدة ({len(new_requests)})", "📂 أرشيف الملفات"])
                
                # --- تبويب الطلبات الجديدة ---
                with tab1:
                    if not new_requests.empty:
                        for index, pt in new_requests.iterrows():
                            pt_name = pt.get('name', 'غير معروف')
                            pt_phone = pt.get('phone', '-')
                            pt_file = pt.get('file_no', '#')
                            
                            with st.expander(f"ملف: {pt_name} (جوال: {pt_phone})", expanded=False):
                                # عرض البيانات الأساسية
                                c1, c2, c3 = st.columns(3)
                                c1.info(f"**الوزن:** {pt.get('weight')} | **الطول:** {pt.get('height')}")
                                c2.warning(f"**الهدف:** {pt.get('target')}")
                                c3.write(f"**العمر:** {pt.get('age')} | **الجنس:** {pt.get('gender')}")
                                
                                st.markdown("---")
                                
                                # عرض التفاصيل (التي كانت مختفية)
                                st.markdown("##### 📝 تفاصيل الاستبيان الكاملة:")
                                details_text = pt.get('details', '')
                                if details_text:
                                    st.text_area("إجابات المريض:", value=details_text, height=250, disabled=True, key=f"det_{pt_file}")
                                else:
                                    st.warning("لا توجد تفاصيل إضافية مسجلة لهذا المريض.")
                                
                                st.markdown("---")
                                
                                # خانة الإرسال
                                st.markdown("##### 📤 إرسال الجدول:")
                                st.caption("ملاحظة: لضمان وصول الملف، يفضل رفع الجدول على (Google Drive) أو (Canva) ولصق الرابط هنا.")
                                
                                with st.form(key=f"send_form_{pt_file}"):
                                    diet_link_input = st.text_input("رابط الجدول الغذائي:", placeholder="https://...")
                                    
                                    if st.form_submit_button("إرسال واعتماد ✅"):
                                        if diet_link_input:
                                            try:
                                                cell = sheet.find(str(pt_file))
                                                if cell:
                                                    # تحديث عمود diet_plan بالرابط
                                                    if 'diet_plan' in headers:
                                                        col_idx = headers.index('diet_plan') + 1
                                                        sheet.update_cell(cell.row, col_idx, diet_link_input)
                                                        st.success(f"تم إرسال الجدول للمريض {pt_name} بنجاح!")
                                                        time.sleep(1)
                                                        st.rerun()
                                            except Exception as e:
                                                st.error(f"حدث خطأ: {e}")
                                        else:
                                            st.error("الرجاء وضع الرابط للإرسال.")
                    else:
                        st.success("🎉 رائع! لا توجد طلبات معلقة.")

                # --- تبويب الأرشيف ---
                with tab2:
                    st.dataframe(archive_files, use_container_width=True)

            else:
                st.info("قاعدة البيانات فارغة حالياً.")
        except Exception as e:
            st.error(f"خطأ في قراءة البيانات: {e}")

# ==========================================
# 📱 المسار 2: واجهة المريض
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
            weight = c4.number_input("الوزن الحالي (كجم)", 30.0, 200.0, 70.0)
            target = st.number_input("الوزن المستهدف", 30.0, 200.0, 60.0)
            st.markdown("---")
            goals = st.multiselect("الأهداف", ["خسارة وزن", "زيادة عضل", "صحة عامة"])
            
            c_back, c_next = st.columns([1, 2])
            with c_next:
                if st.button("التالي ⬅️", use_container_width=True):
                    if name and phone:
                        st.session_state.patient_data.update({'name': name, 'phone': phone, 'age': age, 'gender': gender, 'height': height, 'weight': weight, 'target': target, 'goals': goals})
                        next_step(); st.rerun()
                    else: st.error("الاسم والجوال مطلوبان")
            with c_back:
                if st.button("🏠 إلغاء", use_container_width=True): restart(); st.rerun()

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
                                p = st.session_state.patient_data
                                new_file = str(random.randint(10000, 99999))
                                
                                # --- تجميع كل الإجابات في نص واحد للعمود المخفي ---
                                hidden_blob = f"""
                                - الأهداف: {p.get('goals')}
                                - النشاط: {p.get('activity')} ({p.get('gym')})
                                - أيام التمرين: {p.get('days')} أيام ({p.get('type_ex')})
                                - الوجبات: {p.get('meals')} (وقت ثابت: {p.get('time')})
                                - حساسية: {p.get('allergies')}
                                - لا يحب: {p.get('dislikes')}
                                - الروتين اليومي: {p.get('routine')}
                                - ملاحظات: {p.get('notes')}
                                """.strip()

                                # الحفظ حسب ترتيب الأعمدة المطلوب
                                # file_no | Name | Phone | Gender | Weight | Target | Height | Age | diet_plan | Details
                                row = [
                                    new_file,
                                    p.get('name'),
                                    str(p.get('phone')),
                                    p.get('gender'),
                                    p.get('weight'),
                                    p.get('target'),
                                    p.get('height'),
                                    p.get('age'),
                                    "",             # diet_plan (فارغ)
                                    hidden_blob     # Details (كل التفاصيل هنا)
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
                                    user = df[(df['clean'] == clean_in) | (df['clean'] == clean_in.lstrip('0'))]
                                    
                                    if not user.empty:
                                        st.session_state.patient_data = user.iloc[0].to_dict()
                                        next_step(); st.rerun()
                                    else: st.error("رقم الجوال غير مسجل.")
                                else: st.error("خطأ في قراءة ملف الإكسل")
                        except Exception as e: st.error(f"خطأ: {e}")
            with c2:
                if st.button("رجوع", use_container_width=True): restart(); st.rerun()

        elif st.session_state.step == 2:
            user = st.session_state.patient_data
            st.title(f"أهلاً {user.get('name')} 👋")
            
            # التحقق من وجود رابط الدايت
            diet_link = user.get('diet_plan', '')
            
            st.markdown("### 📥 حاله الجدول")
            
            if diet_link and len(str(diet_link)) > 5:
                # إذا كان الجدول مرسلاً
                st.success("✅ تم إصدار جدولك الجديد!")
                st.markdown(f"**[📄 اضغط هنا لتحميل/عرض الجدول]({diet_link})**")
            else:
                # إذا لم يرسل بعد
                st.info("⏳ يتم الآن تصميم نظامك الغذائي (3 أيام عمل)...")
            
            st.divider()
            
            # إذا الجدول وصل، نظهر زر المتابعة
            if diet_link and len(str(diet_link)) > 5:
                st.subheader("📊 المتابعة الأسبوعية")
                if st.button("تسجيل الوزن الجديد ⬅️"): next_step(); st.rerun()
            
            if st.button("خروج"): restart(); st.rerun()

        elif st.session_state.step == 3:
            st.markdown("### 📝 تسجيل قياسات الأسبوع")
            with st.form("update_w"):
                prev_w = st.session_state.patient_data.get('weight', 70)
                try: prev_w = float(prev_w)
                except: prev_w = 70.0
                st.metric("الوزن السابق", f"{prev_w} كجم")
                current_w = st.number_input("الوزن الحالي", 30.0, 200.0, prev_w)
                if st.form_submit_button("إرسال التحديث"):
                    st.success("تم تحديث بياناتك!")
                    time.sleep(1)
                    restart(); st.rerun()

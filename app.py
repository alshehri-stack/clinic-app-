import streamlit as st
import pandas as pd
import random
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- إعدادات الصفحة ---
st.set_page_config(page_title="العيادة الإلكترونية", layout="wide", page_icon="🏥")

# --- دالة الاتصال بقوقل شيت ---
def connect_to_sheet():
    # استخدام المعلومات من Secrets
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["service_account"], scope)
    client = gspread.authorize(creds)
    # فتح الملف باسمه
    sheet = client.open("Clinic_Data").sheet1
    return sheet

# --- الواجهة الرئيسية ---
st.title("مرحباً بك في العيادة الإلكترونية 🩺")
st.markdown("---")

# تقسيم الصفحة لعمودين
col1, col2 = st.columns(2)

with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063823.png", width=150)
    st.header("تسجيل مريض جديد")
    
    with st.form("patient_form"):
        name = st.text_input("الاسم الثلاثي")
        phone = st.text_input("رقم الجوال")
        age = st.number_input("العمر", min_value=1, max_value=120, step=1)
        gender = st.selectbox("الجنس", ["أنثى", "ذكر"])
        weight = st.number_input("الوزن الحالي (كجم)", min_value=10.0, format="%.1f")
        target = st.text_input("الهدف الصحي (مثلاً: إنقاص وزن، لياقة)")
        
        # زر الإرسال
        submitted = st.form_submit_button("تسجيل البيانات ✅")

        if submitted:
            if name and phone:
                try:
                    # 1. الاتصال بالشيت
                    sheet = connect_to_sheet()
                    
                    # 2. تجهيز البيانات بنفس ترتيب أعمدة الإكسل حقك
                    # الترتيب: file_no | Name | Age | Gender | Weight | Target | Status | phone
                    file_no = str(random.randint(1000, 9999))
                    status = "جديد"
                    
                    row = [file_no, name, age, gender, weight, target, status, phone]
                    
                    # 3. إضافة الصف للملف
                    sheet.append_row(row)
                    
                    st.success(f"تم التسجيل بنجاح! تم حفظ البيانات في النظام السحابي. رقم الملف: {file_no}")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"حدث خطأ في الاتصال بقاعدة البيانات: {e}")
            else:
                st.warning("الرجاء تعبئة الاسم ورقم الجوال على الأقل.")

with col2:
    st.info("💡 معلومات العيادة")
    st.write("ساعات العمل: 4 عصراً - 10 مساءً")
    st.write("الموقع: جدة")

import streamlit as st
import sqlite3
import os
from datetime import datetime, timedelta
import urllib.request

try:
    my_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    st.info(f"🌐 **Исходящий IP сервера Render:** `{my_ip}`")
except Exception as e:
    print(f"Could not fetch outbound IP: {e}")

st.set_page_config(page_title="NOC Quick SMS Tester (SMPP)", page_icon="⚡", layout="centered")

st.title("⚡ NOC Quick SMS Tester (SMPP)")
st.caption("Отправка автотестов через локальную БД SQLite")

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'sms_queue.db')

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id TEXT,
            phone_number TEXT,
            message TEXT,
            send_at REAL,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def add_task(sender_id, phone, message, send_at):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO queue (sender_id, phone_number, message, send_at) VALUES (?, ?, ?, ?)",
        (sender_id, phone, message, send_at)
    )
    conn.commit()
    conn.close()

if "default_time" not in st.session_state:
    st.session_state.default_time = (datetime.now() + timedelta(minutes=2)).time()

with st.form("sms_test_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        sender_id = st.text_input("Sender ID / Alpha", value="TEST")
        phone_number = st.text_input("Номер телефона (E.164)", value="37441824400")
        repeat_count = st.number_input("Количество отправки на один номер", min_value=1, max_value=20, value=1)

    with col2:
        schedule_date = st.date_input("Дата отправки", value=datetime.now().date(), key="schedule_date_input")
        schedule_time = st.time_input("Время отправки", value=st.session_state.default_time, key="schedule_time_input")

    message_text = st.text_area("Текст SMS", value="Test OTP message for DLR verification", height=100)
    
    submit_button = st.form_submit_button("🚀 Запланировать тесты", type="primary", use_container_width=True)

if submit_button:
    if not phone_number.strip():
        st.error("Пожалуйста, укажите номер телефона!")
    elif not message_text.strip():
        st.error("Текст SMS не может быть пустым!")
    else:
        scheduled_dt = datetime.combine(schedule_date, schedule_time)
        scheduled_ts = scheduled_dt.timestamp()

        for _ in range(repeat_count):
            add_task(sender_id.strip(), phone_number.strip(), message_text.strip(), scheduled_ts)

        st.success(f"✅ {repeat_count} тестов успешно зафиксировано в БД на {scheduled_dt.strftime('%d.%m.%Y %H:%M:%S')}!")

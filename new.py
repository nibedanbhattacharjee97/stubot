import streamlit as st
import pandas as pd
import sqlite3
from gtts import gTTS
from googletrans import Translator
import os
import io
import base64
from PIL import Image
import urllib.parse

# --- DB Setup ---
db_name = 'new_respons.db'
conn = sqlite3.connect(db_name, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS respons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Mobile_Number TEXT NOT NULL
    )
''')
conn.commit()

# --- Header ---
if os.path.exists("Anudip_care_Update_photo.jpg"):
    st.image("Anudip_care_Update_photo.jpg")
st.markdown('<h1 style="color: teal; font-size: 26px;">Anudip Student Bot</h1>', unsafe_allow_html=True)

# --- Input Fields ---
col1, col2, col3 = st.columns([3, 3, 1.2])
with col1:
    name = st.text_input("Name")
with col2:
    mobile = st.text_input("CMIS Register Mobile Number", max_chars=10)
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.button("✅ Submit")

# --- Save to DB ---
if submitted:
    if name and mobile:
        cursor.execute("INSERT INTO respons (Name, Mobile_Number) VALUES (?, ?)", (name, mobile))
        conn.commit()
        st.success(f"Submitted for {name} with Mobile Number {mobile}")
    else:
        st.error("Please fill in both Name and Mobile Number.")

# --- Question/Answer Section (Always Visible) ---
st.write("---")
st.markdown('<h1 style="color: teal; font-size: 26px;">Ask Your Question & Get Answer in Your Own Language</h1>', unsafe_allow_html=True)

if os.path.exists("questions_answers.xlsx"):
    try:
        answered_df = pd.read_excel("questions_answers.xlsx")
        selected_question = st.selectbox("Select a question", answered_df['question'])

        if selected_question:
            answer_row = answered_df[answered_df['question'] == selected_question].iloc[0]

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Question:** {answer_row['question']}")
                st.write(f"**Answer:** {answer_row['answer']}")

            with col2:
                if pd.notna(answer_row['picpath']) and os.path.exists(answer_row['picpath']):
                    try:
                        image = Image.open(answer_row['picpath'])
                        st.image(image, caption="Related Image", use_column_width=True)
                    except Exception as e:
                        st.warning(f"Image error: {e}")

            # --- Language and Audio ---
            st.markdown('<h1 style="color: teal;font-size: 26px;">Select Your Language</h1>', unsafe_allow_html=True)
            language_options = {
                "English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te",
                "Marathi": "mr", "Kannada": "kn", "Gujarati": "gu", "Malayalam": "ml",
                "Punjabi": "pa", "Urdu": "ur"
            }
            selected_language = st.selectbox("Choose language", list(language_options.keys()))
            lang_code = language_options[selected_language]

            translator = Translator()
            if selected_language != "English":
                translated_q = translator.translate(answer_row['question'], dest=lang_code).text
                translated_a = translator.translate(answer_row['answer'], dest=lang_code).text
            else:
                translated_q = answer_row['question']
                translated_a = answer_row['answer']

            st.write(f"**Translated Question ({selected_language}):** {translated_q}")
            st.write(f"**Translated Answer ({selected_language}):** {translated_a}")

            # Audio
            text_to_speak = f"Question: {translated_q}. Answer: {translated_a}"
            tts = gTTS(text=text_to_speak, lang=lang_code)
            audio_path = "question_answer_audio.mp3"
            tts.save(audio_path)
            st.audio(audio_path, format="audio/mp3")

    except Exception as e:
        st.error(f"Error loading data: {e}")
else:
    st.error("Missing 'questions_answers.xlsx' file.")

# --- WhatsApp Support ---
st.write("---")
st.markdown('<div style="text-align: center;"><h1 style="color: teal; font-size: 26px;">Contact Us via WhatsApp</h1></div>', unsafe_allow_html=True)
whatsapp_number = "8373069599"
whatsapp_message = "Hi There! Please ask your question here. I am available from 10:30 AM to 5:30 PM."
encoded_message = urllib.parse.quote(whatsapp_message)

if os.path.exists("whatsapp_logo.png"):
    with open("whatsapp_logo.png", "rb") as img:
        encoded_image = base64.b64encode(img.read()).decode()
    st.markdown(f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{encoded_image}" width="50" />
            <p style="font-size: 16px;">WhatsApp In English</p>
            <a href="https://api.whatsapp.com/send?phone=91{whatsapp_number}&text={encoded_message}" target="_blank">
                <button style="background-color:#25D366;color:white;padding:10px 20px;border:none;border-radius:5px;font-size:16px;">
                    Chat on WhatsApp
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)
else:
    st.warning("WhatsApp logo not found.")

st.write("---")
st.markdown('<h1 style="color: teal;font-size: 26px;">Chat Timing - 10:30 AM - 5:30 PM (On Official Days)</h1>', unsafe_allow_html=True)

# --- Download Data Section ---
st.write("---")
st.markdown('<h1 style="color: teal;font-size: 26px;">Download Data</h1>', unsafe_allow_html=True)
password = st.text_input("Enter Password", type="password")

if st.button("Download Data"):
    if password == "monitaring_stu_bot@1234":
        df = pd.read_sql("SELECT * FROM respons", conn)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Answers')
        buffer.seek(0)
        st.download_button(
            label="📥 Download answers data as Excel",
            data=buffer,
            file_name="answers_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Incorrect password. Please try again.")

# --- Review Link ---
st.markdown("[🌟 Click Here To Give A Review](https://www.google.com/search?q=Anudip)", unsafe_allow_html=True)

# --- Close DB ---
conn.close()

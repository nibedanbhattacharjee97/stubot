import streamlit as st
import pandas as pd
import sqlite3
from gtts import gTTS
from googletrans import Translator
import os
import io
import base64
from PIL import Image

# Database setup
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

# App Header
st.image("Anudip_care_Update_photo.jpg")
st.markdown('<h1 style="color: teal; font-size: 26px;">Anudip Student Bot</h1>', unsafe_allow_html=True)

# --- Input Form ---
st.markdown("### Enter Your Details")
with st.form("entry_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        name = st.text_input("Name")
    with col2:
        mobile_number = st.text_input("CMIS Register Mobile Number (10 digits)", max_chars=10)
    with col3:
        submitted = st.form_submit_button("Submit")

    if submitted:
        if not name or not mobile_number:
            st.error("Both Name and Mobile Number are required.")
        elif len(mobile_number) != 10 or not mobile_number.isdigit():
            st.error("Please enter a valid 10-digit mobile number.")
        else:
            cursor.execute("INSERT INTO respons (Name, Mobile_Number) VALUES (?, ?)", (name, mobile_number))
            conn.commit()
            st.success("Your information has been successfully recorded!")

# --- Ask Your Question Section ---
st.write("---")
st.markdown('<h1 style="color: teal; font-size: 26px;">Ask Your Question & Get Answer in Your Own Language</h1>', unsafe_allow_html=True)

# Load answered questions
answered_df = pd.read_excel("questions_answers.xlsx")
selected_answered_question = st.selectbox("Select a question", answered_df['question'])
answered_row = answered_df[answered_df['question'] == selected_answered_question].iloc[0]

# Display Q&A
col1, col2 = st.columns(2)
with col1:
    st.write(f"**Question:** {answered_row['question']}")
    st.write(f"**Answer:** {answered_row['answer']}")

with col2:
    if pd.notna(answered_row['picpath']) and os.path.exists(answered_row['picpath']):
        try:
            image = Image.open(answered_row['picpath'])
            st.image(image, caption="Related Image", use_column_width=True)
        except Exception as e:
            st.warning(f"Error loading image: {e}")

# --- Language Translation & Audio ---
st.markdown('<h1 style="color: teal;font-size: 26px;">Select Your Language</h1>', unsafe_allow_html=True)
language_options = {
    "English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te", 
    "Marathi": "mr", "Kannada": "kn", "Gujarati": "gu", "Malayalam": "ml", 
    "Punjabi": "pa", "Urdu": "ur"
}
selected_language = st.selectbox("Choose language", list(language_options.keys()))

translator = Translator()
lang_code = language_options[selected_language]

if selected_language != "English":
    translated_q = translator.translate(answered_row['question'], dest=lang_code).text
    translated_a = translator.translate(answered_row['answer'], dest=lang_code).text
else:
    translated_q = answered_row['question']
    translated_a = answered_row['answer']

st.write(f"**Translated Question ({selected_language}):** {translated_q}")
st.write(f"**Translated Answer ({selected_language}):** {translated_a}")

text_to_speak = f"Question: {translated_q}. Answer: {translated_a}"
tts = gTTS(text_to_speak, lang=lang_code)
audio_path = 'question_answer_audio.mp3'
tts.save(audio_path)
st.audio(audio_path, format='audio/mp3')

# --- WhatsApp Section ---
st.write("---")
st.markdown('<div style="text-align: center;"><h1 style="color: teal; font-size: 26px;">Contact Us via WhatsApp</h1></div>', unsafe_allow_html=True)

whatsapp_number = "9147394695"
whatsapp_message = "Hi There! Please ask your question here. I am available from 10:30 AM to 5:30 PM."
whatsapp_logo = "whatsapp_logo.png"

if os.path.exists(whatsapp_logo):
    with open(whatsapp_logo, "rb") as img:
        encoded_image = base64.b64encode(img.read()).decode()
    st.markdown(f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{encoded_image}" width="50" alt="WhatsApp Logo"/>
            <p style="font-size: 16px;">WhatsApp For English</p>
            <a href="https://api.whatsapp.com/send?phone=91{whatsapp_number}&text={whatsapp_message}" target="_blank">
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

# --- Password-protected Download Section ---
st.write("---")
st.markdown('<h1 style="color: teal;font-size: 26px;">Download Data</h1>', unsafe_allow_html=True)
password = st.text_input("Enter Password", type="password")

def fetch_data_from_db():
    return pd.read_sql("SELECT * FROM respons", conn)

if st.button("Download Data"):
    if password == "monitaring_stu_bot@1234":
        df = fetch_data_from_db()
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Answers')
        buffer.seek(0)
        st.download_button(
            label="Download answers data as Excel",
            data=buffer,
            file_name="answers_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Incorrect password. Please try again.")

# --- Review Link ---
st.markdown("[Click Here To Give A Review](https://www.google.com/search?q=Anudip)", unsafe_allow_html=True)

# Close DB
conn.close()

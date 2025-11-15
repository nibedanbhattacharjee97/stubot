import streamlit as st
import pandas as pd
import sqlite3
import os
import io
import base64
import urllib.parse
from PIL import Image

# NEW & STABLE LIBRARIES
from deep_translator import GoogleTranslator
import pyttsx3

# ===========================
#      DATABASE SETUP
# ===========================
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

# ===========================
#        APP HEADER
# ===========================
if os.path.exists("Anudip_care_Update_photo.jpg"):
    st.image("Anudip_care_Update_photo.jpg")

st.markdown('<h1 style="color: teal; font-size: 26px;">Anudip Student Bot</h1>', unsafe_allow_html=True)

# ===========================
#      INPUT FORM
# ===========================
col1, col2, col3 = st.columns([3, 3, 1.2])

with col1:
    name = st.text_input("Name")

with col2:
    mobile = st.text_input("CMIS Register Mobile Number", max_chars=10)

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.button("✅ Submit")

# Save Data
if submitted:
    if name and mobile:
        cursor.execute("INSERT INTO respons (Name, Mobile_Number) VALUES (?, ?)", (name, mobile))
        conn.commit()
        st.success(f"Submitted for {name} with Mobile Number {mobile}")
    else:
        st.error("Please fill in both Name and Mobile Number.")

# ===========================
#       Q&A SECTION
# ===========================
st.write("---")
st.markdown('<h1 style="color: teal; font-size: 26px;">Ask Your Question & Get Answer in Your Own Language</h1>', unsafe_allow_html=True)

if os.path.exists("questions_answers.xlsx"):

    try:
        df = pd.read_excel("questions_answers.xlsx")
        selected_question = st.selectbox("Select a question", df["question"])

        if selected_question:
            row = df[df["question"] == selected_question].iloc[0]

            colA, colB = st.columns(2)

            with colA:
                st.write("**Question:**", row["question"])
                st.write("**Answer:**", row["answer"])

            with colB:
                if pd.notna(row['picpath']) and os.path.exists(row['picpath']):
                    try:
                        st.image(Image.open(row['picpath']), caption="Related Image", use_column_width=True)
                    except:
                        st.warning("Image could not be displayed.")

            # ===================================
            #      LANGUAGE TRANSLATION
            # ===================================
            st.markdown('<h1 style="color: teal;font-size: 26px;">Select Your Language</h1>', unsafe_allow_html=True)

            language_options = {
                "English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta",
                "Telugu": "te", "Marathi": "mr", "Kannada": "kn",
                "Gujarati": "gu", "Malayalam": "ml", "Punjabi": "pa", "Urdu": "ur"
            }

            selected_language = st.selectbox("Choose language:", list(language_options.keys()))
            lang_code = language_options[selected_language]

            # Translation
            try:
                if selected_language != "English":
                    translated_q = GoogleTranslator(source="auto", target=lang_code).translate(row["question"])
                    translated_a = GoogleTranslator(source="auto", target=lang_code).translate(row["answer"])
                else:
                    translated_q = row["question"]
                    translated_a = row["answer"]

            except Exception as e:
                st.warning(f"Translation failed: {e}")
                translated_q = row["question"]
                translated_a = row["answer"]

            st.write(f"**Translated Question ({selected_language}):** {translated_q}")
            st.write(f"**Translated Answer ({selected_language}):** {translated_a}")

            # ===================================
            #          FULL AUDIO (WAV)
            # ===================================
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 160)

                audio_text = f"Question: {translated_q}. Answer: {translated_a}"
                audio_file = "qa_audio.wav"   # WAV (full audio, no cut)

                engine.save_to_file(audio_text, audio_file)
                engine.runAndWait()

                st.audio(audio_file, format="audio/wav")

            except Exception as e:
                st.warning(f"Audio generation failed: {e}")

    except Exception as e:
        st.error(f"Error loading questions_answers.xlsx: {e}")

else:
    st.error("Missing 'questions_answers.xlsx' file.")

# ===========================
#     WHATSAPP SUPPORT
# ===========================
st.write("---")
st.markdown(
    '<div style="text-align: center;"><h1 style="color: teal; font-size: 26px;">Contact Us via WhatsApp</h1></div>',
    unsafe_allow_html=True
)

whatsapp_number = "8373069599"
message = urllib.parse.quote("Hi There! Please ask your question here. I am available from 10:30 AM to 5:30 PM.")

if os.path.exists("whatsapp_logo.png"):
    with open("whatsapp_logo.png", "rb") as img:
        img_b64 = base64.b64encode(img.read()).decode()

    st.markdown(f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{img_b64}" width="50" />
            <p style="font-size: 16px;">WhatsApp In English</p>
            <a href="https://api.whatsapp.com/send?phone=91{whatsapp_number}&text={message}" target="_blank">
                <button style="background-color:#25D366;color:white;padding:10px 20px;border:none;border-radius:5px;font-size:16px;">
                    Chat on WhatsApp
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)
else:
    st.warning("WhatsApp logo not found.")

# ===========================
#          DOWNLOAD DATA
# ===========================
st.write("---")
st.markdown('<h1 style="color: teal;font-size: 26px;">Download Data</h1>', unsafe_allow_html=True)

password = st.text_input("Enter Password", type="password")

if st.button("Download Data"):
    if password == "monitaring_stu_bot@1234":
        df = pd.read_sql("SELECT * FROM respons", conn)
        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Answers")

        buffer.seek(0)

        st.download_button(
            label="📥 Download answers data as Excel",
            data=buffer,
            file_name="answers_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Incorrect password!")

# ===========================
#        REVIEW LINK
# ===========================
st.markdown("[🌟 Click Here To Give A Review](https://www.google.com/search?q=Anudip)", unsafe_allow_html=True)

# Close DB
conn.close()

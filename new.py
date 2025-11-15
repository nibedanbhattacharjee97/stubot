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

# -----------------------------------------------------------------------------------
# CONFIGURATION AND INITIALIZATION
# -----------------------------------------------------------------------------------

# Initialize session state for audio caching
if 'audio_cache' not in st.session_state:
    st.session_state.audio_cache = {}

# OPTIONAL DATABASE (for Admin download only)
DB_NAME = 'new_respons.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS respons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT,
        Mobile_Number TEXT
    )
''')
conn.commit()

# -----------------------------------------------------------------------------------
# HEADER & TITLE
# -----------------------------------------------------------------------------------
if os.path.exists("Anudip_care_Update_photo.jpg"):
    st.image("Anudip_care_Update_photo.jpg")

st.markdown('<h1 style="color: teal; font-size: 28px;">Anudip Student Bot</h1>', unsafe_allow_html=True)
st.success("Welcome to Anudip Student Bot! Ask questions in your own language.")

# -----------------------------------------------------------------------------------
# MAIN QUESTION–ANSWER SECTION
# -----------------------------------------------------------------------------------
st.write("---")

st.markdown('<h3 style="color: teal; font-size: 24px;">Ask Your Question & Get Answer in Your Own Language</h3>', 
             unsafe_allow_html=True)

if os.path.exists("questions_answers.xlsx"):
    try:
        qa_df = pd.read_excel("questions_answers.xlsx")

        selected_question = st.selectbox("Select Your Question:", qa_df["question"])

        if selected_question:
            row = qa_df[qa_df["question"] == selected_question].iloc[0]

            col1, col2 = st.columns(2)

            with col1:
                st.write(f"### Question: {row['question']}")
                st.write(f"### Answer: {row['answer']}")

            with col2:
                if pd.notna(row["picpath"]) and os.path.exists(row["picpath"]):
                    try:
                        img = Image.open(row["picpath"])
                        st.image(img, caption="Related Image", use_column_width=True)
                    except Exception as e:
                        st.warning(f"Image Error: {e}")

            # -------------------------------
            # TRANSLATION
            # -------------------------------
            st.write("---")

            st.markdown('<h3 style="color: teal; font-size: 24px;">Select Your Language</h3>',
                        unsafe_allow_html=True)

            languages = {
                "English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta",
                "Telugu": "te", "Marathi": "mr", "Kannada": "kn", "Gujarati": "gu",
                "Malayalam": "ml", "Punjabi": "pa", "Urdu": "ur"
            }

            selected_language = st.selectbox("Choose Language", list(languages.keys()))
            lang_code = languages[selected_language]

            translator = Translator()

            if selected_language != "English":
                translated_q = translator.translate(row["question"], dest=lang_code).text
                translated_a = translator.translate(row["answer"], dest=lang_code).text
            else:
                translated_q = row["question"]
                translated_a = row["answer"]

            st.write(f"**Translated Question:** {translated_q}")
            st.write(f"**Translated Answer:** {translated_a}")

            # -------------------------------
            # AUDIO GENERATION WITH CACHING
            # -------------------------------
            
            # 1. Define unique key and text for audio
            audio_key = f"{selected_question}_{lang_code}"
            text_audio = f"Question: {translated_q}. Answer: {translated_a}"

            if audio_key in st.session_state.audio_cache:
                # 2. Use cached audio data if available
                st.info("Playing cached audio.")
                st.audio(st.session_state.audio_cache[audio_key], format="audio/mp3")
            else:
                # 3. Generate new audio if not in cache
                try:
                    st.info(f"Generating audio for {selected_language}...")
                    
                    # Use BytesIO to create audio in memory, avoiding disk I/O and saving the file
                    audio_fp = io.BytesIO()
                    tts = gTTS(text=text_audio, lang=lang_code)
                    tts.write_to_fp(audio_fp)
                    
                    # Get audio bytes for caching and playback
                    audio_fp.seek(0)
                    audio_bytes = audio_fp.read()
                    
                    # Cache the raw bytes in session state
                    st.session_state.audio_cache[audio_key] = audio_bytes
                    
                    # Play the audio
                    st.audio(audio_bytes, format="audio/mp3")
                    
                except Exception as e:
                    # Catch the 429 error specifically
                    st.error(f"Audio Error: {e}. If this is a 'Too Many Requests' error, please wait 30 seconds and try again, or select a cached language/question.")

    except Exception as e:
        st.error(f"Error Reading Excel: {e}")

else:
    st.error("❌ 'questions_answers.xlsx' not found! Please ensure it is in the same directory.")

# -----------------------------------------------------------------------------------
# WHATSAPP SUPPORT
# -----------------------------------------------------------------------------------
st.write("---")
st.markdown('<h1 style="color: teal; text-align:center; font-size: 26px;">Contact Us on WhatsApp</h1>', 
            unsafe_allow_html=True)

whatsapp_number = "9147394695"
whatsapp_msg = "Hi! Please ask your question. I am available from 10:30 AM - 5:30 PM."
encoded_msg = urllib.parse.quote(whatsapp_msg)

if os.path.exists("whatsapp_logo.png"):
    with open("whatsapp_logo.png", "rb") as img_file:
        encoded_img = base64.b64encode(img_file.read()).decode()

    st.markdown(f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{encoded_img}" width="60" />
            <p style="font-size: 16px;">Chat on WhatsApp</p>
            <a href="https://api.whatsapp.com/send?phone=91{whatsapp_number}&text={encoded_msg}" target="_blank">
                <button style="background-color:#25D366;color:white;padding:10px 25px;border:none;border-radius:5px;font-size:16px;">
                    Open Chat
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)
else:
    st.warning("WhatsApp logo is missing!")

st.write("---")
st.markdown('<h3 style="color: teal;">Chat Timing: 10:30 AM - 5:30 PM (Mon–Fri)</h3>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------------
# ADMIN DOWNLOAD PANEL
# -----------------------------------------------------------------------------------
st.write("---")
st.markdown('<h1 style="color: teal; font-size: 26px;">Admin Panel – Download Data</h1>', unsafe_allow_html=True)

admin_pass = st.text_input("Enter Admin Password", type="password")

if st.button("Download Excel"):
    if admin_pass == "monitaring_stu_bot@1234":
        df = pd.read_sql("SELECT * FROM respons", conn)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Users")

        buffer.seek(0)

        st.download_button(
            label="📥 Download Excel File",
            data=buffer,
            file_name="user_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("❌ Wrong Password")

# -----------------------------------------------------------------------------------
# END
# -----------------------------------------------------------------------------------
conn.close()
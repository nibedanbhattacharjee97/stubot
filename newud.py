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
DB_NAME = 'new_respons.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS respons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Mobile_Number TEXT NOT NULL UNIQUE
    )
''')
conn.commit()

# --- Session State Initialization ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_mobile" not in st.session_state:
    st.session_state.user_mobile = ""
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

# --- Header Image ---
if os.path.exists("Anudip_care_Update_photo.jpg"):
    st.image("Anudip_care_Update_photo.jpg")

# --- Title ---
st.markdown('<h1 style="color: teal; font-size: 26px;">Anudip Student Bot</h1>', unsafe_allow_html=True)

# --- Authentication Section (below PNG) ---
if not st.session_state.logged_in:
    auth_tab = st.radio("🔐 Choose Action", ["Login", "Sign Up"], horizontal=True)

    if auth_tab == "Sign Up":
        st.subheader("📝 Sign Up")
        name = st.text_input("Enter Your Name")
        mobile = st.text_input("Enter Mobile Number", max_chars=10)
        if st.button("Register"):
            if name and mobile:
                try:
                    cursor.execute("INSERT INTO respons (Name, Mobile_Number) VALUES (?, ?)", (name, mobile))
                    conn.commit()
                    st.success("✅ Registration successful. Now go to 'Login'.")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ This number is already registered. Please login.")
            else:
                st.error("❌ Please fill in both name and mobile number.")

    elif auth_tab == "Login":
        st.subheader("🔑 Login")
        mobile = st.text_input("Enter Registered Mobile Number", max_chars=10)
        if st.button("Login"):
            cursor.execute("SELECT * FROM respons WHERE Mobile_Number=?", (mobile,))
            user = cursor.fetchone()
            if user:
                st.success(f"✅ Welcome {user[1]}!")
                st.session_state.logged_in = True
                st.session_state.user_mobile = user[2]
                st.session_state.user_name = user[1]
            else:
                st.error("❌ Mobile number not found. Please Sign Up first.")

# --- Main App After Login ---
if st.session_state.logged_in:
    st.success(f"✅ Welcome {st.session_state.user_name}!")

    # --- Q&A Section ---
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

                # --- Translation and Audio ---
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

                text_to_speak = f"Question: {translated_q}. Answer: {translated_a}"
                tts = gTTS(text=text_to_speak, lang=lang_code)
                audio_path = "question_answer_audio.mp3"
                tts.save(audio_path)
                st.audio(audio_path, format="audio/mp3")

        except Exception as e:
            st.error(f"Error loading questions: {e}")
    else:
        st.error("❌ 'questions_answers.xlsx' file not found.")

    # --- WhatsApp Section ---
    st.write("---")
    st.markdown('<div style="text-align: center;"><h1 style="color: teal; font-size: 26px;">Contact Us via WhatsApp</h1></div>', unsafe_allow_html=True)
    whatsapp_number = "9147394695"
    whatsapp_message = "Hi There! Please ask your question here. I am available from 10:30 AM to 5:30 PM."
    encoded_message = urllib.parse.quote(whatsapp_message)

    if os.path.exists("whatsapp_logo.png"):
        with open("whatsapp_logo.png", "rb") as img:
            encoded_image = base64.b64encode(img.read()).decode()
        st.markdown(f"""
            <div style="text-align: center;">
                <img src="data:image/png;base64,{encoded_image}" width="50" />
                <p style="font-size: 16px;">WhatsApp For English</p>
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

    # --- Admin Data Download ---
    st.write("---")
    st.markdown('<h1 style="color: teal;font-size: 26px;">Download Data (Admin Only)</h1>', unsafe_allow_html=True)
    password = st.text_input("Enter Admin Password", type="password")
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
            st.error("❌ Incorrect password. Access denied.")

    # --- Review Link ---
    st.markdown("[🌟 Click Here To Give A Review](https://www.google.com/search?q=anudip+foundation&sca_esv=cca5566734bdcf74&ei=vd1baJGLJ9Pb1e8PjJWPsQQ&ved=0ahUKEwjR3fuhvIyOAxXTbfUHHYzKI0YQ4dUDCBA&uact=5&oq=anudip+foundation&gs_lp=Egxnd3Mtd2l6LXNlcnAiEWFudWRpcCBmb3VuZGF0aW9uMhQQLhiABBiRAhixAxjRAxjHARiKBTILEC4YgAQYxwEYrwEyCxAAGIAEGJECGIoFMgUQABiABDILEAAYgAQYkQIYigUyCxAuGIAEGMcBGK8BMgUQABiABDIFEAAYgAQyCxAuGIAEGMcBGK8BMgsQLhiABBjHARivATIjEC4YgAQYkQIYsQMY0QMYxwEYigUYlwUY3AQY3gQY4ATYAQFIrEJQ4AdYmjZwAngBkAEAmAHZAaAB7heqAQYwLjE1LjK4AQPIAQD4AQGYAhKgApcXwgIKEAAYsAMY1gQYR8ICBhAAGBYYHsICBxAuGIAEGA3CAgcQABiABBgNwgIGEAAYDRgewgIWEC4YgAQYDRiXBRjcBBjeBBjfBNgBAcICAhAmwgIOEC4YgAQYsQMY0QMYxwHCAg4QLhiABBjHARiOBRivAcICGhAuGIAEGMcBGK8BGJcFGNwEGN4EGOAE2AEBwgIdEC4YgAQYsQMY0QMYxwEYlwUY3AQY3gQY4ATYAQGYAwCIBgGQBgi6BgYIARABGBSSBwYyLjE0LjKgB7DFArIHBjAuMTQuMrgHjRfCBwYwLjIuMTbIB04&sclient=gws-wiz-serp&lqi=ChFhbnVkaXAgZm91bmRhdGlvbiIDiAEBSInbn5rmgICACFojEAAQARgAGAEiEWFudWRpcCBmb3VuZGF0aW9uKgYIAhAAEAGSAR1ub25fZ292ZXJubWVudGFsX29yZ2FuaXphdGlvbqoBYAoNL2cvMTFqMzBiaDRjOBABKhUiEWFudWRpcCBmb3VuZGF0aW9uKAAyHxABIhuQrAFaefgXCYqtny9KrVZJfZTN_g8hohcwzSEyFRACIhFhbnVkaXAgZm91bmRhdGlvbg#lkt=LocalPoiReviews&rlimm=6232895590333594138&lrd=0x3a0275c462a37a3b:0x567fb1841feeba1a,3,,,,)", unsafe_allow_html=True)

# --- Close DB ---
conn.close()

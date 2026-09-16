import datetime
import os
import io
import base64
import urllib.parse
import streamlit as st
import pandas as pd
from gtts import gTTS
from deep_translator import GoogleTranslator
from PIL import Image

# --- Google Sheets Setup ---
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

st.set_page_config(page_title="Anudip Student Bot", layout="centered")


@st.cache_resource
def get_gspread_client():
    """
    Authenticates and caches the core gspread engine.
    """
    try:
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            toml_data = st.secrets["connections"]["gsheets"]
            credentials_dict = {
                "type": toml_data.get("type", "service_account"),
                "project_id": toml_data.get("project_id"),
                "private_key_id": toml_data.get("private_key_id"),
                "private_key": toml_data.get("private_key").replace("\\n", "\n") if toml_data.get("private_key") else None,
                "client_email": toml_data.get("client_email"),
                "client_id": toml_data.get("client_id"),
                "auth_uri": toml_data.get("auth_uri"),
                "token_uri": toml_data.get("token_uri"),
                "auth_provider_x509_cert_url": toml_data.get("auth_provider_x509_cert_url"),
                "client_x509_cert_url": toml_data.get("client_x509_cert_url")
            }
            creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        elif "gcp_service_account" in st.secrets:
            sheet_creds = dict(st.secrets["gcp_service_account"])
            if "private_key" in sheet_creds:
                sheet_creds["private_key"] = sheet_creds["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(sheet_creds, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)

        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Failed to authenticate with Google Sheets API: {e}")
        return None


# ---------------- USER TYPE CONFIG ----------------
# Two separate Google Sheets + two separate Q&A files, one per user type.
USER_CONFIG = {
    "new": {
        "label": "🧑‍🎓 I Have Come To Enroll (New Student)",
        "spreadsheet_name": "Responce_table_For_new_User",
        "worksheet_name": "Sheet1",
        "questions_file": "questions_answers_for_new_student.xlsx",
        "collect_state": False,
    },
    "existing": {
        "label": "🎓 I Am An Existing Student",
        "spreadsheet_name": "Responce Table",
        "worksheet_name": "data",
        "questions_file": "questions_answers.xlsx",
        "collect_state": True,
    },
}


# --- SPEED OPTIMIZATION: CACHE FOR 30 MINUTES (1800 SECONDS) ---
@st.cache_data(ttl=1800)
def get_cached_spreadsheet_records(spreadsheet_name, worksheet_name):
    """
    Fetches and caches sheet data for 30 minutes to eliminate network buffering.
    """
    gc = get_gspread_client()
    if gc is None:
        return []
    try:
        spreadsheet = gc.open(spreadsheet_name)
        sheet = spreadsheet.worksheet(worksheet_name)
        return sheet.get_all_records()
    except Exception:
        return []


def get_target_worksheet_live(spreadsheet_name, worksheet_name):
    """
    Used only for quick, un-cached write operations when appending new rows.
    """
    gc = get_gspread_client()
    if gc is None:
        return None
    try:
        spreadsheet = gc.open(spreadsheet_name)
        return spreadsheet.worksheet(worksheet_name)
    except Exception as e:
        st.error(f"Error accessing Google Sheet: {e}")
        return None


# ---------------- SESSION STATE INIT ----------------
if "user_type" not in st.session_state:
    st.session_state.user_type = None


# ---------------- START / LANDING PAGE ----------------
def show_start_page():
    if os.path.exists("Anudip_care_Update_photo.jpg"):
        st.image("Anudip_care_Update_photo.jpg")

    st.markdown(
        '<h1 style="color: teal; font-size: 28px; text-align:center;">Welcome To Anudip Student Bot</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center; font-size:18px;">Please tell us who you are to continue</p>',
        unsafe_allow_html=True,
    )

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(USER_CONFIG["new"]["label"], use_container_width=True):
            st.session_state.user_type = "new"
            st.rerun()
    with col2:
        if st.button(USER_CONFIG["existing"]["label"], use_container_width=True):
            st.session_state.user_type = "existing"
            st.rerun()


if st.session_state.user_type is None:
    show_start_page()
    st.stop()

# ---------------- MAIN APP (runs only after a choice is made) ----------------
config = USER_CONFIG[st.session_state.user_type]

top_left, top_right = st.columns([5, 1])
with top_right:
    if st.button("⬅ Change"):
        st.session_state.user_type = None
        st.rerun()

if os.path.exists("Anudip_care_Update_photo.jpg"):
    st.image("Anudip_care_Update_photo.jpg")
st.markdown('<h1 style="color: teal; font-size: 26px;">Anudip Student Bot</h1>', unsafe_allow_html=True)
st.caption(f"You selected: **{config['label']}**")

# --- Input Fields ---
if config["collect_state"]:
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name")
    with col2:
        mobile = st.text_input("CMIS Register Mobile Number", max_chars=10)

    col3, col4 = st.columns(2)
    with col3:
        state = st.text_input("State")
    with col4:
        student_id = st.text_input("Student ID")

    submitted = st.button("✅ Submit")
else:
    col1, col2, col3 = st.columns([3, 3, 1.2])
    with col1:
        name = st.text_input("Name")
    with col2:
        mobile = st.text_input("CMIS Register Mobile Number", max_chars=10)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.button("✅ Submit")
    state = ""
    student_id = ""

# --- Save to Google Sheet ---
if submitted:
    # Existing students must also provide State and Student ID
    required_ok = name and mobile and (not config["collect_state"] or (state and student_id))

    if required_ok:
        sheet = get_target_worksheet_live(config["spreadsheet_name"], config["worksheet_name"])
        if sheet is not None:
            try:
                current_date = datetime.date.today().strftime("%Y-%m-%d")
                if config["collect_state"]:
                    # date, name, phonenumber, state, student_id
                    row_to_insert = [current_date, name, mobile, state, student_id]
                else:
                    # date, name, phonenumber
                    row_to_insert = [current_date, name, mobile]

                sheet.append_row(row_to_insert)
                st.success(f"Submitted for {name} with Mobile Number {mobile}")

                # Clear data cache immediately on a fresh submit so download dataset is exact
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Error writing to Google Sheet: {e}")
    else:
        if config["collect_state"]:
            st.error("Please fill in Name, Mobile Number, State and Student ID.")
        else:
            st.error("Please fill in both Name and Mobile Number.")

# --- Question/Answer Section (Always Visible) ---
st.write("---")
st.markdown(
    '<h1 style="color: teal; font-size: 26px;">Ask Your Question & Get Answer in Your Own Language</h1>',
    unsafe_allow_html=True,
)

questions_file = config["questions_file"]

if os.path.exists(questions_file):
    try:
        answered_df = pd.read_excel(questions_file)
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

            if selected_language != "English":
                try:
                    # Robust translation engines using deep-translator
                    translated_q = GoogleTranslator(source='auto', target=lang_code).translate(answer_row['question'])
                    translated_a = GoogleTranslator(source='auto', target=lang_code).translate(answer_row['answer'])
                except Exception as translation_error:
                    st.error(f"Translation engine timed out: {translation_error}")
                    translated_q, translated_a = answer_row['question'], answer_row['answer']
            else:
                translated_q = answer_row['question']
                translated_a = answer_row['answer']

            st.write(f"**Translated Question ({selected_language}):** {translated_q}")
            st.write(f"**Translated Answer ({selected_language}):** {translated_a}")

            # Audio Engine
            text_to_speak = f"Question: {translated_q}. Answer: {translated_a}"
            tts = gTTS(text=text_to_speak, lang=lang_code)
            audio_path = "question_answer_audio.mp3"
            tts.save(audio_path)
            st.audio(audio_path, format="audio/mp3")

    except Exception as e:
        st.error(f"Error loading data: {e}")
else:
    st.error(f"Missing '{questions_file}' file.")

# --- WhatsApp Support ---
st.write("---")
st.markdown(
    '<div style="text-align: center;"><h1 style="color: teal; font-size: 26px;">Contact Us via WhatsApp</h1></div>',
    unsafe_allow_html=True,
)
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
st.markdown(
    '<h1 style="color: teal;font-size: 26px;">Chat Timing - 10:30 AM - 5:30 PM (On Official Days)</h1>',
    unsafe_allow_html=True,
)

# --- Download Data Section ---
st.write("---")
st.markdown('<h1 style="color: teal;font-size: 26px;">Download Data</h1>', unsafe_allow_html=True)
password = st.text_input("Enter Password", type="password")

if st.button("Download Data"):
    if password == "monitaring_stu_bot@1234":
        records = get_cached_spreadsheet_records(config["spreadsheet_name"], config["worksheet_name"])
        if records:
            try:
                df = pd.DataFrame(records)

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Answers')
                buffer.seek(0)

                st.download_button(
                    label="📥 Download answers data as Excel",
                    data=buffer,
                    file_name=f"{st.session_state.user_type}_answers_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error generating download package: {e}")
        else:
            st.warning("No records found or sheet is empty.")
    else:
        st.error("Incorrect password. Please try again.")

# --- Review Link ---
st.markdown("[🌟 Click Here To Give A Review](https://www.google.com/search?q=Anudip)", unsafe_allow_html=True)
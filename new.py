import datetime
import os
import io
import base64
import urllib.parse
import streamlit as st
import pandas as pd
import requests
from gtts import gTTS
from deep_translator import GoogleTranslator
from PIL import Image

try:
    from streamlit_js_eval import get_geolocation
except Exception:
    get_geolocation = None

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
USER_CONFIG = {
    "new": {
        "label": "🧑‍🎓 New Student",
        "spreadsheet_name": "Responce_table_For_new_User",
        "worksheet_name": "Sheet1",
        "questions_file": "questions_answers_for_new_student.xlsx",
        "collect_state": True,
    },
    "existing": {
        "label": "🎓 Existing Student",
        "spreadsheet_name": "Responce Table",
        "worksheet_name": "data",
        "questions_file": "questions_answers.xlsx",
        "collect_state": False,
    },
}


# --- SPEED OPTIMIZATION: CACHE FOR 30 MINUTES (1800 SECONDS) ---
@st.cache_data(ttl=1800)
def get_cached_spreadsheet_records(spreadsheet_name, worksheet_name):
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
    gc = get_gspread_client()
    if gc is None:
        return None
    try:
        spreadsheet = gc.open(spreadsheet_name)
        return spreadsheet.worksheet(worksheet_name)
    except Exception as e:
        st.error(f"Error accessing Google Sheet: {e}")
        return None


# ---------------- OFFICIAL INDIAN STATES & VALIDATION ----------------
INDIAN_STATES = {
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry",
    "Chandigarh", "Andaman and Nicobar Islands", "Dadra and Nagar Haveli and Daman and Diu"
}


def is_valid_indian_state(state_name):
    if not state_name:
        return False
    s_clean = state_name.strip().lower()
    for valid_state in INDIAN_STATES:
        if valid_state.lower() in s_clean or s_clean in valid_state.lower():
            return True
    return False


def is_valid_indian_pincode(pincode):
    p = str(pincode).strip()
    return len(p) == 6 and p.isdigit() and p[0] in "123456789"


# ---------------- GEOLOCATION & PINCODE HELPERS ----------------
def get_client_ip_from_headers():
    """
    Extracts the student's true IP address from Streamlit HTTP headers.
    """
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = {str(k).lower(): v for k, v in st.context.headers.items()}
            for h in ["x-forwarded-for", "cf-connecting-ip", "x-real-ip", "forwarded"]:
                if h in headers and headers[h]:
                    raw = str(headers[h]).split(",")[0].strip()
                    if ":" in raw and not raw.startswith("2") and not raw.startswith("f"):
                        raw = raw.split(":")[0].strip()
                    if raw and not raw.startswith("127.") and not raw.startswith("10.") and not raw.startswith("192.168."):
                        return raw
    except Exception:
        pass
    return None


@st.cache_data(ttl=1800)
def get_location_from_ip(client_ip=None):
    """
    Fetches accurate client location via multi-source IP API, strictly for India.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    target_1 = f"https://ipwho.is/{client_ip}" if client_ip else "https://ipwho.is/"
    target_2 = f"https://freeipapi.com/api/json/{client_ip}" if client_ip else "https://freeipapi.com/api/json"

    try:
        res = requests.get(target_1, headers=headers, timeout=4)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") and data.get("country_code") == "IN":
                region = data.get("region", "").strip()
                postal = str(data.get("postal", "") or "").strip()
                return {
                    "state": region if is_valid_indian_state(region) else "",
                    "pincode": postal if is_valid_indian_pincode(postal) else ""
                }
    except Exception:
        pass

    try:
        res = requests.get(target_2, headers=headers, timeout=4)
        if res.status_code == 200:
            data = res.json()
            if data.get("countryCode") == "IN":
                region = data.get("regionName", "").strip()
                postal = str(data.get("zipCode", "") or "").strip()
                return {
                    "state": region if is_valid_indian_state(region) else "",
                    "pincode": postal if is_valid_indian_pincode(postal) else ""
                }
    except Exception:
        pass

    return None


@st.cache_data(ttl=86400)
def reverse_geocode_coords(lat, lon):
    """
    Reverse geocodes device GPS coordinates using OpenStreetMap Nominatim.
    Fetches exact local PIN code and State directly from device location.
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        res = requests.get(url, headers={"User-Agent": "AnudipStudentBot/4.0 (Windows NT 10.0; Win64; x64)"}, timeout=5)
        if res.status_code == 200:
            addr = res.json().get("address", {})
            st_name = addr.get("state", "").strip()
            pin = addr.get("postcode", "").strip()
            # Clean postcode to digits
            if pin:
                clean_p = "".join(filter(str.isdigit, pin))[:6]
                pin = clean_p if is_valid_indian_pincode(clean_p) else ""
            return {
                "state": st_name if is_valid_indian_state(st_name) else "",
                "pincode": pin if is_valid_indian_pincode(pin) else "",
                "city": addr.get("city") or addr.get("town") or addr.get("village", "")
            }
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400)
def get_state_from_pincode(pincode):
    """
    Resolves official Indian State name from a 6-digit postal PIN code using India Post API.
    Works for Tamil Nadu (60xxxx-64xxxx), Karnataka (56xxxx-59xxxx), UP (20xxxx-28xxxx), etc.
    """
    if not pincode:
        return None
    pincode_clean = str(pincode).strip()
    if not is_valid_indian_pincode(pincode_clean):
        return None
    try:
        res = requests.get(
            f"https://api.postalpincode.in/pincode/{pincode_clean}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=4
        )
        if res.status_code == 200:
            data = res.json()
            if data and isinstance(data, list) and data[0].get("Status") == "Success":
                post_offices = data[0].get("PostOffice", [])
                if post_offices:
                    return post_offices[0].get("State", "")
    except Exception:
        pass
    return None


# ---------------- SESSION STATE INIT ----------------
if "user_type" not in st.session_state:
    st.session_state.user_type = None
if "submitted_ok" not in st.session_state:
    st.session_state.submitted_ok = False
if "new_pincode" not in st.session_state:
    st.session_state.new_pincode = ""
if "new_state" not in st.session_state:
    st.session_state.new_state = ""
if "coords_received" not in st.session_state:
    st.session_state.coords_received = False


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
            st.session_state.submitted_ok = False
            st.session_state.new_pincode = ""
            st.session_state.new_state = ""
            st.session_state.coords_received = False
            st.session_state.pop("pincode_box", None)
            st.session_state.pop("state_box", None)
            st.session_state.pop("ip_checked", None)
            st.rerun()
    with col2:
        if st.button(USER_CONFIG["existing"]["label"], use_container_width=True):
            st.session_state.user_type = "existing"
            st.session_state.submitted_ok = False
            st.rerun()


if st.session_state.user_type is None or st.session_state.user_type not in USER_CONFIG:
    show_start_page()
    st.stop()

# ---------------- MAIN APP (runs only after a choice is made) ----------------
config = USER_CONFIG[st.session_state.user_type]

top_left, top_right = st.columns([5, 1])
with top_right:
    if st.button("⬅ Change"):
        st.session_state.user_type = None
        st.session_state.submitted_ok = False
        st.session_state.new_pincode = ""
        st.session_state.new_state = ""
        st.session_state.coords_received = False
        st.session_state.pop("pincode_box", None)
        st.session_state.pop("state_box", None)
        st.session_state.pop("ip_checked", None)
        st.rerun()

if os.path.exists("Anudip_care_Update_photo.jpg"):
    st.image("Anudip_care_Update_photo.jpg")
st.markdown('<h1 style="color: teal; font-size: 26px;">Anudip Student Bot</h1>', unsafe_allow_html=True)
st.caption(f"You selected: **{config['label']}**")

# ---------------- STEP 1: REGISTRATION FORM ----------------
# Shown only until the form is successfully submitted for this session.
if not st.session_state.submitted_ok:
    if st.session_state.user_type == "new":
        # 1. Trigger Native Browser Location Permission Prompt ("Allow: Only This Time / Always On")
        if get_geolocation and not st.session_state.coords_received:
            try:
                geo = get_geolocation(component_key="get_device_location")
                if geo and "coords" in geo:
                    lat = geo["coords"].get("latitude")
                    lon = geo["coords"].get("longitude")
                    if lat and lon:
                        info = reverse_geocode_coords(lat, lon)
                        if info:
                            if info.get("pincode"):
                                st.session_state.new_pincode = info["pincode"]
                                st.session_state["pincode_box"] = info["pincode"]
                            if info.get("state"):
                                st.session_state.new_state = info["state"]
                                st.session_state["state_box"] = info["state"]
                            st.session_state.coords_received = True
                            st.rerun()
            except Exception:
                pass

        # 2. Network IP fallback (if GPS not yet answered or skipped)
        if not st.session_state.coords_received and not st.session_state.get("ip_checked"):
            c_ip = get_client_ip_from_headers()
            if c_ip:
                ip_loc = get_location_from_ip(c_ip)
                if ip_loc:
                    if ip_loc.get("state") and not st.session_state.new_state:
                        st.session_state.new_state = ip_loc["state"]
                        st.session_state["state_box"] = ip_loc["state"]
                    if ip_loc.get("pincode") and not st.session_state.new_pincode:
                        st.session_state.new_pincode = ip_loc["pincode"]
                        st.session_state["pincode_box"] = ip_loc["pincode"]
            st.session_state.ip_checked = True

        # Callback: When student types or changes PIN code, immediately resolve the exact State
        def on_pincode_change():
            pin_val = st.session_state.get("pincode_box", "").strip()
            st.session_state.new_pincode = pin_val
            # When student enters any 6-digit Indian PIN code, automatically look up official State
            if is_valid_indian_pincode(pin_val):
                found_state = get_state_from_pincode(pin_val)
                if found_state and is_valid_indian_state(found_state):
                    st.session_state.new_state = found_state
                    st.session_state["state_box"] = found_state

        def on_state_change():
            st.session_state.new_state = st.session_state.get("state_box", "").strip()

        # Input fields for New Student
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
        with col2:
            mobile = st.text_input("Mobile Number", max_chars=10)

        col3, col4 = st.columns(2)
        with col3:
            pincode = st.text_input(
                "Pin Code",
                value=st.session_state.get("new_pincode", ""),
                max_chars=6,
                key="pincode_box",
                on_change=on_pincode_change,
                placeholder="Enter 6-digit Pin Code (e.g. 600001)",
                help="Type your 6-digit postal PIN code. State will auto-fill automatically."
            )
        with col4:
            state = st.text_input(
                "State",
                value=st.session_state.get("new_state", ""),
                key="state_box",
                on_change=on_state_change,
                placeholder="Auto-detected from GPS / Pin Code",
                help="State is automatically updated from your location or when you type your Pin Code."
            )

        student_id = ""
        submitted = st.button("✅ Submit")

    else:
        # Existing student flow: Name (Mandatory), Phone Number (Optional), Student ID (Mandatory: AF0...)
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
        with col2:
            mobile = st.text_input("CMIS Register Mobile Number (Optional)", max_chars=10, help="Optional: 10-digit mobile number")

        col3, _ = st.columns(2)
        with col3:
            student_id = st.text_input("Student ID (Mandatory)", help="Must start with 'AF0' (e.g., AF05319302)")

        pincode = ""
        state = ""
        submitted = st.button("✅ Submit")

    # --- Save to Google Sheet ---
    if submitted:
        if st.session_state.user_type == "new":
            clean_pin = pincode.strip()
            clean_state = state.strip()

            # If state is not filled yet, resolve state from pin code before checking
            if is_valid_indian_pincode(clean_pin) and not clean_state:
                resolved_st = get_state_from_pincode(clean_pin)
                if resolved_st:
                    clean_state = resolved_st
                    state = resolved_st

            if not (name.strip() and mobile.strip() and clean_pin and clean_state):
                st.error("Please fill in Name, Mobile Number, Pin Code and State.")
            elif len(mobile.strip()) != 10 or not mobile.strip().isdigit():
                st.error("Please enter a valid 10-digit mobile number.")
            elif not is_valid_indian_pincode(clean_pin):
                st.error("Please enter a valid 6-digit Indian postal PIN Code.")
            else:
                sheet = get_target_worksheet_live(config["spreadsheet_name"], config["worksheet_name"])
                if sheet is not None:
                    try:
                        current_date = datetime.date.today().strftime("%Y-%m-%d")
                        headers = [str(h).strip().lower() for h in sheet.row_values(1)]
                        if "pincode" not in headers:
                            sheet.update_cell(1, len(headers) + 1, "pincode")
                            sheet.update_cell(1, len(headers) + 2, "state")
                            headers = [str(h).strip().lower() for h in sheet.row_values(1)]

                        if headers:
                            row_to_insert = []
                            for h in headers:
                                if "date" in h:
                                    row_to_insert.append(current_date)
                                elif "name" in h:
                                    row_to_insert.append(name.strip())
                                elif "phone" in h or "mobile" in h:
                                    row_to_insert.append(mobile.strip())
                                elif "pin" in h:
                                    row_to_insert.append(clean_pin)
                                elif "state" in h:
                                    row_to_insert.append(clean_state)
                                else:
                                    row_to_insert.append("")
                        else:
                            row_to_insert = [current_date, name.strip(), mobile.strip(), clean_pin, clean_state]

                        sheet.append_row(row_to_insert)

                        # Clear data cache immediately on a fresh submit
                        st.cache_data.clear()

                        # Move on to the Q&A / WhatsApp page
                        st.session_state.submitted_ok = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error writing to Google Sheet: {e}")
        else:
            # Existing student validation & submission:
            # - Name: Mandatory
            # - Student ID: Mandatory & must start with "AF0"
            # - Phone Number: Not Mandatory, but if entered must be numeric and 10 digits
            clean_name = name.strip()
            clean_mobile = mobile.strip()
            clean_id = student_id.strip().upper()

            if not clean_name:
                st.error("Please enter your Name.")
            elif not clean_id:
                st.error("Please enter your Student ID.")
            elif not clean_id.startswith("AF0"):
                st.error("Student ID is mandatory and must start with 'AF0' (e.g., AF05319302).")
            elif clean_mobile and (len(clean_mobile) != 10 or not clean_mobile.isdigit()):
                st.error("Mobile Number is optional, but if entered it must be a valid 10-digit number.")
            else:
                sheet = get_target_worksheet_live(config["spreadsheet_name"], config["worksheet_name"])
                if sheet is not None:
                    try:
                        current_date = datetime.date.today().strftime("%Y-%m-%d")
                        headers = [str(h).strip().lower() for h in sheet.row_values(1)]
                        if headers:
                            row_to_insert = []
                            for h in headers:
                                if "date" in h:
                                    row_to_insert.append(current_date)
                                elif "name" in h:
                                    row_to_insert.append(clean_name)
                                elif "phone" in h or "mobile" in h:
                                    row_to_insert.append(clean_mobile)
                                elif "student" in h or "id" in h:
                                    row_to_insert.append(clean_id)
                                elif "state" in h:
                                    row_to_insert.append("")  # No State collection for existing students
                                elif "pin" in h:
                                    row_to_insert.append("")
                                else:
                                    row_to_insert.append("")
                        else:
                            row_to_insert = [current_date, clean_name, clean_mobile, "", clean_id]

                        sheet.append_row(row_to_insert)

                        # Clear data cache immediately on a fresh submit
                        st.cache_data.clear()

                        # Move on to the Q&A / WhatsApp page
                        st.session_state.submitted_ok = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error writing to Google Sheet: {e}")

    # Don't show anything below the form until it's submitted successfully
    st.stop()

# ---------------- STEP 2: Q&A / WHATSAPP / DOWNLOAD (shown after successful submit) ----------------
if st.button("⬅ Submit Another Entry"):
    st.session_state.submitted_ok = False
    st.session_state.new_pincode = ""
    st.session_state.new_state = ""
    st.session_state.coords_received = False
    st.session_state.pop("pincode_box", None)
    st.session_state.pop("state_box", None)
    st.session_state.pop("ip_checked", None)
    st.rerun()

# --- Question/Answer Section ---
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

# --- Review Link ---
st.markdown("[🌟 Click Here To Give A Review](https://www.google.com/search?q=Anudip)", unsafe_allow_html=True)
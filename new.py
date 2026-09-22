import datetime
import os
import io
import base64
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
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
        "collect_state": False,  # No state collection for existing students
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


# ---------------- GEOLOCATION & PINCODE HELPERS ----------------
@st.cache_data(ttl=1800)
def get_location_from_ip():
    """
    Fetches accurate client location (state/region & postal code) via multi-source IP API.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    # Provider 1: ipwho.is
    try:
        res = requests.get("https://ipwho.is/", headers=headers, timeout=4)
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                return {
                    "lat": data.get("latitude"),
                    "lon": data.get("longitude"),
                    "city": data.get("city", ""),
                    "state": data.get("region", ""),
                    "pincode": str(data.get("postal", "") or "")
                }
    except Exception:
        pass

    # Provider 2: freeipapi.com
    try:
        res = requests.get("https://freeipapi.com/api/json", headers=headers, timeout=4)
        if res.status_code == 200:
            data = res.json()
            return {
                "lat": data.get("latitude"),
                "lon": data.get("longitude"),
                "city": data.get("cityName", ""),
                "state": data.get("regionName", ""),
                "pincode": str(data.get("zipCode", "") or "")
            }
    except Exception:
        pass

    return None


@st.cache_data(ttl=86400)
def reverse_geocode_coords(lat, lon):
    """
    Reverse geocodes latitude/longitude to state and accurate postcode using OpenStreetMap Nominatim.
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        res = requests.get(url, headers={"User-Agent": "AnudipStudentBot/2.0 (Windows NT 10.0; Win64; x64)"}, timeout=4)
        if res.status_code == 200:
            addr = res.json().get("address", {})
            return {
                "state": addr.get("state", ""),
                "pincode": addr.get("postcode", ""),
                "city": addr.get("city") or addr.get("town") or addr.get("village", "")
            }
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400)
def get_state_from_pincode(pincode):
    """
    Resolves Indian State name from a 6-digit postal PIN code using the Postal API.
    """
    if not pincode:
        return None
    pincode_clean = str(pincode).strip()
    if len(pincode_clean) != 6 or not pincode_clean.isdigit():
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


def get_default_location():
    """
    Returns auto-detected State name and Pin Code, prioritizing IP and postal lookup.
    """
    loc = get_location_from_ip()
    st_name = "West Bengal"
    pin = ""
    if loc:
        pin = str(loc.get("pincode") or "").strip()
        if pin:
            clean_digits = "".join(filter(str.isdigit, pin))[:6]
            pin = clean_digits if len(clean_digits) == 6 else pin
        st_name = loc.get("state") or "West Bengal"

    # If pin code is valid, verify and resolve state from postal API
    if pin and len(pin) == 6 and pin.isdigit():
        postal_state = get_state_from_pincode(pin)
        if postal_state:
            st_name = postal_state

    return st_name, pin


# ---------------- SESSION STATE INIT ----------------
default_st, default_pin = get_default_location()

if "user_type" not in st.session_state:
    st.session_state.user_type = None
if "submitted_ok" not in st.session_state:
    st.session_state.submitted_ok = False
if "new_pincode" not in st.session_state:
    st.session_state.new_pincode = default_pin
if "new_state" not in st.session_state or not st.session_state.new_state:
    st.session_state.new_state = default_st
if "gps_resolved" not in st.session_state:
    st.session_state.gps_resolved = False


# --- Real GPS Geolocation via Browser HTML5 ---
# Requests browser's exact GPS coordinates (mobile/laptop) to eliminate ISP exchange mismatch
gps_script = """
<script>
if (navigator.geolocation && !window.location.search.includes('gps_lat')) {
    navigator.geolocation.getCurrentPosition(function(pos) {
        var lat = pos.coords.latitude.toFixed(4);
        var lon = pos.coords.longitude.toFixed(4);
        try {
            var searchParams = new URLSearchParams(window.parent.location.search);
            if (searchParams.get('gps_lat') !== lat) {
                searchParams.set('gps_lat', lat);
                searchParams.set('gps_lon', lon);
                window.parent.location.search = searchParams.toString();
            }
        } catch(e) {}
    }, function(err) {
        console.log("GPS unavailable or denied:", err);
    }, { enableHighAccuracy: true, timeout: 5000, maximumAge: 300000 });
}
</script>
"""
components.html(gps_script, height=0)

# If real GPS coordinates were passed from browser, reverse-geocode them
gps_lat = st.query_params.get("gps_lat")
gps_lon = st.query_params.get("gps_lon")
if gps_lat and gps_lon and not st.session_state.gps_resolved:
    try:
        geo = reverse_geocode_coords(float(gps_lat), float(gps_lon))
        if geo:
            if geo.get("pincode"):
                clean_p = "".join(filter(str.isdigit, str(geo["pincode"])))[:6]
                if len(clean_p) == 6:
                    st.session_state.new_pincode = clean_p
                    st.session_state.pincode_box = clean_p
            if geo.get("state"):
                st.session_state.new_state = str(geo["state"])
                st.session_state.state_box = str(geo["state"])
            st.session_state.gps_resolved = True
    except Exception:
        pass


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
            cur_st, cur_pin = get_default_location()
            st.session_state.new_pincode = cur_pin
            st.session_state.new_state = cur_st
            st.session_state.pincode_box = cur_pin
            st.session_state.state_box = cur_st
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
        cur_st, cur_pin = get_default_location()
        st.session_state.new_pincode = cur_pin
        st.session_state.new_state = cur_st
        st.session_state.pincode_box = cur_pin
        st.session_state.state_box = cur_st
        st.rerun()

if os.path.exists("Anudip_care_Update_photo.jpg"):
    st.image("Anudip_care_Update_photo.jpg")
st.markdown('<h1 style="color: teal; font-size: 26px;">Anudip Student Bot</h1>', unsafe_allow_html=True)
st.caption(f"You selected: **{config['label']}**")

# ---------------- STEP 1: REGISTRATION FORM ----------------
# Shown only until the form is successfully submitted for this session.
if not st.session_state.submitted_ok:
    if st.session_state.user_type == "new":
        # Always make sure state is resolved from current pin code if not set
        current_pin_val = st.session_state.get("new_pincode", default_pin).strip()
        if len(current_pin_val) == 6 and current_pin_val.isdigit():
            resolved = get_state_from_pincode(current_pin_val)
            if resolved:
                st.session_state.new_state = resolved

        if not st.session_state.get("new_state"):
            st.session_state.new_state = default_st or "West Bengal"

        # Initialize widget keys in session state to guarantee they are never empty on load
        if "pincode_box" not in st.session_state or not st.session_state.get("pincode_box"):
            st.session_state.pincode_box = st.session_state.new_pincode
        if "state_box" not in st.session_state or not st.session_state.get("state_box"):
            st.session_state.state_box = st.session_state.new_state

        # Callbacks for interactive changes
        def on_pincode_change():
            pin_val = st.session_state.get("pincode_box", "").strip()
            st.session_state.new_pincode = pin_val
            # When student changes PIN code to any 6-digit number, automatically update State
            if len(pin_val) == 6 and pin_val.isdigit():
                found_st = get_state_from_pincode(pin_val)
                if found_st:
                    st.session_state.new_state = found_st
                    st.session_state.state_box = found_st

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
                max_chars=6,
                key="pincode_box",
                on_change=on_pincode_change,
                help="Auto-detected Pin Code. If this does not match, delete it and enter your 6-digit PIN code."
            )
        with col4:
            state = st.text_input(
                "State",
                key="state_box",
                on_change=on_state_change,
                help="Auto-detected State. If this does not match, delete it and enter your State name."
            )

        student_id = ""
        submitted = st.button("✅ Submit")

    else:
        # Existing student flow: Name, CMIS Register Mobile Number, Student ID (NO State collection)
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
        with col2:
            mobile = st.text_input("CMIS Register Mobile Number", max_chars=10)

        col3, _ = st.columns(2)
        with col3:
            student_id = st.text_input("Student ID")

        pincode = ""
        state = ""
        submitted = st.button("✅ Submit")

    # --- Save to Google Sheet ---
    if submitted:
        if st.session_state.user_type == "new":
            clean_pin = pincode.strip()
            # If state wasn't updated yet, resolve state from pin code
            if len(clean_pin) == 6 and clean_pin.isdigit() and not state.strip():
                resolved_st = get_state_from_pincode(clean_pin)
                if resolved_st:
                    state = resolved_st

            if not (name.strip() and mobile.strip() and clean_pin and state.strip()):
                st.error("Please fill in Name, Mobile Number, Pin Code and State.")
            elif len(mobile.strip()) != 10 or not mobile.strip().isdigit():
                st.error("Please enter a valid 10-digit mobile number.")
            elif len(clean_pin) != 6 or not clean_pin.isdigit():
                st.error("Please enter a valid 6-digit Pin Code.")
            else:
                sheet = get_target_worksheet_live(config["spreadsheet_name"], config["worksheet_name"])
                if sheet is not None:
                    try:
                        current_date = datetime.date.today().strftime("%Y-%m-%d")
                        # Ensure headers exist in the sheet
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
                                    row_to_insert.append(state.strip())
                                else:
                                    row_to_insert.append("")
                        else:
                            row_to_insert = [current_date, name.strip(), mobile.strip(), clean_pin, state.strip()]

                        sheet.append_row(row_to_insert)

                        # Clear data cache immediately on a fresh submit
                        st.cache_data.clear()

                        # Move on to the Q&A / WhatsApp page
                        st.session_state.submitted_ok = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error writing to Google Sheet: {e}")
        else:
            # Existing student validation & submission (No State collected)
            if not (name.strip() and mobile.strip() and student_id.strip()):
                st.error("Please fill in Name, CMIS Register Mobile Number and Student ID.")
            elif len(mobile.strip()) != 10 or not mobile.strip().isdigit():
                st.error("Please enter a valid 10-digit mobile number.")
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
                                    row_to_insert.append(name.strip())
                                elif "phone" in h or "mobile" in h:
                                    row_to_insert.append(mobile.strip())
                                elif "student" in h or "id" in h:
                                    row_to_insert.append(student_id.strip())
                                elif "state" in h:
                                    row_to_insert.append("")  # No State collection for existing students
                                elif "pin" in h:
                                    row_to_insert.append("")
                                else:
                                    row_to_insert.append("")
                        else:
                            # Fallback default if sheet has no headers
                            row_to_insert = [current_date, name.strip(), mobile.strip(), "", student_id.strip()]

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
    cur_st, cur_pin = get_default_location()
    st.session_state.new_pincode = cur_pin
    st.session_state.new_state = cur_st
    st.session_state.pincode_box = cur_pin
    st.session_state.state_box = cur_st
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
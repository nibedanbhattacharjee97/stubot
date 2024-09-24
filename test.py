import streamlit as st
import base64
import pandas as pd
from PIL import Image
import os
from io import BytesIO
from gtts import gTTS
from googletrans import Translator

# Set the page config for wider display
st.set_page_config(layout="wide")

# Function to load and encode the background image
def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded_string}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Call the function to set the background image
add_bg_from_local('Actual.jpg')  # Replace with your image file



@st.cache_data
def load_excel_data(file_path):
    return pd.read_excel(file_path)

# Load the Excel data
excel_file = 'questions_answers.xlsx'
df = load_excel_data(excel_file)

st.markdown('<h1 class="custom-title">Please Ask Your Question & Get Answer In Your Own Language</h1>', unsafe_allow_html=True)
selected_question = st.selectbox("Select a question", df['question'], key="questions")

# Display selected question and answer
question_row = df[df['question'] == selected_question].iloc[0]
col1, col2 = st.columns(2)

with col1:
    st.write(f"**Question:** {question_row['question']}")
    st.write(f"**Answer:** {question_row['answer']}")

# Display image if available
with col2:
    if pd.notna(question_row['picpath']) and isinstance(question_row['picpath'], str) and os.path.exists(question_row['picpath']):
        try:
            image = Image.open(question_row['picpath'])
            st.image(image, caption="Related Image", use_column_width=True)
        except Exception as e:
            st.write(f"Error loading image: {e}")
    else:
        st.write("")

# Language selection for text-to-speech
st.markdown('<h1 class="custom-title">Select Language for Translation and Voice Output</h1>', unsafe_allow_html=True)
language_options = {"English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te", "Marathi": "mr"}
selected_language = st.selectbox("Choose language", list(language_options.keys()), key="language")

# Translator initialization
translator = Translator()

# Translate question and answer
if selected_language != "English":
    translated_question = translator.translate(question_row['question'], dest=language_options[selected_language]).text
    translated_answer = translator.translate(question_row['answer'], dest=language_options[selected_language]).text
else:
    translated_question = question_row['question']
    translated_answer = question_row['answer']

# Display the translated question and answer
st.write(f"**Translated Question ({selected_language}):** {translated_question}")
st.write(f"**Translated Answer ({selected_language}):** {translated_answer}")

# Generate voice for the translated question and answer without saving to disk
text_to_speak = f"Question: {translated_question}. Answer: {translated_answer}"
language_code = language_options[selected_language]
tts = gTTS(text=text_to_speak, lang=language_code)

# Save the audio to a BytesIO object instead of a file
audio_bytes = BytesIO()
tts.write_to_fp(audio_bytes)
audio_bytes.seek(0)  # Go back to the start of the BytesIO object

# Display an audio player for the user to listen to the translated question and answer
st.audio(audio_bytes, format='audio/mp3')

# Contact Us via WhatsApp Section
st.write("---")
st.title("Contact Us via WhatsApp")

whatsapp_numbers = [
    {"number": "9147394695", "language": "English"},
    {"number": "9147394695", "language": "Hindi"},
    {"number": "9831894500", "language": "Bengali"},
    {"number": "7595063323", "language": "Tamil"},
    {"number": "6293415105", "language": "Telegu"}
]
whatsapp_message = "Hi Anu! I Have a Query."
whatsapp_logo_path = "whatsapp_logo.png"

# Create columns for WhatsApp contacts
col1, col2, col3, col4, col5 = st.columns(5)

if os.path.exists(whatsapp_logo_path):
    for idx, col in enumerate([col1, col2, col3, col4, col5]):
        with col:
            st.image(whatsapp_logo_path, caption=f"WhatsApp For {whatsapp_numbers[idx]['language']}", use_column_width=False, width=50)
            whatsapp_url = f"https://api.whatsapp.com/send?phone=91{whatsapp_numbers[idx]['number']}&text={whatsapp_message}"
            st.markdown(f'<a href="{whatsapp_url}" target="_blank">WhatsApp</a>', unsafe_allow_html=True)
else:
    st.error("WhatsApp logo not found. Please check the path.")

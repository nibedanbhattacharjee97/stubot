import streamlit as st
import pandas as pd
from PIL import Image
import os
from io import BytesIO
from gtts import gTTS
from googletrans import Translator
import sqlite3



st.image("Actual.png")


# Load the Excel file containing questions and answers using st.cache_data for better caching
@st.cache_data
def load_excel_data(file_path):
    return pd.read_excel(file_path)

# Load the Excel data
excel_file = 'questions_answers.xlsx'
df = load_excel_data(excel_file)

# Display a selectbox for browsing questions
import streamlit as st

# Adding custom CSS for title styling
st.markdown("""
    <style>
    .custom-title {
        font-size:25px;
        color: Teal;
        font-weight: normal;
    }
    </style>
    """, unsafe_allow_html=True)

# Displaying the title with the new style
st.markdown('<h1 class="custom-title">Please Ask Your Question & Get Answer In Your Own Language</h1>', unsafe_allow_html=True)

selected_question = st.selectbox("Select a question", df['question'], key="questions")

# Display selected question and answer
question_row = df[df['question'] == selected_question].iloc[0]
col1, col2 = st.columns(2)

with col1:
    st.write(f"**Question:** {question_row['question']}")
    st.write(f"**Answer:** {question_row['answer']}")

# Display image if available and valid path exists
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
# Adding custom CSS for title styling
st.markdown("""
    <style>
    .custom-title {
        font-size:25px;
        color: Teal;
        font-weight: normal;
    }
    </style>
    """, unsafe_allow_html=True)

# Displaying the title with the new style
st.markdown('<h1 class="custom-title">Select Language for Translation and Voice Output</h1>', unsafe_allow_html=True)
language_options = {"English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te", "Marathi": "mr"}
selected_language = st.selectbox("Choose language", list(language_options.keys()), key="language")

# Translator initialization
translator = Translator()

# Translate question and answer to the selected language if not English
if selected_language != "English":
    translated_question = translator.translate(question_row['question'], dest=language_options[selected_language]).text
    translated_answer = translator.translate(question_row['answer'], dest=language_options[selected_language]).text
else:
    translated_question = question_row['question']
    translated_answer = question_row['answer']

# Display the translated question and answer
st.write(f"**Translated Question ({selected_language}):** {translated_question}")
st.write(f"**Translated Answer ({selected_language}):** {translated_answer}")

# Generate voice for the translated question and answer
text_to_speak = f"Question: {translated_question}. Answer: {translated_answer}"
language_code = language_options[selected_language]
tts = gTTS(text_to_speak, lang=language_code)
audio_file_path = 'question_answer_audio.mp3'
tts.save(audio_file_path)

# Display an audio player for the user to listen to the translated question and answer
st.audio(audio_file_path, format='audio/mp3')

# Contact Us via WhatsApp Section
st.write("---")
st.title("Contact Us via WhatsApp")

# WhatsApp details
whatsapp_numbers = [
    {"number": "9831894500", "language": "English"},
    {"number": "9831894500", "language": "Hindi"},
    {"number": "9831894500", "language": "Bengali"},
    {"number": "7595063323", "language": "Tamil"},
    {"number": "6293415105", "language": "Telegu"}
]
whatsapp_message = "Hi Anu! I Have a Query."
whatsapp_logo_path = "whatsapp_logo.png"

# Create columns for WhatsApp contacts
col1, col2, col3, col4, col5 = st.columns(5)

# Check if logo file exists
if os.path.exists(whatsapp_logo_path):
    # Display WhatsApp logo and link in each column
    for idx, col in enumerate([col1, col2, col3, col4, col5]):
        with col:
            st.image(whatsapp_logo_path, caption=f"WhatsApp For {whatsapp_numbers[idx]['language']}", use_column_width=False, width=50)
            whatsapp_url = f"https://api.whatsapp.com/send?phone=91{whatsapp_numbers[idx]['number']}&text={whatsapp_message}"
            st.markdown(f'<a href="{whatsapp_url}" target="_blank">WhatsApp</a>', unsafe_allow_html=True)
else:
    st.error("WhatsApp logo not found. Please check the path.")

import streamlit as st
import pandas as pd
from PIL import Image
import os
from io import BytesIO
from gtts import gTTS
from googletrans import Translator
import sqlite3

# Set page configuration for full width
st.set_page_config(page_title="Related Questions", layout="wide")

# Load the Excel file containing questions and answers
excel_file = 'questions_answers.xlsx'
df = pd.read_excel(excel_file)

# Display a selectbox for browsing questions
st.title("Related Questions", anchor="title1")
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
st.subheader("Select Language for Translation and Voice Output")
language_options = {"English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te"}
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

import streamlit as st
import os

st.write("---")
st.title("Contact Us via WhatsApp")

# WhatsApp details
whatsapp_numbers = [
    {"number": "9831894500", "language": "Hindi , English"},
    {"number": "", "language": "English"},
    {"number": "", "language": "Other Languages"}
]
whatsapp_message = "Hello, I have a question regarding your service."
whatsapp_logo_path = "whatsapp_logo.png"  # Ensure this is the correct path for your image

# Create three columns
col1, col2, col3 = st.columns(3)

# Check if logo file exists
if os.path.exists(whatsapp_logo_path):
    # Display WhatsApp logo and link in each column
    with col1:
        st.image(whatsapp_logo_path, caption=f"WhatsApp For {whatsapp_numbers[0]['language']}", use_column_width=False, width=50)
        whatsapp_url_1 = f"https://api.whatsapp.com/send?phone=91{whatsapp_numbers[0]['number']}&text={whatsapp_message}"
        st.markdown(f'<a href="{whatsapp_url_1}" target="_blank">WhatsApp</a>', unsafe_allow_html=True)

    with col2:
        st.image(whatsapp_logo_path, caption=f"WhatsApp For {whatsapp_numbers[1]['language']}", use_column_width=False, width=50)
        whatsapp_url_2 = f"https://api.whatsapp.com/send?phone=91{whatsapp_numbers[1]['number']}&text={whatsapp_message}"
        st.markdown(f'<a href="{whatsapp_url_2}" target="_blank">WhatsApp</a>', unsafe_allow_html=True)

    with col3:
        st.image(whatsapp_logo_path, caption=f"WhatsApp For {whatsapp_numbers[2]['language']}", use_column_width=False, width=50)
        whatsapp_url_3 = f"https://api.whatsapp.com/send?phone=91{whatsapp_numbers[2]['number']}&text={whatsapp_message}"
        st.markdown(f'<a href="{whatsapp_url_3}" target="_blank">WhatsApp</a>', unsafe_allow_html=True)

else:
    st.error("WhatsApp logo not found. Please check the path.")



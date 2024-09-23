import streamlit as st
import pandas as pd
from PIL import Image
import os
from io import BytesIO
from gtts import gTTS
from googletrans import Translator
import sqlite3

# Create SQLite database and table if it doesn't exist
conn = sqlite3.connect('submitted_questions.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        question TEXT,
        pic TEXT,
        phone TEXT
    )
''')
conn.commit()

# Load the Excel file containing questions and answers
excel_file = 'questions_answers.xlsx'
df = pd.read_excel(excel_file)

# Display a selectbox for browsing questions
st.title("Related Questions")
selected_question = st.selectbox("Select a question", df['question'])

# Display selected question and answer
question_row = df[df['question'] == selected_question].iloc[0]
st.write(f"**Question:** {question_row['question']}")
st.write(f"**Answer:** {question_row['answer']}")

# Display image if available and valid path exists
if pd.notna(question_row['picpath']) and isinstance(question_row['picpath'], str) and os.path.exists(question_row['picpath']):
    try:
        image = Image.open(question_row['picpath'])
        st.image(image, caption="Related Image", use_column_width=True)
    except Exception as e:
        st.write(f"Error loading image: {e}")
else:
    st.write("")

# Language selection for text-to-speech
st.title("Select Language for Translation and Voice Output")
language_options = {"English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te"}
selected_language = st.selectbox("Choose language", list(language_options.keys()))

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

# WhatsApp integration
st.write("---")
st.title("Contact Us via WhatsApp")

whatsapp_number = "9083387648"
whatsapp_message = "Hello, I have a question regarding your service."
whatsapp_url = f"https://api.whatsapp.com/send?phone=91{whatsapp_number}&text={whatsapp_message}"

# Load and display WhatsApp logo
whatsapp_logo_path = "whatsapp_logo.png"  # Make sure the image is in your project folder

if os.path.exists(whatsapp_logo_path):
    # Display the image using st.image
    st.image(whatsapp_logo_path, caption="Contact Us on WhatsApp", use_column_width=False, width=50)
    
    # Display the link under the image
    st.markdown(f'<a href="{whatsapp_url}" target="_blank">Click here to chat with us on WhatsApp</a>', unsafe_allow_html=True)
else:
    st.error("WhatsApp logo not found. Please check the path.")


# Close the database connection
conn.close()

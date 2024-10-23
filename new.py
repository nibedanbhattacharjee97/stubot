import streamlit as st
import pandas as pd
from PIL import Image
import os
from gtts import gTTS
from googletrans import Translator
import sqlite3
import io
import schedule
import time
import threading
from datetime import datetime

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('new_answer_db')  # Updated database name
c = conn.cursor()

# Create the table for storing user-submitted answers if it doesn't already exist
c.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT,
        name TEXT,
        phone TEXT,
        location TEXT
    )
''')
conn.commit()

st.image("Actual.png")

# Load the Excel file containing questions and answers using st.cache_data for better caching
@st.cache_data
def load_excel_data(file_path):
    return pd.read_excel(file_path)

# Load the Excel data
excel_file = 'questions_answers.xlsx'
df = load_excel_data(excel_file)

# Filter the questions with answers and without answers
answered_df = df[df['answer'].notna() & df['answer'].str.strip().ne("")]
unanswered_df = df[df['answer'].isna() | df['answer'].str.strip().eq("")]

# Section for Answer Submission
st.markdown("""<style>
    .custom-title { font-size:25px; color: Teal; font-weight: normal; }
    </style>""", unsafe_allow_html=True)

st.markdown('<h1 class="custom-title">Submit Your Answer</h1>', unsafe_allow_html=True)

selected_unanswered_question = st.selectbox("Select an unanswered question", unanswered_df['question'], key="unanswered_questions", label_visibility='collapsed')

col_a, col_b = st.columns([1, 1])

with st.form("answer_form"):
    with col_a:
        name = st.text_input("Your Name")
    with col_b:
        phone = st.text_input("Your Phone Number")
    
    user_answer = st.text_area("Your Answer")
    location = st.text_input("Your Location")
    
    submit_answer = st.form_submit_button("Submit Answer")

if submit_answer:
    if name and phone and user_answer and location:
        c.execute('''
            INSERT INTO answers (question, answer, name, phone, location) 
            VALUES (?, ?, ?, ?, ?)
        ''', (selected_unanswered_question, user_answer, name, phone, location))
        conn.commit()
        st.success("Thank you! Your answer has been submitted.")
    else:
        st.error("Please fill out all the fields.")

# Display Questions and Answers
st.markdown('<h1 class="custom-title">Please Ask Your Question & Get Answer In Your Own Language</h1>', unsafe_allow_html=True)

selected_answered_question = st.selectbox("Select a question", answered_df['question'], key="answered_questions")

answered_question_row = answered_df[answered_df['question'] == selected_answered_question].iloc[0]
col1, col2 = st.columns(2)

with col1:
    st.write(f"**Question:** {answered_question_row['question']}")
    st.write(f"**Answer:** {answered_question_row['answer']}")

with col2:
    if pd.notna(answered_question_row['picpath']) and isinstance(answered_question_row['picpath'], str) and os.path.exists(answered_question_row['picpath']):
        try:
            image = Image.open(answered_question_row['picpath'])
            st.image(image, caption="Related Image", use_column_width=True)
        except Exception as e:
            st.write(f"Error loading image: {e}")
    else:
        st.write("")

# Language Translation and Voice Output
st.markdown('<h1 class="custom-title">Select Language for Translation and Voice Output</h1>', unsafe_allow_html=True)
language_options = {"English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te", "Marathi": "mr"}
selected_language = st.selectbox("Choose language", list(language_options.keys()), key="language")

translator = Translator()

if selected_language != "English":
    translated_question = translator.translate(answered_question_row['question'], dest=language_options[selected_language]).text
    translated_answer = translator.translate(answered_question_row['answer'], dest=language_options[selected_language]).text
else:
    translated_question = answered_question_row['question']
    translated_answer = answered_question_row['answer']

st.write(f"**Translated Question ({selected_language}):** {translated_question}")
st.write(f"**Translated Answer ({selected_language}):** {translated_answer}")

text_to_speak = f"Question: {translated_question}. Answer: {translated_answer}"
language_code = language_options[selected_language]
tts = gTTS(text_to_speak, lang=language_code)
audio_file_path = 'question_answer_audio.mp3'
tts.save(audio_file_path)

st.audio(audio_file_path, format='audio/mp3')

# WhatsApp Contact Section
st.write("---")
st.markdown('<h1 class="custom-title">Contact Us via WhatsApp</h1>', unsafe_allow_html=True)

whatsapp_numbers = [
    {"number": "9147394695", "language": "English"},
    {"number": "9147394695", "language": "Hindi"},
    {"number": "9147394695", "language": "Bengali"},
    {"number": "7595063323", "language": "Tamil"},
    {"number": "6293415105", "language": "Telugu"}
]
whatsapp_message = "Hi Anu! I Have a Query."
whatsapp_logo_path = "whatsapp_logo.png"

cols = st.columns(5)

if os.path.exists(whatsapp_logo_path):
    for idx, col in enumerate(cols):
        with col:
            st.image(whatsapp_logo_path, caption=f"WhatsApp For {whatsapp_numbers[idx]['language']}", use_column_width=False, width=50)
            whatsapp_url = f"https://api.whatsapp.com/send?phone=91{whatsapp_numbers[idx]['number']}&text={whatsapp_message}"
            st.markdown(f'<a href="{whatsapp_url}" target="_blank">WhatsApp</a>', unsafe_allow_html=True)
else:
    st.error("WhatsApp logo not found. Please check the path.")

# Define the function to export the database to CSV
def export_to_csv():
    query = "SELECT * FROM answers"
    df = pd.read_sql_query(query, conn)
    folder_path = "store_data"  # Update this to your desired folder path
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    current_date = datetime.now().strftime("%Y-%m-%d")
    csv_file_path = os.path.join(folder_path, f"answers_{current_date}.csv")
    df.to_csv(csv_file_path, index=False)
    print(f"Exported to {csv_file_path}")

# Schedule the function to run every day at 5 PM
schedule.every().day.at("17:00").do(export_to_csv)

# Function to run the scheduler in the background
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start the scheduler thread
threading.Thread(target=run_schedule, daemon=True).start()

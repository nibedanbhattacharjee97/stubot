import streamlit as st
import pandas as pd
from PIL import Image
import os
from gtts import gTTS
from googletrans import Translator
import sqlite3

# Load center name and state data from the provided Excel file
center_state_file = 'Statewise_center.xlsx'  # Replace with the actual path to your Excel file
center_data = pd.read_excel(center_state_file, engine="openpyxl")
center_data.columns = ['Center Name', 'State']  # Adjust column names if needed

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('updated_new_db')
c = conn.cursor()

# Check if the 'center_name' column exists, and if not, add it
try:
    c.execute('SELECT center_name FROM answers')
except sqlite3.OperationalError:
    c.execute('ALTER TABLE answers ADD COLUMN center_name TEXT')

# Create the table for storing user-submitted answers if it doesn't already exist
c.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT,
        name TEXT,
        phone TEXT,
        center_name TEXT,
        state TEXT
    )
''')
conn.commit()

st.image("Actual_UP.jpg")

# Load the Excel file containing questions and answers
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
st.markdown('<h1 style="color: teal;">Submit Your Answer</h1>', unsafe_allow_html=True)

# Form for submitting an answer
with st.form("answer_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Your Name")

    with col2:
        phone = st.text_input("Your Phone Number")

    # Center Name selection
    center_name = st.selectbox("Select Center Name", ["Select a center"] + list(center_data['Center Name'].unique()))
    
    # Display State based on selected Center Name
    if center_name != "Select a center":
        state = center_data.loc[center_data['Center Name'] == center_name, 'State'].values[0]
        st.write(f"State: {state}")

    # Question selection and answer input
    selected_unanswered_question = st.selectbox("Select an unanswered question", unanswered_df['question'], key="unanswered_questions")
    user_answer = st.text_area("Your Answer")
    
    # Submit button for the form
    submit_answer = st.form_submit_button("Submit Answer")

# Submit form data to the database
if submit_answer:
    if name and phone and user_answer and center_name != "Select a center":
        c.execute('''
            INSERT INTO answers (question, answer, name, phone, center_name, state) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (selected_unanswered_question, user_answer, name, phone, center_name, state))
        conn.commit()
        st.success("Thank you! Your answer has been submitted.")
    else:
        st.error("Please fill out all the fields.")

# Section to Display Questions with Answers
st.markdown('<h1 style="color: teal;">Ask Your Question & Get Answer in Your Own Language</h1>', unsafe_allow_html=True)

# Dropdown to select a question with an answer
selected_answered_question = st.selectbox("Select a question", answered_df['question'], key="answered_questions")
answered_question_row = answered_df[answered_df['question'] == selected_answered_question].iloc[0]

col1, col2 = st.columns(2)
with col1:
    st.write(f"**Question:** {answered_question_row['question']}")
    st.write(f"**Answer:** {answered_question_row['answer']}")

# Display image if available
with col2:
    if pd.notna(answered_question_row['picpath']) and os.path.exists(answered_question_row['picpath']):
        try:
            image = Image.open(answered_question_row['picpath'])
            st.image(image, caption="Related Image", use_column_width=True)
        except Exception as e:
            st.write(f"Error loading image: {e}")
    else:
        st.write("")

# Language Translation and Voice Output
st.markdown('<h1 style="color: teal;">Select Language for Translation and Voice Output</h1>', unsafe_allow_html=True)
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
st.markdown('<h1 style="color: teal;">Contact Us via WhatsApp</h1>', unsafe_allow_html=True)
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

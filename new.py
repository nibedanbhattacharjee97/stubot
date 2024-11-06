import streamlit as st
import pandas as pd
import sqlite3
import re
from PIL import Image
from gtts import gTTS
from googletrans import Translator
import io
import os

# Load questions from Excel file
questions_df = pd.read_excel("From.xlsx")
questions = questions_df['Question'].tolist()

# Load center-state mapping from Statewise_center.xlsx
center_state_file = 'Statewise_center.xlsx'
center_data = pd.read_excel(center_state_file)
center_data.columns = ['Center Name', 'State']
center_state_mapping = dict(zip(center_data['Center Name'], center_data['State']))

# Set up SQLite database connection
conn = sqlite3.connect('respons.db')
cursor = conn.cursor()

# Create the base table with columns for Name, Mobile_Number, center_code, and State
cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS respons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT,
        Mobile_Number TEXT,
        center_code TEXT,
        State TEXT
    )
''')
conn.commit()

# Function to check if a column exists in the table
def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column[1] == column_name for column in columns)

# Sanitize and add columns for each question if they don’t already exist
def sanitize_column_name(column_name):
    column_name = re.sub(r'[^a-zA-Z0-9_]', '_', column_name)
    return column_name[:50]

for question in questions:
    column_name = sanitize_column_name(question)
    if not column_exists(cursor, 'respons', column_name):
        cursor.execute(f"ALTER TABLE respons ADD COLUMN \"{column_name}\" TEXT")
        conn.commit()

# Streamlit form layout
st.image("Anudip_care_Update_photo.jpg")
st.title("Survey")

# Center Code dropdown and State display outside of the form to trigger dynamic changes
center_code = st.selectbox("Center Code", list(center_state_mapping.keys()))
state = center_state_mapping.get(center_code, "")
state_input = st.text_input("State", value=state, disabled=True)

# Streamlit form layout
with st.form("survey_form"):
    name = st.text_input("Name")
    mobile_number = st.text_input("Mobile Number", max_chars=10)
    answers = {}
    for question in questions:
        answer = st.text_input(question)
        answers[sanitize_column_name(question)] = answer
    submitted = st.form_submit_button("Submit")
    if submitted:
        columns = ['Name', 'Mobile_Number', 'State', 'center_code'] + list(answers.keys())
        values = [name, mobile_number, state, center_code] + list(answers.values())
        placeholders = ', '.join('?' * len(columns))
        cursor.execute(f'''
            INSERT INTO respons ({', '.join(columns)})
            VALUES ({placeholders})
        ''', values)
        conn.commit()
        st.success("Thank you! Your response has been recorded.")

# Fetch data from the database
def fetch_data_from_db():
    query = "SELECT * FROM respons"
    df = pd.read_sql(query, conn)
    return df

st.write("---")
st.markdown('<h1 style="color: teal; font-size: 26px;">Ask Your Question & Get Answer in Your Own Language</h1>', unsafe_allow_html=True)

answered_df = pd.read_excel("questions_answers.xlsx")
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

# Language Translation and Voice Output
st.markdown('<h1 style="color: teal;font-size: 26px;">Select Language for Translation and Voice Output</h1>', unsafe_allow_html=True)
language_options = {"English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te", "Marathi": "mr"}
selected_language = st.selectbox("Choose language", list(language_options.keys()), key="language")
translator = Translator()
translated_question = translator.translate(answered_question_row['question'], dest=language_options[selected_language]).text if selected_language != "English" else answered_question_row['question']
translated_answer = translator.translate(answered_question_row['answer'], dest=language_options[selected_language]).text if selected_language != "English" else answered_question_row['answer']
st.write(f"**Translated Question ({selected_language}):** {translated_question}")
st.write(f"**Translated Answer ({selected_language}):** {translated_answer}")

text_to_speak = f"Question: {translated_question}. Answer: {translated_answer}"
tts = gTTS(text_to_speak, lang=language_options[selected_language])
audio_file_path = 'question_answer_audio.mp3'
tts.save(audio_file_path)
st.audio(audio_file_path, format='audio/mp3')

# WhatsApp Contact Section
st.write("---")
st.markdown('<h1 style="color: teal;font-size: 26px;">Contact Us via WhatsApp</h1>', unsafe_allow_html=True)
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

# Password-protected Download Section
st.write("---")
st.markdown('<h1 style="color: teal;font-size: 26px;">Download Data</h1>', unsafe_allow_html=True)
password = st.text_input("Enter Password", type="password")
if st.button("Download Data"):
    if password == "monitaring_stu_bot@1234":
        data_df = fetch_data_from_db()
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            data_df.to_excel(writer, index=False, sheet_name='Answers')
        excel_buffer.seek(0)
        st.download_button(
            label="Download answers data as Excel",
            data=excel_buffer,
            file_name="answers_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Incorrect password. Please try again.")

# Adding BookslotDetails Form link
Review_link = "[Click Here To Give A Review](https://www.google.com/search?q=anudip&oq=anudip&gs_lcrp=EgZjaHJvbWUyBggAEEUYOTIGCAEQRRhBMgYIAhBFGDwyEAgDEC4YxwEYsQMY0QMYgAQyBwgEEAAYgAQyBwgFEAAYgAQyBggGEEUYPDIGCAcQRRhB0gEIMzkxM2owajeoAgiwAgE&sourceid=chrome&ie=UTF-8#lrd=0x3a0275c462a37a3b:0x567fb1841feeba1a,3,,,,)"
st.markdown(Review_link, unsafe_allow_html=True)

conn.close()

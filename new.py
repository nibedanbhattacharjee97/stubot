import streamlit as st
import pandas as pd
from PIL import Image
import os
from gtts import gTTS
from googletrans import Translator
import sqlite3
import io

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('answers_db.db')
c = conn.cursor()

# Create the table for storing user-submitted answers if it doesn't already exist
c.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT,
        name TEXT,
        phone TEXT
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

# Section 1: Display Questions and Answers (only questions with answers)
st.markdown("""
    <style>
    .custom-title {
        font-size:25px;
        color: Teal;
        font-weight: normal;
    }
    </style>
    """, unsafe_allow_html=True)

# Displaying the title for Question & Answer
st.markdown('<h1 class="custom-title">Please Ask Your Question & Get Answer In Your Own Language</h1>', unsafe_allow_html=True)

selected_answered_question = st.selectbox("Select a question", answered_df['question'], key="answered_questions")

# Display selected question and its answer
answered_question_row = answered_df[answered_df['question'] == selected_answered_question].iloc[0]
col1, col2 = st.columns(2)

with col1:
    st.write(f"**Question:** {answered_question_row['question']}")
    st.write(f"**Answer:** {answered_question_row['answer']}")

# Display image if available and valid path exists
with col2:
    if pd.notna(answered_question_row['picpath']) and isinstance(answered_question_row['picpath'], str) and os.path.exists(answered_question_row['picpath']):
        try:
            image = Image.open(answered_question_row['picpath'])
            st.image(image, caption="Related Image", use_column_width=True)
        except Exception as e:
            st.write(f"Error loading image: {e}")
    else:
        st.write("")

# Section for Language Translation and Voice Output
st.markdown('<h1 class="custom-title">Select Language for Translation and Voice Output</h1>', unsafe_allow_html=True)
language_options = {"English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te", "Marathi": "mr"}
selected_language = st.selectbox("Choose language", list(language_options.keys()), key="language")

# Translator initialization
translator = Translator()

# Translate question and answer to the selected language if not English
if selected_language != "English":
    translated_question = translator.translate(answered_question_row['question'], dest=language_options[selected_language]).text
    translated_answer = translator.translate(answered_question_row['answer'], dest=language_options[selected_language]).text
else:
    translated_question = answered_question_row['question']
    translated_answer = answered_question_row['answer']

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

# Create two columns: one for the answer submission form and one for the download section
col1, col2 = st.columns([2, 1])  # Adjust the column widths as needed

# Column 1: Answer submission form
with col1:
    st.markdown('<h1 class="custom-title">Submit Your Answer</h1>', unsafe_allow_html=True)
    st.write("If an answer is missing, you can provide your answer below:")

    selected_unanswered_question = st.selectbox("Select a question to answer", unanswered_df['question'], key="unanswered_questions")

    # Create two columns for "Your Name" and "Your Phone Number"
    col_a, col_b = st.columns([1, 1])  # First row with two columns

    # Create three columns for the input form
    with st.form("answer_form"):
        # First row for name and phone number
        with col_a:
            name = st.text_input("Your Name")
        with col_b:
            phone = st.text_input("Your Phone Number")
        
        # Second row for answer (full width)
        user_answer = st.text_area("Your Answer")
        
        submit_answer = st.form_submit_button("Submit Answer")

    # If user submits the form, save the answer to the database
    if submit_answer:
        if name and phone and user_answer:
            c.execute('''
                INSERT INTO answers (question, answer, name, phone) 
                VALUES (?, ?, ?, ?)
            ''', (selected_unanswered_question, user_answer, name, phone))
            conn.commit()
            st.success("Thank you! Your answer has been submitted.")
        else:
            st.error("Please fill out all the fields.")

# Column 2: Download section
with col2:
    st.write("---")  # Separator line
    st.markdown('<h1 class="custom-title">Download Submitted Answers</h1>', unsafe_allow_html=True)

    # Function to retrieve the data from the database for download
    def get_data():
        query = '''
            SELECT question, answer, name, phone FROM answers
        '''
        data = pd.read_sql(query, conn)
        return data

    # Retrieve the data from the database
    data = get_data()

    # Download button for CSV
    csv_data = data.to_csv(index=False)
    st.download_button(
        label="Download data as CSV",
        data=csv_data,
        file_name='submitted_answers.csv',
        mime='text/csv'
    )

    # Download button for Excel
    excel_data = io.BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        data.to_excel(writer, index=False)
    excel_data.seek(0)

# Contact Us via WhatsApp Section
st.write("---")
st.markdown('<h1 class="custom-title">Contact Us via WhatsApp</h1>', unsafe_allow_html=True)

# WhatsApp details
whatsapp_numbers = [
    {"number": "9147394695", "language": "English"},
    {"number": "9147394695", "language": "Hindi"},
    {"number": "9147394695", "language": "Bengali"},
    {"number": "7595063323", "language": "Tamil"},
    {"number": "6293415105", "language": "Telugu"}
]
whatsapp_message = "Hi Anu! I Have a Query."
whatsapp_logo_path = "whatsapp_logo.png"

# Create columns for WhatsApp contacts
col1, col2, col3, col4, col5 = st.columns(5)

# Check if logo file exists
if os.path.exists(whatsapp_logo_path):
    for idx, col in enumerate([col1, col2, col3, col4, col5]):
        with col:
            st.image(whatsapp_logo_path, caption=f"WhatsApp For {whatsapp_numbers[idx]['language']}", use_column_width=False, width=50)
            whatsapp_url = f"https://api.whatsapp.com/send?phone=91{whatsapp_numbers[idx]['number']}&text={whatsapp_message}"
            st.markdown(f'<a href="{whatsapp_url}" target="_blank">WhatsApp</a>', unsafe_allow_html=True)
else:
    st.error("WhatsApp logo not found. Please check the path.")

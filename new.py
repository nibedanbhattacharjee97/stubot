import streamlit as st
import pandas as pd
import sqlite3
from gtts import gTTS
from googletrans import Translator
import os
import io
from PIL import Image

# Set up SQLite database connection
db_name = 'new_respons.db'
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# Create a simplified table for Name and CMIS Register Mobile Number
cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS respons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Mobile_Number TEXT NOT NULL
    )
''')
conn.commit()

# Streamlit layout
st.image("Anudip_care_Update_photo.jpg")

# Streamlit layout

st.markdown('<h1 style="color: teal; font-size: 26px;"></h1>', unsafe_allow_html=True)
# Create two columns for Name and Mobile Number inputs
col1, col2 = st.columns(2)

with st.form("entry_form"):
    with col1:
        name = st.text_input("Name")
    with col2:
        mobile_number = st.text_input("CMIS Register Mobile Number (10 digits)", max_chars=10)
    submitted = st.form_submit_button("Submit")
    
    if submitted:
        if not name or not mobile_number:
            st.error("Both Name and Mobile Number are required.")
        elif len(mobile_number) != 10 or not mobile_number.isdigit():
            st.error("Please enter a valid 10-digit mobile number.")
        else:
            cursor.execute('''
                INSERT INTO respons (Name, Mobile_Number)
                VALUES (?, ?)
            ''', (name, mobile_number))
            conn.commit()
            st.success("Your information has been successfully recorded!")

# Fetch data from the database
def fetch_data_from_db():
    query = "SELECT * FROM respons"
    df = pd.read_sql(query, conn)
    return df

st.write("---")
st.markdown('<h1 style="color: teal; font-size: 26px;">Ask Your Question & Get Answer in Your Own Language</h1>', unsafe_allow_html=True)

# Display question and answer
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
st.markdown('<h1 style="color: teal;font-size: 26px;">Select Your Language</h1>', unsafe_allow_html=True)
language_options = {"English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te", "Marathi": "mr","Kannada": "kn", "Gujarati": "gu", "Malayalam": "ml", "Punjabi": "pa", "Urdu": "ur"}
selected_language = st.selectbox("Choose language", list(language_options.keys()), key="language")
translator = Translator()
translated_question = translator.translate(answered_question_row['question'], dest=language_options[selected_language]).text if selected_language != "English" else answered_question_row['question']
translated_answer = translator.translate(answered_question_row['answer'], dest=language_options[selected_language]).text if selected_language != "English" else answered_question_row['answer']
st.write(f"**Translated Question ({selected_language}):** {translated_question}")
st.write(f"**Translated Answer ({selected_language}):** {translated_answer}")

# Convert text to speech
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
    {"number": "9147394695", "language": "Tamil"},
    {"number": "9147394695", "language": "Telugu"}
]
whatsapp_message = "Hi There! Please ask your question here. I am available from 10:30 AM to 5:30 PM."
whatsapp_logo_path = "whatsapp_logo.png"
cols = st.columns(5)
if os.path.exists(whatsapp_logo_path):
    for idx, col in enumerate(cols):
        with col:
            st.image(whatsapp_logo_path, caption=f"WhatsApp For {whatsapp_numbers[idx]['language']}", use_column_width=False, width=50)
            whatsapp_url = f"https://api.whatsapp.com/send?phone=91{whatsapp_numbers[idx]['number']}&text={whatsapp_message}"
            st.markdown(f'<a href="{whatsapp_url}" target="_blank">WhatsApp</a>', unsafe_allow_html=True)


st.write("---")
st.markdown('<h1 style="color: teal;font-size: 26px;">Chat Timing - 10:30am - 5:30pm (On Official Days)</h1>', unsafe_allow_html=True)



 #Password-protected Download Section
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

# Adding Review Form link
Review_link = "[Click Here To Give A Review](https://www.google.com/search?q=Anudip&rlz=1C1GCEU_enIN1160IN1160&oq=Anudip&gs_lcrp=EgZjaHJvbWUyBggAEEUYOTIGCAEQRRhBMhAIAhAuGMcBGLEDGNEDGIAEMg0IAxAuGK8BGMcBGIAEMgYIBBBFGDsyBggFEEUYPDIGCAYQRRg8MgYIBxBFGEHSAQg3OTM1ajBqN6gCCLACAfEFJAkb0IMSV7_xBSQJG9CDEle_&sourceid=chrome&ie=UTF-8&lqi=CgZBbnVkaXAiA4gBAUiJ25-a5oCAgAhaDBAAGAAiBmFudWRpcJIBHW5vbl9nb3Zlcm5tZW50YWxfb3JnYW5pemF0aW9uqgFKCg0vZy8xMWozMGJoNGM4EAEqCiIGYW51ZGlwKAAyHxABIhsnliKrkyGIpHoRhlZBDAwUu9v1f28C7WLNhz4yChACIgZhbnVkaXA#lkt=LocalPoiReviews&rlimm=6232895590333594138&lrd=0x3a0275c462a37a3b:0x567fb1841feeba1a,3,,,,)"
st.markdown(Review_link, unsafe_allow_html=True)

# Close the database connection
conn.close()

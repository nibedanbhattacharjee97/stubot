import streamlit as st
import pandas as pd
from PIL import Image
import os
from io import BytesIO
from gtts import gTTS  # Import gTTS for text-to-speech
from googletrans import Translator  # Import Google Translate API

# Load the Excel file containing questions and answers
excel_file = 'questions_answers.xlsx'
df = pd.read_excel(excel_file)

# Sidebar for browsing questions
st.sidebar.title("Related Questions")
selected_question = st.sidebar.selectbox("Select a question", df['question'])

# Display selected question and answer
question_row = df[df['question'] == selected_question].iloc[0]
st.write(f"**Question:** {question_row['question']}")
st.write(f"**Answer:** {question_row['answer']}")

# Display image if available and valid path exists
if question_row['picpath'] and os.path.exists(question_row['picpath']):
    image = Image.open(question_row['picpath'])
    st.image(image, caption="Related Image", use_column_width=True)
else:
    st.write("No image available for this question.")

# Language selection for text-to-speech
st.sidebar.title("Select Language for Translation and Voice Output")
language_options = {"English": "en", "Hindi": "hi", "Bengali": "bn"}
selected_language = st.sidebar.selectbox("Choose language", list(language_options.keys()))

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

# Use gTTS to convert the translated text to speech in the selected language
language_code = language_options[selected_language]
tts = gTTS(text_to_speak, lang=language_code)
audio_file_path = 'question_answer_audio.mp3'
tts.save(audio_file_path)

# Display an audio player for the user to listen to the translated question and answer
st.audio(audio_file_path, format='audio/mp3')

# Section for new student entry if no question is available
st.sidebar.write("---")
st.sidebar.title("Submit Your Own Question")
st.sidebar.write("If the question is not available, please submit your details below:")

# Ensure the uploaded_images directory exists
upload_directory = "uploaded_images"
if not os.path.exists(upload_directory):
    os.makedirs(upload_directory)

# Form for student details
with st.sidebar.form(key="student_form"):
    name = st.text_input("Name")
    question = st.text_input("Question")
    pic = st.file_uploader("Upload an Image (optional)", type=["jpg", "jpeg", "png"])
    phone = st.text_input("Phone Number")
    
    # Submit button
    submitted = st.form_submit_button("Submit")

# Handle the submitted data
if submitted:
    # Save the uploaded image if provided, and display it directly
    if pic:
        # Display image directly in Streamlit
        st.image(pic, caption="Uploaded Image", use_column_width=True)

        # Save the image to memory
        img_bytes = pic.read()
        img = Image.open(BytesIO(img_bytes))

        # Save the image file to the upload directory
        pic_path = os.path.join(upload_directory, pic.name)
        img.save(pic_path)
    else:
        pic_path = None

    # Create a new entry
    new_entry = {
        "Name": name,
        "Question": question,
        "Pic": pic.name if pic else None,
        "Ph No": phone
    }
    
    # Append to the existing Excel file
    new_data_df = pd.DataFrame([new_entry])
    
    # Check if the file exists and append the data
    if os.path.exists('submitted_questions.xlsx'):
        with pd.ExcelWriter('submitted_questions.xlsx', mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
            new_data_df.to_excel(writer, index=False, header=False, startrow=writer.sheets['Sheet1'].max_row, sheet_name='Sheet1')
    else:
        new_data_df.to_excel('submitted_questions.xlsx', index=False, sheet_name='Sheet1')

    st.sidebar.success("Your data has been submitted successfully!")

# Display the submitted details if available
if submitted:
    st.write(f"**Name:** {name}")
    st.write(f"**Question:** {question}")
    st.write(f"**Phone Number:** {phone}")
    if pic:
        st.image(pic, caption="Uploaded Image", use_column_width=True)
    else:
        st.write("No image uploaded.")

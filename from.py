import streamlit as st
import pandas as pd
import sqlite3

# Load questions from Excel file
questions_df = pd.read_excel("From.xlsx")  # Load the Excel file
questions = questions_df['Question'].tolist()  # Assuming 'Question' column has the questions

# Set up SQLite database connection
conn = sqlite3.connect('responses.db')
cursor = conn.cursor()

# Create the base table with columns for Name, Mobile_Number, and State
cursor.execute('''
    CREATE TABLE IF NOT EXISTS responses (
        Name TEXT,
        Mobile_Number INTEGER,
        State TEXT
    )
''')
conn.commit()

# Function to check if a column exists in the table
def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column[1] == column_name for column in columns)

# Add columns for each question if they don’t already exist
for question in questions:
    column_name = question.replace(" ", "_").replace("?", "").replace("-", "_")
    
    if not column_exists(cursor, 'responses', column_name):
        # Ensure the column name is wrapped in double quotes to avoid issues with special characters
        cursor.execute(f"ALTER TABLE responses ADD COLUMN \"{column_name}\" TEXT")
        conn.commit()

# Streamlit form layout
st.title("Google Form-like Survey")
with st.form("survey_form"):
    # Basic user information fields
    name = st.text_input("Name")
    mobile_number = st.text_input("Mobile Number", max_chars=10)
    state = st.text_input("State")

    # Collect answers for each question
    answers = {}
    for question in questions:
        answer = st.text_input(question)
        answers[question] = answer

    # Submit button
    submitted = st.form_submit_button("Submit")
    if submitted:
        # Prepare column names and values for SQL insertion
        columns = ['Name', 'Mobile_Number', 'State'] + [q.replace(" ", "_").replace("?", "").replace("-", "_") for q in questions]
        values = [name, mobile_number, state] + list(answers.values())
        
        # Insert data into the database
        placeholders = ', '.join('?' * len(columns))
        cursor.execute(f'''
            INSERT INTO responses ({', '.join(columns)})
            VALUES ({placeholders})
        ''', values)
        conn.commit()
        st.success("Thank you! Your responses have been recorded.")

conn.close()

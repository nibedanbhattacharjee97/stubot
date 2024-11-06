import streamlit as st
import pandas as pd
import sqlite3
import re

# Load questions from Excel file
questions_df = pd.read_excel("From.xlsx")  # Load the Excel file
questions = questions_df['Question'].tolist()  # Assuming 'Question' column has the questions

# Load center-state mapping from Statewise_center.xlsx
statewise_df = pd.read_excel("Statewise_center.xlsx")  # Load the Excel file
center_state_mapping = dict(zip(statewise_df['Center Name'], statewise_df['State']))

# Set up SQLite database connection
conn = sqlite3.connect('respons.db')
cursor = conn.cursor()

# Create the base table with columns for Name, Mobile_Number, and State
cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS respons (
        Name TEXT,
        Mobile_Number INTEGER,
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
    column_name = re.sub(r'[^a-zA-Z0-9_]', '_', column_name)  # Replace special characters with '_'
    return column_name[:50]  # Truncate to 50 characters to avoid SQLite limits

for question in questions:
    column_name = sanitize_column_name(question)
    
    if not column_exists(cursor, 'respons', column_name):
        cursor.execute(f"ALTER TABLE respons ADD COLUMN \"{column_name}\" TEXT")
        conn.commit()

# Streamlit form layout
st.title("Google Form-like Survey")

# Center Code dropdown and State display outside of the form to trigger dynamic changes
center_code = st.selectbox("Center Code", list(center_state_mapping.keys()))  # Dropdown for Center Code
state = center_state_mapping.get(center_code, "")  # Get the state for the selected center code

# Display the state dynamically (read-only)
state_input = st.text_input("State", value=state, disabled=True)

# Streamlit form layout
with st.form("survey_form"):
    # Basic user information fields
    name = st.text_input("Name")
    mobile_number = st.text_input("Mobile Number", max_chars=10)

    # Collect answers for each question
    answers = {}
    for question in questions:
        answer = st.text_input(question)
        answers[sanitize_column_name(question)] = answer  # Use sanitized column names

    # Submit button
    submitted = st.form_submit_button("Submit")
    if submitted:
        # Prepare column names and values for SQL insertion
        columns = ['Name', 'Mobile_Number', 'State', 'center_code'] + list(answers.keys())
        values = [name, mobile_number, state, center_code] + list(answers.values())
        
        # Insert data into the database
        placeholders = ', '.join('?' * len(columns))
        cursor.execute(f'''
            INSERT INTO respons ({', '.join(columns)})
            VALUES ({placeholders})
        ''', values)
        conn.commit()
        st.success("Thank you! Your response has been recorded.")

conn.close()

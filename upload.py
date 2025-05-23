import streamlit as st
import pandas as pd
import sqlite3

# Database setup
conn = sqlite3.connect('new_respons.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS respons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Mobile_Number TEXT NOT NULL
    )
''')
conn.commit()

st.title("Upload Excel to Database")

# File uploader
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Read Excel file
        df = pd.read_excel(uploaded_file)

        # Show preview
        st.write("Excel Preview:")
        st.dataframe(df)

        # Ensure necessary columns exist
        if 'Name' in df.columns and 'Mobile_Number' in df.columns:
            df = df[['Name', 'Mobile_Number']]
            df['Mobile_Number'] = df['Mobile_Number'].astype(str).str.strip()

            # Insert into database
            df.to_sql('respons', conn, if_exists='append', index=False)
            st.success("Data uploaded to the 'respons' table successfully.")
        else:
            st.error("Excel must contain 'Name' and 'Mobile_Number' columns.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

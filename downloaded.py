import streamlit as st
import pandas as pd
import sqlite3
import io

# Function to fetch data from the SQLite DB
def fetch_data_from_db():
    conn = sqlite3.connect('new_respons.db')
    df = pd.read_sql_query("SELECT * FROM respons", conn)
    conn.close()
    return df

# Title
st.markdown('<h1 style="color: teal;font-size: 26px;">Download Responses Data</h1>', unsafe_allow_html=True)

# Fetch data
data_df = fetch_data_from_db()

# Convert to Excel in memory
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
    data_df.to_excel(writer, index=False, sheet_name='Responses')
excel_buffer.seek(0)

# Download button
st.download_button(
    label="📥 Download responses data as Excel",
    data=excel_buffer,
    file_name="new_respons_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

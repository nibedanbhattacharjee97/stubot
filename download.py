import pandas as pd
import sqlite3
import io

# Function to create and populate the SQLite database
def create_database():
    conn = sqlite3.connect('updated_new_db')
    c = conn.cursor()
    
    # Create the table for storing answers if it doesn't already exist
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
    
    # Sample data to populate the database
    sample_data = [
        ("What is Python?", "Python is a programming language.", "Alice", "1234567890", "Center A", "State A"),
        ("What is SQLite?", "SQLite is a database engine.", "Bob", "0987654321", "Center B", "State B"),
    ]
    
    # Insert sample data into the answers table
    c.executemany('''
        INSERT INTO answers (question, answer, name, phone, center_name, state)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_data)
    
    conn.commit()
    conn.close()
    print("Database created and populated with sample data.")

# Function to download data to an Excel file
def download_data_to_excel():
    # Connect to the SQLite database
    conn = sqlite3.connect('updated_new_db')
    
    # Fetch all data from the 'answers' table
    query = "SELECT * FROM answers"
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Convert the DataFrame to an Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Answers')
    
    # Return the Excel file for download
    output.seek(0)
    return output

# Create the database and populate it with sample data
create_database()

# Download the data to an Excel file
excel_data = download_data_to_excel()

# Save the Excel data to a file
with open("answers_data.xlsx", "wb") as f:
    f.write(excel_data.read())

print("Data downloaded to answers_data.xlsx.")

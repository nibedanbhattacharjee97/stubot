import pandas as pd
import sqlite3

def fetch_all_data(database_path):
    """Fetch all records from the answers table in the SQLite database."""
    conn = sqlite3.connect(database_path)
    try:
        # Use pd.read_sql_query to fetch all records from the answers table
        data = pd.read_sql_query("SELECT * FROM answers", conn)
    finally:
        conn.close()  # Ensure the connection is closed
    return data

def save_to_csv(data, output_file):
    """Save the DataFrame to a CSV file."""
    data.to_csv(output_file, index=False)
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    database_path = 'updated_new_db'  # Path to your SQLite database
    output_file = 'answers_data.csv'   # Output CSV file name

    # Fetch data and save it
    all_data = fetch_all_data(database_path)
    
    # Check if there is any data before saving
    if not all_data.empty:
        save_to_csv(all_data, output_file)
    else:
        print("No data found in the answers table.")

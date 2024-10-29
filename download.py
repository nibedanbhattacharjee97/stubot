import pandas as pd
import sqlite3

# Connect to SQLite database
conn = sqlite3.connect('updated_new_db_data')

# Query the answers table
query = 'SELECT * FROM answers'
df = pd.read_sql_query(query, conn)

# Specify the output Excel file name
output_file = 'answers_data.xlsx'

# Export DataFrame to Excel
df.to_excel(output_file, index=False)

# Close the database connection
conn.close()

print(f'Data has been exported to {output_file}')

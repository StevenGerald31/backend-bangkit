import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Muat variabel dari file .env
load_dotenv()

def create_db_connection():
    try:
        # Ambil nilai dari environment variables
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        if connection.is_connected():
            print("Connection to MySQL database was successful.")
        return connection
    except Error as e:
        print(f"Error: '{e}'")
        return None
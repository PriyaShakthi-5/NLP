import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error as MySQLError

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'medi_extract',
    'port': 3307,
    'autocommit': True,
}


def _query_db(sql, params=(), fetch=False, fetchone=False):
    """Helper to handle XAMPP MySQL connection, query execution, and auto-close."""
    # Convert SQLite "?" placeholders to MySQL "%s" placeholders
    sql = sql.replace('?', '%s')
    with mysql.connector.connect(**DB_CONFIG) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        if fetchone:
            row = cursor.fetchone()
            return row
        return cursor.fetchall() if fetch else cursor.lastrowid


def save_prescription_result(filename, extracted_text, extracted_fields, accuracy):
    """Saves extraction results directly to XAMPP MySQL database."""
    sql = '''
        INSERT INTO prescriptions (
            filename, extracted_text, patient_name, medicine, dosage, frequency, duration, strength, accuracy, reviewed, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        filename, extracted_text,
        extracted_fields.get('patient_name', ''),
        extracted_fields.get('medicine', ''),
        extracted_fields.get('dosage', ''),
        extracted_fields.get('frequency', ''),
        extracted_fields.get('duration', ''),
        extracted_fields.get('strength', ''),
        accuracy, 0,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    return _query_db(sql, params)


def init_db():
    """Initializes the database and prescriptions table in XAMPP MySQL."""
    try:
        config_no_db = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
        with mysql.connector.connect(**config_no_db) as conn:
            conn.cursor().execute('CREATE DATABASE IF NOT EXISTS medi_extract')
        
        # Create MySQL Table
        with mysql.connector.connect(**DB_CONFIG) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prescriptions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    filename VARCHAR(255),
                    extracted_text TEXT,
                    patient_name VARCHAR(255),
                    medicine VARCHAR(255),
                    dosage VARCHAR(255),
                    frequency VARCHAR(255),
                    duration VARCHAR(255),
                    strength VARCHAR(255),
                    accuracy FLOAT,
                    reviewed INT DEFAULT 0,
                    created_at VARCHAR(50)
                )
            ''')
            # Auto-migrate column if adding to existing database table
            try:
                cursor.execute('ALTER TABLE prescriptions ADD COLUMN patient_name VARCHAR(255) AFTER extracted_text')
            except MySQLError:
                pass
    except MySQLError as e:
        print(f"Database initialization error: {e}")


def list_prescriptions(query='', limit=None):
    """Retrieves list of records from XAMPP MySQL based on query matching."""
    if query:
        sql = 'SELECT * FROM prescriptions WHERE filename LIKE ? OR patient_name LIKE ? OR medicine LIKE ? OR extracted_text LIKE ? ORDER BY id DESC'
        params = (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')
    else:
        sql, params = 'SELECT * FROM prescriptions ORDER BY id DESC', ()
    rows = _query_db(sql, params, fetch=True)
    return rows[:limit] if limit else rows


def get_prescription(record_id):
    """Retrieves a single prescription record by ID from XAMPP MySQL."""
    return _query_db('SELECT * FROM prescriptions WHERE id = ?', (record_id,), fetchone=True)


def update_prescription(record_id, extracted_fields, accuracy):
    """Updates XAMPP MySQL record values upon human review."""
    sql = 'UPDATE prescriptions SET patient_name = ?, medicine = ?, dosage = ?, frequency = ?, duration = ?, strength = ?, accuracy = ?, reviewed = 1 WHERE id = ?'
    params = (
        extracted_fields.get('patient_name', ''),
        extracted_fields.get('medicine', ''),
        extracted_fields.get('dosage', ''),
        extracted_fields.get('frequency', ''),
        extracted_fields.get('duration', ''),
        extracted_fields.get('strength', ''),
        accuracy, record_id
    )
    _query_db(sql, params)


if __name__ == '__main__':
    init_db()

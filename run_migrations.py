import os
import psycopg2
from psycopg2 import sql

def run_migrations():
    """Run database migrations using direct SQL queries"""
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("DATABASE_URL environment variable not set.")
        return
    
    print("Connecting to database...")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    try:
        # Migration 1: Add department column to User table
        print("Adding department column to User table...")
        cursor.execute("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS department VARCHAR(64) DEFAULT 'general'
        """)
        
        # Migration 2: Update Payroll table with attendance-related columns
        print("Updating Payroll table with attendance columns...")
        cursor.execute("""
            ALTER TABLE payroll 
            ADD COLUMN IF NOT EXISTS attendance_based BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS attendance_salary NUMERIC(10, 2) DEFAULT 0,
            ADD COLUMN IF NOT EXISTS present_days INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS absent_days INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS late_days INTEGER DEFAULT 0
        """)
        
        # Migration 3: Create Attendance table if it doesn't exist
        print("Creating Attendance table if it doesn't exist...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL REFERENCES employee(id),
                date DATE NOT NULL,
                check_in_time TIME,
                check_out_time TIME,
                status VARCHAR(20) DEFAULT 'present',
                remarks VARCHAR(255),
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_employee_attendance_date UNIQUE (employee_id, date)
            )
        """)
        
        # Commit all migrations
        conn.commit()
        print("Database migrations completed successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migrations()
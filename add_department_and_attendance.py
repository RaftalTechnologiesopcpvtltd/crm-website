from app import db, create_app
from sqlalchemy import Column, String, Boolean, Integer, Numeric, Date, Time, Text, UniqueConstraint, ForeignKey
from sqlalchemy.sql import text

def add_department_to_user():
    """Add department column to User table"""
    print("Adding department column to User table...")
    with create_app().app_context():
        db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS department VARCHAR(64) DEFAULT 'general'"))
        db.session.commit()
        print("Department column added to User table.")

def update_payroll_table():
    """Update Payroll table with attendance-related columns"""
    print("Updating Payroll table with attendance columns...")
    with create_app().app_context():
        db.session.execute(text("ALTER TABLE payroll ADD COLUMN IF NOT EXISTS attendance_based BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE payroll ADD COLUMN IF NOT EXISTS attendance_salary NUMERIC(10, 2) DEFAULT 0"))
        db.session.execute(text("ALTER TABLE payroll ADD COLUMN IF NOT EXISTS present_days INTEGER DEFAULT 0"))
        db.session.execute(text("ALTER TABLE payroll ADD COLUMN IF NOT EXISTS absent_days INTEGER DEFAULT 0"))
        db.session.execute(text("ALTER TABLE payroll ADD COLUMN IF NOT EXISTS late_days INTEGER DEFAULT 0"))
        db.session.commit()
        print("Payroll table updated with attendance columns.")

def create_attendance_table():
    """Create Attendance table"""
    print("Creating Attendance table...")
    with create_app().app_context():
        # Check if the table already exists
        exists = db.session.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'attendance')")).scalar()
        
        if not exists:
            db.session.execute(text("""
                CREATE TABLE attendance (
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
            """))
            db.session.commit()
            print("Attendance table created.")
        else:
            print("Attendance table already exists.")

if __name__ == "__main__":
    add_department_to_user()
    update_payroll_table()
    create_attendance_table()
    print("Database migration completed successfully.")
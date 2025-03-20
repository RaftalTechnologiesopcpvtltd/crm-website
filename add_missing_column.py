from app import create_app, db
from sqlalchemy import text

def add_missing_column():
    app = create_app()
    with app.app_context():
        # Check if the column exists
        try:
            # Try to add the column
            db.session.execute(text("ALTER TABLE project_payment ADD COLUMN IF NOT EXISTS is_recorded_in_sales BOOLEAN DEFAULT FALSE"))
            db.session.commit()
            print("Column 'is_recorded_in_sales' added successfully to the project_payment table!")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding column: {e}")

if __name__ == "__main__":
    add_missing_column()
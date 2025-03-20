from app import app, db
from models import User
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_admin_user(username, email, password):
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            print(f"User {username} already exists.")
            # Update admin privileges if needed
            if not existing_user.is_admin:
                existing_user.is_admin = True
                db.session.commit()
                print(f"User {username} has been granted admin privileges.")
            return
        
        # Create a new admin user
        admin_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user {username} created successfully!")

if __name__ == "__main__":
    # Replace these with your desired credentials
    admin_username = "admin"
    admin_email = "admin@example.com"
    admin_password = "admin1234"  # Make sure to use a strong password in production
    
    create_admin_user(admin_username, admin_email, admin_password)
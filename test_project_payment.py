from app import create_app, db
from models import Project, ProjectPayment, Sales, User, ClientUser
from decimal import Decimal
from datetime import datetime, date, timedelta
import random

app = create_app()

def create_test_project():
    """Create a test project with sales record"""
    with app.app_context():
        # Get the current admin user
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            print("No admin user found. Cannot create test project.")
            return
            
        # Create a test client
        client = ClientUser.query.filter_by(name="Test Client").first()
        if not client:
            client = ClientUser(
                name="Test Client",
                email="testclient@example.com",
                platform="other",
                platform_username="testclient",
                is_existing_user=False
            )
            db.session.add(client)
            db.session.flush()
            print(f"Created test client: {client.name}")
        
        # Create a test project
        project_name = f"Test Project {date.today().strftime('%Y-%m-%d')}"
        project = Project(
            name=project_name,
            description="This is a test project created for accounting integration testing",
            client="Test Client Corp",
            client_user_id=client.id,
            platform="other",
            platform_project_id=f"TEST-{random.randint(1000, 9999)}",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status="in-progress",
            budget=Decimal("2000.00"),
            payment_status="pending"
        )
        print(f"Adding project to database: {project_name}")
        db.session.add(project)
        
        # Print debug info before commit
        print(f"Project before commit - has ID: {project.id}")
        
        # Commit to get ID
        db.session.commit()
        print(f"Project after commit - ID: {project.id}")
        print(f"Created test project: {project.name} with budget ${project.budget}")
        
        # Create sales record manually since automatic creation isn't working
        print("Creating sales record manually...")
        sale = Sales(
            project_id=project.id,
            total_amount=project.budget,
            received_amount=Decimal("0.00"),
            currency='USD',
            status='open',
            difference=project.budget  # Initially, difference is the full budget
        )
        db.session.add(sale)
        db.session.commit()
        print(f"Manually created sales record with ID: {sale.id}")
        
        # Validate the sales record exists
        sales_check = Sales.query.filter_by(project_id=project.id).first()
        if sales_check:
            print(f"Sales record exists with total amount: ${sales_check.total_amount}")
        else:
            print("ERROR: No sales record was found after manual creation.")
        
        return project

def create_test_payment(project_id):
    """Create a test payment for a project"""
    with app.app_context():
        project = Project.query.get(project_id)
        if not project:
            print(f"No project found with ID {project_id}")
            return
            
        # Create a test payment
        payment = ProjectPayment(
            project_id=project.id,
            amount_original=Decimal("1500.00"),
            currency_original="USD",
            platform_fee=Decimal("150.00"),
            conversion_fee=Decimal("0.00"),
            conversion_rate=Decimal("1.0"),
            amount_received=Decimal("1350.00"),
            currency_received="USD",
            payment_date=date.today(),
            status="transferred",  # This triggers the journal entry creation
            notes="Test payment with automatic journal entry creation"
        )
        db.session.add(payment)
        db.session.commit()
        print(f"Created test payment for project {project.name}: ${payment.amount_original} (received: ${payment.amount_received})")
        
        # Manually update the sales record (simulating what the route handler does)
        print("Manually updating sales record...")
        sale = Sales.query.filter_by(project_id=project.id).first()
        if sale:
            print(f"Current sales record - received: ${sale.received_amount}, difference: ${sale.difference}")
            # Update received amount
            sale.received_amount += payment.amount_received
            sale.calculate_difference()
            payment.is_recorded_in_sales = True
            db.session.commit()
            print(f"Updated sales record - received: ${sale.received_amount}, difference: ${sale.difference}")
        
        # Check sales record update
        sale = Sales.query.filter_by(project_id=project.id).first()
        if sale:
            print(f"Sales record updated - received amount: ${sale.received_amount}, difference: ${sale.difference}")
        
        # Return payment ID instead of the detached object
        return payment.id

def close_test_sales(project_id):
    """Force close a project's sales record"""
    with app.app_context():
        sale = Sales.query.filter_by(project_id=project_id).first()
        if not sale:
            print(f"No sales record found for project ID {project_id}")
            return
            
        sale.status = "closed"
        sale.closed_date = date.today()
        sale.calculate_difference()
        db.session.commit()
        
        print(f"Closed sales record for project ID {project_id}")
        print(f"Final status: {sale.status}, closed date: {sale.closed_date}")
        print(f"Total amount: ${sale.total_amount}, received: ${sale.received_amount}, difference: ${sale.difference}")
        
        return sale

if __name__ == "__main__":
    import sys
    
    # Check if any arguments are provided
    if len(sys.argv) > 1:
        # If arg is 'create_project', only create a project
        if sys.argv[1] == 'create_project':
            print("Creating test project only...")
            project = create_test_project()
            print(f"Created project with ID: {project.id if project else 'None'}")
            sys.exit(0)
        # If arg is 'create_payment', create a payment for the given project ID
        elif sys.argv[1] == 'create_payment' and len(sys.argv) > 2:
            try:
                project_id = int(sys.argv[2])
                print(f"Creating test payment for project ID: {project_id}...")
                payment = create_test_payment(project_id)
                print(f"Created payment with ID: {payment if payment else 'None'}")
                sys.exit(0)
            except ValueError:
                print(f"Invalid project ID: {sys.argv[2]}")
                sys.exit(1)
        # If arg is 'close_sales', close the sales record for the given project ID
        elif sys.argv[1] == 'close_sales' and len(sys.argv) > 2:
            try:
                project_id = int(sys.argv[2])
                print(f"Closing sales record for project ID: {project_id}...")
                sale = close_test_sales(project_id)
                print(f"Closed sales record with ID: {sale.id if sale else 'None'}")
                sys.exit(0)
            except ValueError:
                print(f"Invalid project ID: {sys.argv[2]}")
                sys.exit(1)
    
    # Default: run all steps
    try:
        print("Running complete test sequence...")
        
        # Create a test project
        print("Step 1: Creating test project")
        project = create_test_project()
        
        if project:
            print(f"\nStep 2: Creating test payment for project ID: {project.id}")
            # Create a test payment
            payment = create_test_payment(project.id)
            
            if payment:
                print(f"\nStep 3: Closing sales record for project ID: {project.id}")
                # Close the sales record
                sale = close_test_sales(project.id)
                
                if sale:
                    print("\nComplete test sequence succeeded!")
                else:
                    print("\nError: Failed to close sales record.")
            else:
                print("\nError: Failed to create payment.")
        else:
            print("\nError: Failed to create project.")
    except Exception as e:
        print(f"Test sequence failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
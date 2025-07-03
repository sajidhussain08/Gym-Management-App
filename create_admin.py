from app import db, AdminUser, app

with app.app_context():
    username = "Naveen"
    password = "12345"

    # Check if the admin already exists
    existing_user = AdminUser.query.filter_by(username=username).first()
    if existing_user:
        print(f"Admin user '{username}' already exists.")
    else:
        new_admin = AdminUser(username=username)
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()
        print(f"Admin user '{username}' created successfully.")

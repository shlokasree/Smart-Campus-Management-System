
from getpass import getpass

from pwdlib import PasswordHash

from database import get_connection


password_hash = PasswordHash.recommended()


def main():
    print("\n=== CampusCare Admin Setup ===")

    name = input("Enter admin name: ").strip()
    email = input("Enter admin email: ").strip().lower()
    password = getpass("Enter admin password: ")
    confirm_password = getpass("Confirm admin password: ")

    if not name:
        print("Admin name is required.")
        return

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        print("Please enter a valid email address.")
        return

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, role
            FROM users
            WHERE LOWER(email) = %s
            """,
            (email,)
        )

        existing = cursor.fetchone()

        if existing:
            print(
                f"An account already exists with role "
                f"'{existing['role']}'. No changes were made."
            )
            connection.rollback()
            return

        hashed_password = password_hash.hash(password)

        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (name, email, hashed_password, "admin")
        )

        created_user = cursor.fetchone()
        connection.commit()

        print("\nAdmin account created successfully!")
        print("Admin ID:", created_user["id"])
        print("Admin email:", email)
        print("You can now sign in through CampusCare.")

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print("\nAdmin setup failed:", error)

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()

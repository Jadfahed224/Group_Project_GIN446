"""Server-side validation for sign-up and log-in."""
import re

EMAIL = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")


def validate_signup(form):
 errors = {}
 email = form.get("email", "").strip().lower()
 password = form.get("password", "")
 confirm = form.get("confirm", "")
 if email == "":
    errors["email"] = "Email is required."
 elif len(email) > 120:
    errors["email"] = "Email must be 120 characters or less."
 elif not EMAIL.match(email):
    errors["email"] = "Enter a valid email address."
 if len(password) < 8:
    errors["password"] = "Your password needs at least 8 characters."
 if confirm != password:
    errors["confirm"] = "The two passwords are not the same."
 return errors, email


def validate_login(form):
    errors = {}
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    if email == "":
        errors["email"] = "Email is required."
    if password == "":
        errors["password"] = "Password is required."
    return errors, email


def validate_search(raw):
    """Clean the search text. Returns (error message or None, cleaned text)."""
    text = (raw or "").strip().lower()
    if text == "":
        return "Type a name or a number to search.", text
    if len(text) > 30:
        return "Search text must be 30 characters or less.", text
    return None, text
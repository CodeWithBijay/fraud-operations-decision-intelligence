"""Create a sign-in account for the FraudOps app.

Usage:  python3 scripts/make_user.py <username> <lead|analyst>
It asks for the password (hidden) and prints a block to paste into Streamlit Secrets
(Streamlit Cloud: Manage app > Settings > Secrets; locally: .streamlit/secrets.toml).
Only a salted PBKDF2-SHA256 hash is printed; the password itself is never stored."""
import getpass
import hashlib
import os
import sys

if len(sys.argv) != 3 or sys.argv[2] not in ("lead", "analyst"):
    raise SystemExit("Usage: python3 scripts/make_user.py <username> <lead|analyst>")
user, role = sys.argv[1].strip().lower(), sys.argv[2]
pw = getpass.getpass("Password (at least 8 characters): ")
if len(pw) < 8 or pw != getpass.getpass("Repeat password: "):
    raise SystemExit("Passwords do not match or are shorter than 8 characters. Nothing created.")
salt = os.urandom(16)
digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()
print(f'\n[users.{user}]\nrole = "{role}"\nsalt = "{salt.hex()}"\nhash = "{digest}"\n')

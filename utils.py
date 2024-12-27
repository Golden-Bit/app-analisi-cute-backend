import os
import json
import bcrypt
from fastapi import HTTPException

USERS_FOLDER = "users"  # cartella dove sono i file <username>.json

def verify_credentials(username: str, password: str) -> bool:
    """
    Verifica che l'utente esista e che la password sia corretta.
    Ritorna True o False.
    """
    user_file = os.path.join(USERS_FOLDER, f"{username}.json")
    if not os.path.isfile(user_file):
        return False
    try:
        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        hashed_pw = user_data["hashed_password"].encode("utf-8")
        return bcrypt.checkpw(password.encode("utf-8"), hashed_pw)
    except:
        return False
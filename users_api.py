from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import bcrypt
from typing import Optional, Dict

app = FastAPI(root_path="/api4")

# Configurazione CORS (aperta, modificabile in base alle necessità)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cartella in cui salvare i file utente
USERS_FOLDER = "users"

# Assicuriamoci che la cartella esista
if not os.path.exists(USERS_FOLDER):
    os.makedirs(USERS_FOLDER)


# -----------------------------
# Pydantic Models
# -----------------------------
class UserCreate(BaseModel):
    username: str
    password: str
    # Metadati liberi da associare all'utente
    # (es. email, nome, cognome, preferenze, ecc.)
    metadata: Dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class UpdateUserRequest(BaseModel):
    # L'utente può aggiornare password e/o metadata
    password: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


# -----------------------------
# Helper Functions
# -----------------------------
def get_user_file_path(username: str) -> str:
    """
    Ritorna il path del file JSON di un utente a partire dallo username.
    """
    return os.path.join(USERS_FOLDER, f"{username}.json")


def load_user_data(username: str) -> dict:
    """
    Carica i dati di un utente dal file corrispondente.
    Solleva HTTPException(404) se l'utente non esiste.
    """
    file_path = get_user_file_path(username)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Utente non trovato.")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_user_data(user_data: dict):
    """
    Salva i dati di un utente nel file nominato in base allo username.
    """
    username = user_data["username"]
    file_path = get_user_file_path(username)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(user_data, f, indent=4)


# -----------------------------
# Endpoint: Registrazione
# -----------------------------
@app.post("/register")
def register_user(user: UserCreate):
    """
    Registra un nuovo utente.
    - Crea un file JSON nominato <username>.json
    - Salva l'hash della password e i metadati
    """
    file_path = get_user_file_path(user.username)

    # 1. Verifica che l'utente non esista già
    if os.path.exists(file_path):
        raise HTTPException(
            status_code=409,
            detail="Username già esistente. Scegli un username diverso."
        )

    # 2. Hash della password
    hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())

    # 3. Salva il file
    user_data = {
        "username": user.username,
        "hashed_password": hashed_password.decode("utf-8"),
        "metadata": user.metadata
    }
    save_user_data(user_data)

    return {"message": "Registrazione avvenuta con successo."}


# -----------------------------
# Endpoint: Login
# -----------------------------
@app.post("/login")
def login_user(credentials: LoginRequest):
    """
    Esegue login controllando username e password.
    - Se l'hash coincide, restituisce un messaggio di successo.
    - Altrimenti, solleva HTTPException(401).
    """
    # 1. Carica dati utente
    try:
        user_data = load_user_data(credentials.username)
    except HTTPException:
        # Se l'utente non esiste
        raise HTTPException(status_code=401, detail="Username o password non validi.")

    # 2. Verifica l'hash della password
    hashed_password = user_data["hashed_password"].encode("utf-8")
    if bcrypt.checkpw(credentials.password.encode("utf-8"), hashed_password):
        return {"message": "Login effettuato con successo."}
    else:
        raise HTTPException(status_code=401, detail="Username o password non validi.")


# -----------------------------
# Endpoint: Aggiornamento
# -----------------------------
@app.put("/update/{username}")
def update_user(username: str, updated_data: UpdateUserRequest):
    """
    Aggiorna i dati di un utente.
    È possibile aggiornare la password e/o i metadata.
    """
    # 1. Carica i dati esistenti
    user_data = load_user_data(username)

    # 2. Aggiorna la password (se fornita)
    if updated_data.password is not None:
        new_hashed = bcrypt.hashpw(updated_data.password.encode("utf-8"), bcrypt.gensalt())
        user_data["hashed_password"] = new_hashed.decode("utf-8")

    # 3. Aggiorna i metadata (se forniti)
    if updated_data.metadata is not None:
        # Approccio: unisci i vecchi metadata con quelli nuovi,
        # oppure puoi sostituirli completamente. Qui scegliamo di sostituire:
        user_data["metadata"] = updated_data.metadata

    # 4. Salva i dati aggiornati
    save_user_data(user_data)

    return {
        "message": "Dati aggiornati con successo.",
        "data": user_data
    }


# -----------------------------
# Avvio del server (sviluppo)
# -----------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)

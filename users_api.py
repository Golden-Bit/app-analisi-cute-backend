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
# Pydantic Model per operazioni admin
# -----------------------------
class AdminChangePasswordRequest(BaseModel):
    admin_username: str
    admin_password: str
    new_password: str

# -----------------------------
# Endpoint Admin: Cambio password arbitrario di un utente
# -----------------------------
@app.put("/admin/change_password/{target_username}")
def admin_change_password(target_username: str, req: AdminChangePasswordRequest):
    """
    Permette all'utente admin (username "admin") di cambiare la password di un qualsiasi account.
    Richiede:
      - admin_username: deve essere "admin"
      - admin_password: password corrente dell'admin (verificata tramite hash)
      - new_password: la nuova password da assegnare all'utente target
    """
    # Verifica che l'utente che richiede l'operazione sia "admin"
    if req.admin_username != "admin":
        raise HTTPException(status_code=403, detail="Accesso non autorizzato.")

    # Verifica le credenziali dell'admin
    try:
        admin_data = load_user_data(req.admin_username)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Credenziali admin non valide.")

    if not bcrypt.checkpw(req.admin_password.encode("utf-8"), admin_data["hashed_password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Credenziali admin non valide.")

    # Carica i dati dell'utente target
    try:
        user_data = load_user_data(target_username)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Utente di destinazione non trovato.")

    # Aggiorna la password con il nuovo valore (hashata)
    new_hashed = bcrypt.hashpw(req.new_password.encode("utf-8"), bcrypt.gensalt())
    user_data["hashed_password"] = new_hashed.decode("utf-8")
    save_user_data(user_data)

    return {"message": f"Password dell'utente '{target_username}' cambiata con successo."}


# -----------------------------
# Endpoint Admin: Visualizzazione di tutti gli account
# -----------------------------
@app.get("/admin/accounts")
def get_all_accounts(admin_username: str, admin_password: str):
    """
    Permette all'utente admin (username "admin") di visualizzare tutti gli account e le relative informazioni.
    Le credenziali admin devono essere passate come query parameters.
    """
    # Verifica che l'utente che effettua la richiesta sia "admin"
    if admin_username != "admin":
        raise HTTPException(status_code=403, detail="Accesso non autorizzato.")

    # Verifica le credenziali dell'admin
    try:
        admin_data = load_user_data(admin_username)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Credenziali admin non valide.")

    if not bcrypt.checkpw(admin_password.encode("utf-8"), admin_data["hashed_password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Credenziali admin non valide.")

    # Leggi tutti i file utente nella cartella USERS_FOLDER
    accounts = []
    for filename in os.listdir(USERS_FOLDER):
        if filename.endswith(".json"):
            with open(os.path.join(USERS_FOLDER, filename), "r", encoding="utf-8") as f:
                user_info = json.load(f)
                accounts.append(user_info)

    return {"accounts": accounts}


# -----------------------------
# Endpoint Admin: Eliminazione di un utente
# -----------------------------
@app.delete("/admin/delete/{target_username}")
def admin_delete_user(target_username: str, admin_username: str, admin_password: str):
    """
    Permette all'utente admin (username "admin") di eliminare un qualsiasi account.
    Le credenziali admin devono essere passate come query parameters.

    Esempio di richiesta:
      DELETE /admin/delete/utente_target?admin_username=admin&admin_password=laPasswordAdmin

    Nota: L'admin non può eliminare se stesso.
    """
    # Impedisci che l'admin elimini se stesso (opzionale)
    if target_username == "admin":
        raise HTTPException(status_code=403, detail="L'admin non può eliminare se stesso.")

    # Verifica che chi effettua la richiesta sia "admin"
    if admin_username != "admin":
        raise HTTPException(status_code=403, detail="Accesso non autorizzato.")

    # Verifica le credenziali dell'admin
    try:
        admin_data = load_user_data(admin_username)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Credenziali admin non valide.")

    if not bcrypt.checkpw(admin_password.encode("utf-8"), admin_data["hashed_password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Credenziali admin non valide.")

    # Verifica che l'utente target esista
    file_path = get_user_file_path(target_username)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Utente di destinazione non trovato.")

    # Elimina il file corrispondente all'utente target
    os.remove(file_path)
    return {"message": f"Utente '{target_username}' eliminato con successo."}


# -----------------------------
# Endpoint: Visualizzazione dei dati dell'utente (profilo personale)
# -----------------------------
@app.get("/me")
def get_own_data(username: str, password: str):
    """
    Permette ad un utente di visualizzare i propri dati.
    Verifica le credenziali e, se corrette, restituisce i dati (username e metadata).
    """
    # Carica i dati dell'utente
    try:
        user_data = load_user_data(username)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Utente non trovato.")

    # Verifica le credenziali
    hashed_password = user_data["hashed_password"].encode("utf-8")
    if not bcrypt.checkpw(password.encode("utf-8"), hashed_password):
        raise HTTPException(status_code=401, detail="Credenziali non valide.")

    # Rimuove il campo hashed_password dalla risposta (opzionale)
    user_data.pop("hashed_password", None)

    return {"data": user_data}



# -----------------------------
# Avvio del server (sviluppo)
# -----------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)

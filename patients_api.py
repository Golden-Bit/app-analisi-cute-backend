import os
import json
import bcrypt
from datetime import datetime
from fastapi import FastAPI, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from uuid import uuid4

from utils import verify_credentials  # la tua funzione di verifica password

app = FastAPI(root_path="/api3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modello per una singola anagrafica
class Anagrafica(BaseModel):
    id: str
    nome: str
    cognome: str
    birth_date: str
    address: str
    peso: float
    altezza: float
    gender: str
    skin_types: List[str]
    issues: List[str]
    analysis_history: List[Dict[str, Any]] = []

# ------------------------------------------------------------------------
#  FUNZIONI DI SUPPORTO
# ------------------------------------------------------------------------


def get_user_anagrafiche_file(username: str) -> str:
    """
    Ritorna il path del file anagrafiche per lo user specificato:
    user_data/<username>/anagrafiche.json

    Se la cartella user_data/<username> non esiste, la crea.
    """
    user_folder = os.path.join("user_data", username)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return os.path.join(user_folder, "anagrafiche.json")


def load_user_anagrafiche(username: str) -> List[dict]:
    """
    Carica la lista di anagrafiche dal file dell'utente.
    Se il file non esiste o è vuoto, ritorna lista vuota.
    """
    user_anagrafiche_path = get_user_anagrafiche_file(username)
    if not os.path.isfile(user_anagrafiche_path):
        return []
    try:
        with open(user_anagrafiche_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_all_anagrafiche(username: str):
    if username != "admin":
        return []

    users = []
    for user_file in os.listdir("users"):
        users.append(user_file.replace(".json", ""))

    anagrafiche = []
    for user_name in users:
        anagrafiche.extend(load_user_anagrafiche(user_name))

    return anagrafiche


def save_user_anagrafiche(username: str, anagrafiche_list: List[dict]):
    """
    Salva la lista di anagrafiche nel file dell'utente, in user_data/<username>/anagrafiche.json
    """
    user_anagrafiche_path = get_user_anagrafiche_file(username)
    for anagrafica in anagrafiche_list:
        anagrafica["source_user"] = username
    with open(user_anagrafiche_path, "w", encoding="utf-8") as f:
        json.dump(anagrafiche_list, f, indent=4, ensure_ascii=False)


def verify_admin_credentials(admin_username: str, admin_password: str):
    if admin_username.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Accesso non autorizzato")

    admin_file = os.path.join("users", "admin.json")
    if not os.path.isfile(admin_file):
        raise HTTPException(status_code=401, detail="Credenziali admin non valide")

    try:
        with open(admin_file, "r", encoding="utf-8") as f:
            admin_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Credenziali admin non valide")

    hashed_pw = admin_data.get("hashed_password", "").encode("utf-8")
    if not bcrypt.checkpw(admin_password.encode("utf-8"), hashed_pw):
        raise HTTPException(status_code=401, detail="Credenziali admin non valide")


def paginate_items(items: List[Any], page: int, page_size: int) -> dict:
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "items": items[start:end],
    }
# ------------------------------------------------------------------------


@app.options("/{path_name:path}")
async def options_handler():
    return JSONResponse(status_code=200, content="OK")


# ------------------------------------------------------------------------
#  ENDPOINTS
# ------------------------------------------------------------------------

@app.post("/create_anagrafiche")
async def create_anagrafica(
        new_anagrafica: Anagrafica,
        username: str,
        password: str,
):
    """
    Crea una nuova anagrafica per l'utente 'username' (se i credentials sono validi).
    """
    # 1. Verifica credenziali
    if not verify_credentials(username, password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    # 2. Carica anagrafiche esistenti dell'utente
    anagrafiche = load_user_anagrafiche(username)

    # 3. Aggiungi la nuova anagrafica
    new_record = new_anagrafica.dict()
    if "created_at" not in new_record:
        new_record["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    anagrafiche.append(new_record)

    # 4. Salva
    save_user_anagrafiche(username, anagrafiche)

    return {"message": "Anagrafica creata con successo"}


@app.put("/anagrafiche/{anagrafica_id}", response_model=Anagrafica)
async def update_anagrafica(
        anagrafica_id: str,
        updated_data: Anagrafica,
        username: str,
        password: str,
):
    """
    Aggiorna un'anagrafica esistente per l'utente specificato, tramite ID.
    """
    # 1. Verifica credenziali
    if not verify_credentials(username, password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    # 2. Carica l'elenco anagrafiche di quell'utente
    anagrafiche = load_user_anagrafiche(username)

    # 3. Cerca l'anagrafica da aggiornare
    for idx, an_item in enumerate(anagrafiche):
        if an_item["id"] == anagrafica_id:
            # Sostituisci i campi con quelli nuovi, ma conserva l'ID
            updated_dict = updated_data.dict()
            updated_dict["id"] = anagrafica_id
            if "created_at" in an_item:
                updated_dict["created_at"] = an_item["created_at"]
            if "source_user" in an_item:
                updated_dict["source_user"] = an_item["source_user"]
            anagrafiche[idx] = updated_dict

            # Salva e ritorna
            save_user_anagrafiche(username, anagrafiche)
            return anagrafiche[idx]

    raise HTTPException(status_code=404, detail="Anagrafica non trovata.")


@app.delete("/anagrafiche/{anagrafica_id}", response_model=dict)
async def delete_anagrafica(
    anagrafica_id: str,
    username: str,
    password: str,
):
    """
    Elimina un'anagrafica tramite ID, dal file dell'utente.
    """
    # 1. Verifica credenziali
    if not verify_credentials(username, password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    # 2. Carica l'elenco anagrafiche di quell'utente
    anagrafiche = load_user_anagrafiche(username)

    # 3. Trova e rimuovi l'anagrafica
    for idx, an_item in enumerate(anagrafiche):
        if an_item["id"] == anagrafica_id:
            deleted = anagrafiche.pop(idx)
            save_user_anagrafiche(username, anagrafiche)
            return {"message": "Anagrafica eliminata con successo.", "data": deleted}
    raise HTTPException(status_code=404, detail="Anagrafica non trovata.")


@app.get("/anagrafiche", response_model=List[Anagrafica])
async def get_anagrafiche(
    username: str,
    password: str,
):
    """
    Recupera tutte le anagrafiche dell'utente specificato.
    """
    # 1. Verifica credenziali
    if not verify_credentials(username, password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    if username == "admin":
        anagrafiche = load_all_anagrafiche(username)

        return anagrafiche
    else:
        anagrafiche = load_user_anagrafiche(username)
        return anagrafiche


@app.get("/admin/users/{target_username}/anagrafiche_history")
async def get_user_anagrafiche_history(
    target_username: str,
    admin_username: str,
    admin_password: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
):
    """
    Permette all'admin di recuperare con paginazione le anagrafiche create da uno specifico utente.
    """
    verify_admin_credentials(admin_username, admin_password)

    user_records = load_user_anagrafiche(target_username)
    user_records.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    paginated = paginate_items(user_records, page, page_size)

    return {
        "data": {
            "username": target_username,
            **paginated,
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

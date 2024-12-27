import os
import json
import bcrypt
from fastapi import FastAPI, HTTPException, Form
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


def save_user_anagrafiche(username: str, anagrafiche_list: List[dict]):
    """
    Salva la lista di anagrafiche nel file dell'utente, in user_data/<username>/anagrafiche.json
    """
    user_anagrafiche_path = get_user_anagrafiche_file(username)
    with open(user_anagrafiche_path, "w", encoding="utf-8") as f:
        json.dump(anagrafiche_list, f, indent=4)
# ------------------------------------------------------------------------


@app.options("/{path_name:path}")
async def options_handler():
    return JSONResponse(status_code=200, content="OK")


# ------------------------------------------------------------------------
#  ENDPOINTS
# ------------------------------------------------------------------------

@app.post("/create_anagrafiche")
async def create_anagrafica(
        new_anagrafica: Anagrafica = Form(...),
        username: str = Form(""),
        password: str = Form(""),
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
    anagrafiche.append(new_anagrafica.dict())

    # 4. Salva
    save_user_anagrafiche(username, anagrafiche)

    return {"message": "Anagrafica creata con successo"}


@app.put("/anagrafiche/{anagrafica_id}", response_model=Anagrafica)
async def update_anagrafica(
        anagrafica_id: str,
    updated_data: Anagrafica = Form(...),
        username: str = Form(""),
        password: str = Form(""),
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
            anagrafiche[idx] = updated_dict

            # Salva e ritorna
            save_user_anagrafiche(username, anagrafiche)
            return anagrafiche[idx]

    raise HTTPException(status_code=404, detail="Anagrafica non trovata.")


@app.delete("/anagrafiche/{anagrafica_id}", response_model=dict)
async def delete_anagrafica(
    anagrafica_id: str,
    username: str = Form(""),
    password: str = Form(""),
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
    username: str = Form(""),
    password: str = Form(""),
):
    """
    Recupera tutte le anagrafiche dell'utente specificato.
    """
    # 1. Verifica credenziali
    if not verify_credentials(username, password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    # 2. Carica e restituisci
    anagrafiche = load_user_anagrafiche(username)
    return anagrafiche


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

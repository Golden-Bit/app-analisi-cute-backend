import json
import os
from datetime import datetime

import bcrypt
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Any

from agent.agent_utils import main  # Importiamo la funzione `main` dallo script precedente
from utils import verify_credentials  # Funzione di verifica credenziali (non mostrata qui)

app = FastAPI(
    root_path="/api2"
)

# Configurazione CORS aperto
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permette richieste da qualsiasi origine
    allow_credentials=True,
    allow_methods=["*"],  # Permette tutti i metodi (GET, POST, ecc.)
    allow_headers=["*"],  # Permette tutti gli header
)


# ------------------------------------------------------------------------------
# MODELLI
# ------------------------------------------------------------------------------
class AnalysisRequest(BaseModel):
    """
    Modello per la richiesta di analisi:
    - patient_id: ID del paziente
    - images: lista di immagini in Base64
    """
    patient_id: str
    body_zone: str = "Non specificata"
    images: List[str]  # Lista di immagini in formato Base64


class AnalysisResult(BaseModel):
    """
    Modello per la risposta di analisi:
    - result: dizionario con i risultati dell'analisi
    """
    result: dict  # Risultato parsato come dizionario


# ------------------------------------------------------------------------------
# FUNZIONI UTILI
# ------------------------------------------------------------------------------
def get_user_anagrafiche_file(username: str) -> str:
    """
    Restituisce il percorso del file anagrafiche per lo user specificato:
    user_data/<username>/anagrafiche.json
    """
    user_folder = os.path.join("user_data", username)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return os.path.join(user_folder, "anagrafiche.json")


def load_user_anagrafiche(username: str) -> List[dict]:
    """
    Carica e restituisce l'elenco dei pazienti (anagrafiche)
    dal file user_data/<username>/anagrafiche.json.
    Se il file non esiste o non è leggibile, ritorna una lista vuota.
    """
    anagrafiche_path = get_user_anagrafiche_file(username)
    if not os.path.isfile(anagrafiche_path):
        return []
    try:
        with open(anagrafiche_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_user_anagrafiche(username: str, data: List[dict]):
    """
    Salva l'elenco di pazienti (anagrafiche) nel file
    user_data/<username>/anagrafiche.json.
    """
    anagrafiche_path = get_user_anagrafiche_file(username)
    with open(anagrafiche_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


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
        "items": items[start:end]
    }


def build_user_analysis_history(target_username: str) -> List[dict]:
    patients_data = load_user_anagrafiche(target_username)
    history_items = []

    for patient in patients_data:
        patient_id = patient.get("id")
        patient_name = patient.get("nome")
        patient_surname = patient.get("cognome")

        for entry in patient.get("analysis_history", []):
            history_items.append({
                "nome": patient_name,
                "cognome": patient_surname,
                "source_user": patient.get("source_user") or target_username,
                "patient_label": f"{(patient_name or '').strip()} {(patient_surname or '').strip()}".strip(),
                "patient_ref": patient_id,
                "timestamp": entry.get("timestamp"),
                "result": entry.get("result", {}),
            })

    history_items.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return history_items


def execute_main_with_retries(base64_images, body_zone: str = "Non specificata", max_retries=10):
    """
    Esegue la funzione main (analisi delle immagini) un massimo di `max_retries` volte
    finché non restituisce un risultato valido.
    """
    for attempt in range(max_retries):
        try:
            print(f"Tentativo {attempt + 1} di esecuzione della funzione main...")
            result = main(base64_images, body_zone)
            if result is not None:
                return result
        except Exception as e:
            print(f"Errore durante il tentativo {attempt + 1}: {e}")
    raise ValueError("Impossibile ottenere un risultato valido dopo più tentativi.")


def update_patient_analysis(username: str, patient_id: str, analysis_result: dict):
    """
    Aggiorna il file anagrafiche dell'utente `username` per aggiungere
    il risultato di un'analisi al paziente specificato, creando o aggiornando
    il campo `analysis_history`.

    :param username: nome utente che possiede il file anagrafiche
    :param patient_id: ID del paziente da aggiornare
    :param analysis_result: Risultato dell'analisi da aggiungere
    """
    # Carica i pazienti dal file dell'utente
    patients_data = load_user_anagrafiche(username)

    # Trova il paziente specificato
    patient = next((p for p in patients_data if p.get("id") == patient_id), None)
    if not patient:
        raise ValueError(f"Il paziente con ID {patient_id} non esiste per l'utente {username}.")

    # Aggiungi o aggiorna il campo `analysis_history`
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    analysis_entry = {"timestamp": timestamp, "result": analysis_result}
    if "analysis_history" in patient:
        patient["analysis_history"].append(analysis_entry)
    else:
        patient["analysis_history"] = [analysis_entry]

    # Salva le modifiche nel file
    save_user_anagrafiche(username, patients_data)


# ------------------------------------------------------------------------------
# ENDPOINT
# ------------------------------------------------------------------------------
@app.post("/analyze_skin", response_model=AnalysisResult)
async def analyze_skin(
        username: str,
        password: str,
        request: AnalysisRequest
):
    """
    Endpoint per analizzare lo stato della pelle in base a immagini Base64.
    Richiede credenziali e la request con patient_id e images in Base64.
    """

    print(request.images)
    # Verifica credenziali
    if not verify_credentials(username, password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    try:
        # Esegui la funzione `main` con un massimo di 10 tentativi (come da codice originale)
        result = execute_main_with_retries(request.images, request.body_zone, max_retries=10)

        result["body_zone"] = request.body_zone

        # Aggiorna la storia delle analisi del paziente specificato
        update_patient_analysis(username, request.patient_id, result)

        return {"result": result}

    except FileNotFoundError as e:
        # Se l'utente non ha mai creato un file anagrafiche o manca qualche file
        raise HTTPException(status_code=500, detail=f"Errore file: {e}")
    except ValueError as e:
        # Se il paziente non esiste o la funzione main non ha prodotto un risultato
        raise HTTPException(status_code=404, detail=f"Errore: {e}")
    except Exception as e:
        # Altri errori generici
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/users/{target_username}/analysis_history")
async def get_user_analysis_history(
    target_username: str,
    admin_username: str,
    admin_password: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
):
    """
    Permette all'admin di recuperare lo storico analisi di uno specifico utente con paginazione.
    """
    verify_admin_credentials(admin_username, admin_password)

    history = build_user_analysis_history(target_username)
    paginated = paginate_items(history, page, page_size)

    return {
        "data": {
            "username": target_username,
            **paginated,
        }
    }


# ------------------------------------------------------------------------------
# AVVIO SERVER
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

import json
import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

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


def execute_main_with_retries(base64_images, max_retries=3):
    """
    Esegue la funzione main (analisi delle immagini) un massimo di `max_retries` volte
    finché non restituisce un risultato valido.
    """
    for attempt in range(max_retries):
        try:
            print(f"Tentativo {attempt + 1} di esecuzione della funzione main...")
            result = main(base64_images)
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
    # Verifica credenziali
    if not verify_credentials(username, password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    try:
        # Esegui la funzione `main` con un massimo di 10 tentativi (come da codice originale)
        result = execute_main_with_retries(request.images, max_retries=10)

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


# ------------------------------------------------------------------------------
# AVVIO SERVER
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

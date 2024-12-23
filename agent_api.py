import json
import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from agent.agent_utils import main  # Importiamo la funzione `main` dallo script precedente

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

# Modello per la richiesta
class AnalysisRequest(BaseModel):
    patient_id: str
    images: List[str]  # Lista di immagini in formato Base64

# Modello per la risposta
class AnalysisResult(BaseModel):
    result: dict  # Risultato parsato come dizionario


def execute_main_with_retries(base64_images, max_retries=3):
    """
    Esegue la funzione main un massimo di `max_retries` volte finché non restituisce un risultato valido.
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


PATIENTS_FILE = "anagrafiche.json"  # Percorso del file JSON contenente le anagrafiche

def update_patient_analysis(patient_id: str, analysis_result: dict):
    """
    Aggiorna il file dei pazienti per aggiungere il risultato di un'analisi
    al paziente specificato, creando o aggiornando il campo `analysis_history`.

    :param patient_id: ID del paziente
    :param analysis_result: Risultato dell'analisi da aggiungere
    """
    if not os.path.exists(PATIENTS_FILE):
        raise FileNotFoundError(f"Il file {PATIENTS_FILE} non esiste.")

    # Leggi i dati dal file
    with open(PATIENTS_FILE, "r") as f:
        patients_data = json.load(f)

    # Trova il paziente specificato
    patient = next((p for p in patients_data if p.get("id") == patient_id), None)
    if not patient:
        raise ValueError(f"Il paziente con ID {patient_id} non esiste.")

    # Aggiungi o aggiorna il campo `analysis_history`
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    analysis_entry = {"timestamp": timestamp, "result": analysis_result}
    if "analysis_history" in patient:
        patient["analysis_history"].append(analysis_entry)
    else:
        patient["analysis_history"] = [analysis_entry]

    # Salva le modifiche nel file
    with open(PATIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(patients_data, f, indent=4)

@app.post("/analyze_skin", response_model=AnalysisResult)
async def analyze_skin(request: AnalysisRequest):
    """
    Endpoint per analizzare lo stato della pelle in base a immagini Base64.
    """
    try:
        # Esegui la funzione `main` con un massimo di 3 tentativi
        result = execute_main_with_retries(request.images, max_retries=10)

        # Aggiorna la storia delle analisi del paziente specificato
        update_patient_analysis(request.patient_id, result)

        return {"result": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Errore file: {e}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Errore: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

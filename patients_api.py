from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
import json
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puoi specificare i domini consentiti
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nome del file JSON per memorizzare le anagrafiche
DATA_FILE = "anagrafiche.json"

# Assicurati che il file esista e abbia un formato valido
try:
    with open(DATA_FILE, "r") as file:
        anagrafiche = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    anagrafiche = []

# Modello per l'anagrafica

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

# Gestione della richiesta OPTIONS
@app.options("/{path_name:path}")
async def options_handler():
    return JSONResponse(status_code=200, content="OK")


# Funzione di supporto per salvare i dati nel file JSON
def save_to_file():
    with open(DATA_FILE, "w") as file:
        json.dump(anagrafiche, file, indent=4)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json
import uuid

# Endpoint per creare una nuova anagrafica
@app.post("/create_anagrafiche")
async def create_anagrafica(new_anagrafica: Anagrafica):
    try:
        # Carica le anagrafiche esistenti
        try:
            with open(DATA_FILE, "r") as file:
                anagrafiche = json.load(file)
        except FileNotFoundError:
            anagrafiche = []

        # Aggiungi la nuova anagrafica
        anagrafiche.append(new_anagrafica.dict())

        # Salva il file aggiornato
        with open(DATA_FILE, "w") as file:
            json.dump(anagrafiche, file, indent=4)

        return {"message": "Anagrafica creata con successo"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/anagrafiche/{anagrafica_id}", response_model=Anagrafica)
async def update_anagrafica(anagrafica_id: str, updated_data: Anagrafica):
    """
    Aggiorna un'anagrafica esistente tramite ID.
    """
    for idx, anagrafica in enumerate(anagrafiche):
        if anagrafica["id"] == anagrafica_id:
            anagrafiche[idx] = updated_data.dict()
            anagrafiche[idx]["id"] = anagrafica_id  # Mantieni l'ID invariato
            save_to_file()
            return anagrafiche[idx]
    raise HTTPException(status_code=404, detail="Anagrafica non trovata.")

@app.delete("/anagrafiche/{anagrafica_id}", response_model=dict)
async def delete_anagrafica(anagrafica_id: str):
    """
    Elimina un'anagrafica tramite ID.
    """
    for idx, anagrafica in enumerate(anagrafiche):
        if anagrafica["id"] == anagrafica_id:
            deleted = anagrafiche.pop(idx)
            save_to_file()
            return {"message": "Anagrafica eliminata con successo.", "data": deleted}
    raise HTTPException(status_code=404, detail="Anagrafica non trovata.")


@app.get("/anagrafiche", response_model=List[Anagrafica])
async def get_anagrafiche():
    """
    Recupera tutte le anagrafiche.
    """

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            anagrafiche = json.load(file)
    except FileNotFoundError:
        anagrafiche = []

    return anagrafiche

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)


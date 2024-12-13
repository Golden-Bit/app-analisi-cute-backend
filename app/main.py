import json
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# CORS configuration (open for development purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

class AnalysisRequest(BaseModel):
    analysis_type: str
    images: List[str]  # Base64 encoded images


class AnalysisResponse(BaseModel):
    valore: int
    descrizione: str
    valutazione_professionale: str
    consigli: str


# Simulated results for each analysis type
SIMULATED_RESULTS = {
    "Idratazione": {
        "valore": 50,
        "descrizione": "La pelle ha un'idratazione normale.",
        "valutazione_professionale": "Il livello di idratazione è adeguato.",
        "consigli": "Mantenere l'idratazione bevendo acqua e utilizzando prodotti idratanti."
    },
    "Strato lipidico": {
        "valore": 40,
        "descrizione": "Lo strato lipidico è ridotto.",
        "valutazione_professionale": "La pelle potrebbe essere soggetta a secchezza.",
        "consigli": "Utilizzare creme nutrienti e protettive."
    },
    "Elasticità": {
        "valore": 70,
        "descrizione": "La pelle mostra un'elasticità elevata.",
        "valutazione_professionale": "Il livello di elasticità è ottimale.",
        "consigli": "Continuare con una routine di skincare equilibrata."
    },
    "Cheratina": {
        "valore": 30,
        "descrizione": "La cheratina è ridotta.",
        "valutazione_professionale": "Possibili problemi di protezione naturale della pelle.",
        "consigli": "Integrare con prodotti ricchi di cheratina."
    },
    "Pelle sensibile": {
        "valore": 60,
        "descrizione": "La pelle è moderatamente sensibile.",
        "valutazione_professionale": "Occasionalmente reattiva agli agenti esterni.",
        "consigli": "Utilizzare prodotti lenitivi e ipoallergenici."
    },
    "Macchie cutanee": {
        "valore": 20,
        "descrizione": "Macchie cutanee poco visibili.",
        "valutazione_professionale": "La pelle è generalmente uniforme.",
        "consigli": "Utilizzare protezione solare per prevenire future macchie."
    },
    "Tonalità": {
        "valore": 80,
        "descrizione": "La tonalità della pelle è uniforme e luminosa.",
        "valutazione_professionale": "Aspetto della pelle eccellente.",
        "consigli": "Mantenere una routine equilibrata."
    },
    "Densità pilifera": {
        "valore": 10,
        "descrizione": "Densità pilifera molto bassa.",
        "valutazione_professionale": "Aspetto levigato della pelle.",
        "consigli": "Continuare a idratare e proteggere la pelle."
    },
    "Pori ostruiti": {
        "valore": 55,
        "descrizione": "Pori leggermente ostruiti.",
        "valutazione_professionale": "Possibilità di imperfezioni se non trattati.",
        "consigli": "Effettuare esfoliazione regolare e utilizzare prodotti per la pulizia profonda."
    }
}


@app.post("/analyze",)# response_model=AnalysisResponse)
async def analyze(request: AnalysisRequest):
    #if request.analysis_type not in SIMULATED_RESULTS:
    #    raise HTTPException(status_code=400, detail="Tipo di analisi non supportato.")

    #print(json.dumps(request.json(), indent=2))
    time.sleep(5)
    # Simulated response
    #result = SIMULATED_RESULTS[request.analysis_type]
    return SIMULATED_RESULTS #AnalysisResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8101)

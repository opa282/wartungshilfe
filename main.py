import fastapi
import uvicorn
import os
import random
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ==============================================================================
# Daten-Integration
# ==============================================================================
def load_data():
    """Lädt die Fehlerdaten, ordnet Lösungen zu und generiert Teile."""
    
    # Manuell erstellte Zuordnung von Fehlern zu Lösungen
    error_remedy_map = {
        "Not enough memory to generate the external reference list": "Increase PLC memory or simplify program.",
        "Cycle time is greater than the set watchdog time": "Change task configuration or optimize code.",
        "Access violation by an IEC task (for example zero pointer)": "Correct program logic (e.g., check for null pointers).",
        "Internal error, no access to IO data": "Restart CPU or call support.",
        "Watchdog task could not be installed": "Check Communication Module and CPU firmware version.",
        "Error in configuration data, PLC cannot read": "Create new configuration.",
        "Timeout when setting the warm start parameters of the Communication Module": "Check Communication Module.",
        "Error in firmware version of Communication Module (version not supported/too old)": "Update firmware of the Communication Module.",
        "Maximum errors in series detected 50 telegrams in sequence are invalid or corrupted.": "Restart PLC. If error still exists, replace PLC.",
        "FPU division by zero": "Correct program to avoid division by zero.",
        "Timeout in the I/O Module": "Replace I/O module.",
        "Overflow diagnosis buffer": "Restart PLC.",
        "Process voltage too high": "Check process voltage source and wiring.",
        "Process voltage too low": "Check process voltage source and wiring.",
        "Plausibility check failed (iParameter)": "Check configuration parameters.",
        "Checksum error in the I/O Module": "Replace I/O Module or check safety configuration.",
        "PROFIsafe communication error": "Restart I/O Module. If error persists, contact support.",
        "PROFIsafe watchdog timed out": "Restart I/O Module or increase watchdog time.",
        "Internal data interchange disturbed": "Check PLC program and module connections.",
        "Different hardware and firmware versions in the module": "Replace I/O Module to match versions.",
        "Internal error in the device": "Replace I/O Module.",
        "Sensor voltage too low": "Check sensor voltage and wiring.",
        "Process voltage switched off (ON->OFF)": "Turn process voltage ON.",
        "Short-circuit at the digital output": "Check terminal and wiring for short-circuits."
    }

    # Erstelle die finale Datenstruktur
    error_data = {}
    teile_db = {}
    komponenten = ["Sensor", "Motor", "Pumpe", "Ventil", "Steuerung", "Relais", "Kabelbaum", "Netzteil"]

    for i, (error, remedy) in enumerate(error_remedy_map.items()):
        anzahl_teile = random.randint(1, 3)
        moegliche_teile = []
        for j in range(anzahl_teile):
            teil_name = f"{random.choice(komponenten)}-{i+1}.{j+1}"
            moegliche_teile.append(teil_name)
            teile_db[teil_name] = f"plan_{teil_name.lower().replace(' ', '_')}.pdf"
        
        error_data[error] = {"remedy": remedy, "parts": moegliche_teile}
        
    return error_data, teile_db

# Laden der Daten beim Start
error_data, teile_zu_schaltplan = load_data()

# ==============================================================================
# FastAPI Anwendung
# ==============================================================================
app = fastapi.FastAPI()

class PartRequest(BaseModel):
    error: str

class SchematicRequest(BaseModel):
    part: str

# API Endpunkte
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/search_errors")
async def search_errors(query: str = ""):
    if not query:
        return []
    return [fehler for fehler in error_data.keys() if query.lower() in fehler.lower()][:10]

@app.get("/api/all_errors")
async def get_all_errors():
    return sorted(list(error_data.keys()))

@app.post("/api/parts")
async def get_parts(request: PartRequest):
    return error_data.get(request.error, {"remedy": "Keine Daten gefunden.", "parts": []})

@app.post("/api/schematic")
async def get_schematic(request: SchematicRequest):
    return {"schematic": teile_zu_schaltplan.get(request.part)}

# Statische Dateien und die Haupt-HTML-Datei bereitstellen
script_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(script_dir, "static")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(static_dir, 'index.html'))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
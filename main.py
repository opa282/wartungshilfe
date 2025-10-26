
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
    """Lädt die echten Fehlerdaten und generiert zugehörige Teile."""
    
    # Manuell aus dem User-Input extrahierte Fehler
    error_messages = [
        # Alte Fehler
        "Not enough memory to generate the external reference list",
        "Cycle time is greater than the set watchdog time",
        "Access violation by an IEC task (for example zero pointer)",
        "Exception cannot be assigned to an IEC task",
        "Cycle time of IEC task is greater than watchdog time",
        "There is not enough memory available for configuration of PROFINET Controller",
        "Internal error occured during configuration of PROFINET Controller",
        "Internal error, no access to IO data",
        "Watchdog task could not be installed",
        "Installation of the Communication Module bus driver failed",
        "Initialization error, not enough memory",
        "Accessing test to the Communication Module failed",
        "Watchdog test for the Communication Module failed",
        "Error in configuration data, PLC cannot read",
        "Timeout when setting the warm start parameters of the Communication Module",
        "Installation of the Communication Module driver failed",
        "Error occurred when creating the I/O description list of the Communication Module",
        "Error configuration",
        "Error in firmware version of Communication Module (version not supported/too old)",
        "Maximum errors in series detected 50 telegrams in sequence are invalid or corrupted.",
        "Installation of a protocol driver for the serial interface failed, not enough memory",
        "Incorrect data format of the hardware driver of the I/O-Bus",
        "FPU division by zero",
        "FPU overflow",
        "FPU underflow",
        "Forbidden FPU operation (e.g. 0/0)",
        "Error internal Ethernet",
        "Program not started because of an existing error",
        "User program contains an endless loop, a stop by hand is necessary",
        "No configuration available",
        "Writing of the boot project failed",
        "Failed to delete boot project",
        "Error firmware update of SD card, file could not be opened",
        "Error while reading/writing the configuration data from/to the SD card",

        # Neue Fehler
        "Timeout in the I/O Module",
        "Overflow diagnosis buffer",
        "Process voltage too high",
        "Process voltage too low",
        "Plausibility check failed (iParameter)",
        "Checksum error in the I/O Module",
        "PROFIsafe communication error",
        "PROFIsafe watchdog timed out",
        "Parameter value or configuration error",
        "Internal data interchange disturbed",
        "Different hardware and firmware versions in the module",
        "Internal error in the device",
        "Sensor voltage too low",
        "Process voltage switched off (ON->OFF)",
        "Wrong measurement; wrong temperature at the compensations channel",
        "AI531: Wrong measurement; potential difference is to high",
        "Output overflow at analog output",
        "Measurement underflow at the analog input",
        "Input/output value to high",
        "Short-circuit at the analog input",
        "Measurement overflow or cut wire at the analog input",
        "Short-circuit at the digital output",
        "PLC conflict",
        "Outputs are different (synchronization error)"
    ]

    fehler_db = {}
    teile_db = {}
    
    komponenten = ["Sensor", "Motor", "Pumpe", "Ventil", "Steuerung", "Relais", "Kabelbaum", "Netzteil"]
    
    for i, error in enumerate(error_messages):
        anzahl_teile = random.randint(1, 3)
        moegliche_teile = []
        for j in range(anzahl_teile):
            teil_name = f"{random.choice(komponenten)}-{i+1}.{j+1}"
            moegliche_teile.append(teil_name)
            teile_db[teil_name] = f"plan_{teil_name.lower().replace(' ', '_')}.pdf"
            
        fehler_db[error] = moegliche_teile
        
    return fehler_db, teile_db

fehler_zu_teilen, teile_zu_schaltplan = load_data()

# ==============================================================================
# FastAPI Anwendung
# ==============================================================================
app = fastapi.FastAPI()

class PartRequest(BaseModel):
    error: str

class SchematicRequest(BaseModel):
    part: str

# API Endpunkte
@app.get("/api/search_errors")
async def search_errors(query: str = ""):
    if not query:
        return []
    return [fehler for fehler in fehler_zu_teilen.keys() if query.lower() in fehler.lower()][:10]

@app.get("/api/all_errors")
async def get_all_errors():
    return sorted(list(fehler_zu_teilen.keys()))

@app.post("/api/parts")
async def get_parts(request: PartRequest):
    return fehler_zu_teilen.get(request.error, [])

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

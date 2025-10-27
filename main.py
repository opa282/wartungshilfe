import fastapi
import uvicorn
import os
import json
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta

import random
# Lokale Importe
from wartungshilfe_web.config import settings 
from wartungshilfe_web.database import User, UserInDB, get_user, add_user, verify_password, pwd_context, get_all_users, update_user_data, delete_user

# ==============================================================================
# Security Konfiguration
# ==============================================================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

# ==============================================================================
# Authentifizierungs-Funktionen
# ==============================================================================
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username=username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Dependency für Admin-Rolle
def is_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Operation not permitted")
    return True

# ==============================================================================
# Daten-Integration
# ==============================================================================
def load_data():
    """
    Lädt die Fehlerliste und generiert dynamisch Lösungsvorschläge,
    Teile und Schaltpläne. Diese Logik ist aus der ursprünglichen
    Schaltplan.py-Datei integriert.
    """
    error_data = {}
    teile_zu_schaltplan = {}
    
    # Strukturierte Daten aus dem User-Input
    real_error_data = [
        {"error": "Not enough memory to generate the external reference list", "remedy": "Increase PLC memory or simplify program."},
        {"error": "Cycle time is greater than the set watchdog time", "remedy": "Change task configuration"},
        {"error": "Access violation by an IEC task (for example zero pointer)", "remedy": "Correct program"},
        {"error": "Exception cannot be assigned to an IEC task", "remedy": "Correct program"},
        {"error": "Cycle time of IEC task is greater than watchdog time", "remedy": "Change task configuration"},
        {"error": "There is not enough memory available for configuration of PROFINET Controller", "remedy": "Reboot PLC, reduce PROFINET configuration and reload project"},
        {"error": "Internal error occured during configuration of PROFINET Controller", "remedy": "Reboot PLC and reload project"},
        {"error": "Internal error, no access to IO data", "remedy": "Restart CPU or call support"},
        {"error": "Watchdog task could not be installed", "remedy": "Check Communication Module, Check CPU firmware version"},
        {"error": "Installation of the Communication Module bus driver failed", "remedy": "Check Communication Module, Check CPU firmware version"},
        {"error": "Initialization error, not enough memory", "remedy": "Check Communication Module, Check CPU firmware version"},
        {"error": "Accessing test to the Communication Module failed", "remedy": "Check Communication Module, Check CPU FW version"},
        {"error": "Watchdog test for the Communication Module failed", "remedy": "Check Communication Module"},
        {"error": "Error in configuration data, PLC cannot read", "remedy": "Create new configuration"},
        {"error": "Timeout when setting the warm start parameters of the Communication Module", "remedy": "Check Communication Module"},
        {"error": "Installation of the Communication Module driver failed", "remedy": "Check Communication Module and FW version"},
        {"error": "Error occurred when creating the I/O description list of the Communication Module", "remedy": "Check Communication Module and FW version"},
        {"error": "Error configuration", "remedy": "Check configuration"},
        {"error": "Error in firmware version of Communication Module (version not supported/too old)", "remedy": "Update firmware"},
        {"error": "Maximum errors in series detected 50 telegrams in sequence are invalid or corrupted.", "remedy": "Restart PLC. If error still exists, replace PLC."},
        {"error": "Installation of a protocol driver for the serial interface failed, not enough memory", "remedy": "Check CPU FW version"},
        {"error": "Incorrect data format of the hardware driver of the I/O-Bus", "remedy": "Check CPU FW version"},
        {"error": "FPU division by zero", "remedy": "Clear up program"},
        {"error": "FPU overflow", "remedy": "Clear up program"},
        {"error": "FPU underflow", "remedy": "Clear up program"},
        {"error": "Forbidden FPU operation (e.g. 0/0)", "remedy": "Clear up program"},
        {"error": "Error internal Ethernet", "remedy": "Replace module"},
        {"error": "Program not started because of an existing error", "remedy": "Eliminate error and acknowledge"},
        {"error": "User program contains an endless loop, a stop by hand is necessary", "remedy": "Correct user program"},
        {"error": "No configuration available", "remedy": "Create new configuration, check configuration"},
        {"error": "Writing of the boot project failed", "remedy": "Reload project"},
        {"error": "Failed to delete boot project", "remedy": "Failed to delete boot project"}, # Remedy was missing, used error as placeholder
        {"error": "Error firmware update of SD card, file could not be opened", "remedy": "Check SD card, e.g. removed without 'ejected'"},
        {"error": "Error while reading/writing the configuration data from/to the SD card", "remedy": "Check SD card"},
        {"error": "Timeout in the I/O Module", "remedy": "Replace module"},
        {"error": "Overflow diagnosis buffer", "remedy": "Clear all errors"},
        {"error": "Process voltage too high", "remedy": "Correct value"}, # Generic remedy
        {"error": "Process voltage too low", "remedy": "Correct value"}, # Generic remedy
        {"error": "Plausibility check failed (iParameter)", "remedy": "Check parameters"}, # Generic remedy
        {"error": "Checksum error in the I/O Module", "remedy": "Check module"}, # Generic remedy
        {"error": "PROFIsafe communication error", "remedy": "Check PROFIsafe configuration"}, # Generic remedy
        {"error": "PROFIsafe watchdog timed out", "remedy": "Check PROFIsafe configuration"}, # Generic remedy
        {"error": "Parameter value or configuration error", "remedy": "Check parameter value or configuration"},
        {"error": "Internal data interchange disturbed", "remedy": "Restart PLC"}, # Generic remedy
        {"error": "Different hardware and firmware versions in the module", "remedy": "Update firmware or check hardware"},
        {"error": "Internal error in the device", "remedy": "Replace device"},
        {"error": "Sensor voltage too low", "remedy": "Check sensor voltage supply"},
        {"error": "Process voltage switched off (ON->OFF)", "remedy": "Check process voltage supply"},
        {"error": "Wrong measurement; wrong temperature at the compensations channel", "remedy": "Check sensor and compensation channel"},
        {"error": "AI531: Wrong measurement; potential difference is to high", "remedy": "Check wiring and potential difference"},
        {"error": "Output overflow at analog output", "remedy": "Check output load and configuration"},
        {"error": "Measurement underflow at the analog input", "remedy": "Check sensor and wiring"},
        {"error": "Input/output value to high", "remedy": "Check input/output signal level"},
        {"error": "Short-circuit at the analog input", "remedy": "Check wiring for short-circuits"},
        {"error": "Measurement overflow or cut wire at the analog input", "remedy": "Check sensor and wiring for open circuits"},
        {"error": "Short-circuit at the digital output", "remedy": "Check terminal and wiring for short-circuits."},
        {"error": "PLC conflict", "remedy": "Resolve PLC conflict"}, # Generic remedy
        {"error": "Outputs are different (synchronization error)", "remedy": "Check synchronization logic"},
        # --- Ab hier die neuen Fehler aus dem zweiten Teil ---
        {"error": "Timeout in the I/O Module", "remedy": "Replace I/O module"},
        {"error": "Overflow diagnosis buffer", "remedy": "Restart"},
        {"error": "Process voltage too high", "remedy": "Check process voltage"},
        {"error": "Process voltage too low", "remedy": "Check process voltage"},
        {"error": "Plausibility check failed (iParameter)", "remedy": "Check configuration"},
        {"error": "Checksum error in the I/O Module", "remedy": "Non-safety I/O: Replace I/O Module. Safety-I/O: Check safety configuration and CRCs for iParameters and F-Parameters"},
        {"error": "PROFIsafe communication error", "remedy": "Restart I/O Module. If this error persists, contact ABB technical support."},
        {"error": "PROFIsafe watchdog timed out", "remedy": "Restart I/O Module. If this error persists, increase PROFIsafe watchdog time."},
        {"error": "Parameter value or configuration", "remedy": "Check master"},
        {"error": "F-Parameter configuration and address switch value do not match", "remedy": "Check I/O Module's F-Parameter configuration and module address switch value"},
        {"error": "Internal data interchange disturbed", "remedy": "Replace I/O Module"},
        {"error": "Different hardware and firmware versions in the module", "remedy": "Replace I/O Module"},
        {"error": "Internal error in the device", "remedy": "Replace I/O Module"},
        {"error": "Sensor voltage too low", "remedy": "Check sensor voltage"},
        {"error": "Process voltage switched off (ON->OFF)", "remedy": "Process voltage ON"},
        {"error": "Wrong measurement; wrong temperature at the compensations channel", "remedy": "Check temperature compensation channel"},
        {"error": "AI531: Wrong measurement; potential difference is to high", "remedy": "AI531: Check potential difference"},
        {"error": "CD522: PWM duty cycle out of duty area", "remedy": "CD522: Check min/max values"},
        {"error": "Output overflow at analog output", "remedy": "Check output value"},
        {"error": "Measurement underflow at the analog input", "remedy": "Check input value"},
        {"error": "Input/output value to high", "remedy": "Check input/output value"},
        {"error": "Short-circuit at the analog input", "remedy": "Check terminal"},
        {"error": "Measurement overflow or cut wire at the analog input", "remedy": "Check input value and terminal"}
    ]

    komponenten = ["Sensor", "Motor", "Pumpe", "Ventil", "Steuerung", "Relais", "Kabelbaum", "Netzteil"]

    # Hilfs-Dictionary, um Duplikate zu zählen und Fehler eindeutig zu machen
    error_counts = {}

    for i, data in enumerate(real_error_data):
        error = data["error"]
        remedy = data["remedy"]

        # Prüfe auf Duplikate und mache den Fehlertext eindeutig
        if error in error_counts:
            error_counts[error] += 1
            unique_error = f"{error} ({error_counts[error]})"
        else:
            error_counts[error] = 1
            unique_error = error

        anzahl_teile = random.randint(1, 3)
        part_names = [f"{random.choice(komponenten)}-{i+1}.{j+1}" for j in range(anzahl_teile)]
        
        error_data[unique_error] = {"remedy": remedy, "parts": part_names}
        for part_name in part_names:
            teile_zu_schaltplan[part_name] = f"plan_{part_name.lower().replace(' ', '_')}.pdf"

    return error_data, teile_zu_schaltplan

error_data, teile_zu_schaltplan = load_data()

# ==============================================================================
# FastAPI Anwendung
# ==============================================================================
app = fastapi.FastAPI()

class PartRequest(BaseModel):
    error: str

class SchematicRequest(BaseModel):
    part: str

class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str

class UserUpdateRequest(BaseModel):
    new_password: str | None = None
    new_role: str | None = None

# ==============================================================================
# API Endpunkte
# ==============================================================================

# --- Login Endpunkt ---
@app.post("/api/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    # Sichere Passwortverifizierung wiederhergestellt
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        # Verwende den kanonischen Benutzernamen aus der DB für den Token
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

# --- Geschützte Endpunkte ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/search_errors")
async def search_errors(query: str = "", current_user: User = Depends(get_current_active_user)):
    if not query:
        return []
    return [fehler for fehler in error_data.keys() if query.lower() in fehler.lower()][:10]
    return [fehler for fehler in error_data.keys() if query.lower() in fehler.lower()]

@app.get("/api/all_errors")
async def get_all_errors(current_user: User = Depends(get_current_active_user)):
    return sorted(list(error_data.keys()))

@app.post("/api/parts")
async def get_parts(request: PartRequest, current_user: User = Depends(get_current_active_user)):
    return error_data.get(request.error, {"remedy": "Keine Daten gefunden.", "parts": []})

@app.post("/api/schematic")
async def get_schematic(request: SchematicRequest, current_user: User = Depends(get_current_active_user)):
    return {"schematic": teile_zu_schaltplan.get(request.part)}

# --- Admin-spezifischer Endpunkt (Beispiel) ---
@app.get("/api/admin/check")
async def admin_check(is_admin_user: bool = Depends(is_admin)):
    return {"message": "Welcome, Admin! You have access to special settings."}

@app.post("/api/admin/users", status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreateRequest, is_admin_user: bool = Depends(is_admin)):
    hashed_password = pwd_context.hash(user_data.password)
    user_in_db = UserInDB(
        username=user_data.username,
        hashed_password=hashed_password,
        role=user_data.role,
    )
    # add_user gibt False zurück, wenn der Benutzer bereits existiert
    if not add_user(user_in_db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    return {"message": f"User '{user_data.username}' created successfully."}

@app.get("/api/admin/users", response_model=list[User])
async def read_users(is_admin_user: bool = Depends(is_admin)):
    return get_all_users()

@app.put("/api/admin/users/{username}")
async def update_user(username: str, update_data: UserUpdateRequest, is_admin_user: bool = Depends(is_admin)):
    if not update_user_data(username, update_data.dict(exclude_unset=True)):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User '{username}' updated successfully."}

@app.delete("/api/admin/users/{username}")
async def remove_user(username: str, is_admin_user: bool = Depends(is_admin)):
    if username.lower() == 'admin': # Schutz vor Selbstlöschung
        raise HTTPException(status_code=400, detail="Cannot delete the primary admin account.")
    if not delete_user(username):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User '{username}' deleted successfully."}

@app.get("/api/admin/backup/users")
async def backup_users(is_admin_user: bool = Depends(is_admin)):
    """Stellt die users.json Datei als Download bereit."""
    db_file_path = os.path.join(os.path.dirname(__file__), "users.json")
    if not os.path.exists(db_file_path):
        raise HTTPException(status_code=404, detail="Users file not found.")
    return FileResponse(path=db_file_path, filename="users_backup.json", media_type='application/json')

# Statische Dateien und die Haupt-HTML-Datei bereitstellen
script_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(script_dir, "static")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(static_dir, 'index.html'))

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8003)

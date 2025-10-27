from pydantic import BaseModel
from passlib.context import CryptContext
import json
import os

# ==============================================================================
# Pydantic Modelle für Benutzer
# ==============================================================================
class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None
    role: str

class UserInDB(User):
    hashed_password: str

# ==============================================================================
# Passwort-Kontext und Verifizierung
# ==============================================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Überprüft ein Klartext-Passwort gegen einen Hash."""
    return pwd_context.verify(plain_password, hashed_password)

# ==============================================================================
# Persistente Benutzerdatenbank (JSON-Datei)
# ==============================================================================
# Render stellt einen persistenten Speicher unter /data bereit.
# Lokal verwenden wir weiterhin den alten Pfad als Fallback.
RENDER_DATA_DIR = "/data"
DB_FILE = os.path.join(RENDER_DATA_DIR, "users.json") if os.path.exists(RENDER_DATA_DIR) else os.path.join(os.path.dirname(__file__), "users.json")
_users_db = {} # Wird jetzt aus der Datei geladen

def _save_db():
    """Speichert die In-Memory-DB in die JSON-Datei."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(_users_db, f, indent=4)

def _load_db():
    """Lädt die DB aus der JSON-Datei oder initialisiert sie, wenn sie nicht existiert."""
    global _users_db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            _users_db = json.load(f)
    else:
        # Initialisiere mit Standard-Benutzern, wenn die Datei nicht existiert
        _users_db = {
            "admin": {
                "username": "admin", "full_name": "Haupt-Administrator", "email": "admin@example.com",
                "hashed_password": pwd_context.hash("Admin123"), "role": "admin", "disabled": False
            },
            "user": {
                "username": "user", "full_name": "Standard-Benutzer", "email": "user@example.com",
                "hashed_password": pwd_context.hash("user123"), "role": "user", "disabled": False
            }
        }
        _save_db()

def get_user(username: str) -> UserInDB | None:
    """Sucht einen Benutzer in der In-Memory-Datenbank."""
    for db_username, user_data in _users_db.items():
        if db_username.lower() == username.lower():
            return UserInDB(**user_data)
    return None

def add_user(user: UserInDB):
    """Fügt einen neuen Benutzer hinzu und speichert in die Datei."""
    for existing_user in _users_db:
        if existing_user.lower() == user.username.lower():
            return False # Benutzer existiert bereits
    _users_db[user.username] = user.dict()
    _save_db()
    return True

def get_all_users() -> list[User]:
    """Gibt eine Liste aller Benutzer zurück (ohne Passwörter)."""
    return [User(**user_data) for user_data in _users_db.values()]

def update_user_data(username: str, update_data: dict) -> bool:
    """Aktualisiert die Daten eines Benutzers und speichert in die Datei."""
    user_to_update = None
    for db_username in _users_db:
        if db_username.lower() == username.lower():
            user_to_update = db_username
            break
    
    if not user_to_update:
        return False

    if "new_password" in update_data and update_data["new_password"]:
        _users_db[user_to_update]["hashed_password"] = pwd_context.hash(update_data["new_password"])
    if "new_role" in update_data:
        _users_db[user_to_update]["role"] = update_data["new_role"]
    
    _save_db()
    return True

def delete_user(username: str) -> bool:
    """Löscht einen Benutzer und speichert die Änderung in die Datei."""
    user_to_delete = None
    for db_username in _users_db:
        if db_username.lower() == username.lower():
            user_to_delete = db_username
            break

    if user_to_delete and _users_db.pop(user_to_delete, None):
        _save_db()
        return True
    return False

# Lade die Datenbank beim Start des Moduls
_load_db()
document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elemente ---
    const loginContainer = document.getElementById('login-container');
    const appContainer = document.getElementById('app-container');
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    const logoutButton = document.getElementById('logout-button');
    const userRoleSpan = document.getElementById('user-role');
    const adminPanel = document.getElementById('admin-panel');

    const errorSearch = document.getElementById('error-search');
    const suggestionsBox = document.getElementById('suggestions-box');
    const errorDropdown = document.getElementById('error-dropdown');
    const remedySection = document.getElementById('remedy-section');
    const remedyText = document.getElementById('remedy-text');
    const partsSection = document.getElementById('parts-section');
    const partSelect = document.getElementById('part-select');
    const resultSection = document.getElementById('result-section');
    const schematicResult = document.getElementById('schematic-result');

    // --- Admin Elemente ---
    const addUserForm = document.getElementById('add-user-form');
    const addUserStatus = document.getElementById('add-user-status');
    const userManagementSection = document.getElementById('user-management-section');
    const userTableBody = document.getElementById('user-table-body');
    const backupUsersButton = document.getElementById('backup-users-button');

    // --- Modal Elemente ---
    const editUserModal = document.getElementById('edit-user-modal');
    const editUserForm = document.getElementById('edit-user-form');
    const editUsernameSpan = document.getElementById('edit-username');
    const editUserOriginalUsername = document.getElementById('edit-user-original-username');
    const closeModalButton = document.querySelector('.close-button');

    // --- Authentifizierung ---
    let token = localStorage.getItem('accessToken');
    let userRole = localStorage.getItem('userRole');

    function showLogin() {
        loginContainer.style.display = 'block';
        appContainer.style.display = 'none';
        localStorage.removeItem('accessToken');
        localStorage.removeItem('userRole');
        token = null;
        userRole = null;
    }

    function showApp() {
        loginContainer.style.display = 'none';
        appContainer.style.display = 'block';
        userRoleSpan.textContent = userRole;
        
        if (userRole === 'admin') {
            adminPanel.style.display = 'block';
            userManagementSection.style.display = 'block';
            loadUsers();
        } else {
            adminPanel.style.display = 'none';
            userManagementSection.style.display = 'none';
        }

        loadAllErrorsDropdown();
    }

    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = e.target.username.value;
        const password = e.target.password.value;

        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        fetch('/api/login', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Anmeldung fehlgeschlagen');
            }
            return response.json();
        })
        .then(data => {
            token = data.access_token;
            userRole = data.role;
            localStorage.setItem('accessToken', token);
            localStorage.setItem('userRole', userRole);
            loginError.textContent = '';
            showApp();
        })
        .catch(error => {
            loginError.textContent = 'Falscher Benutzername oder Passwort.';
            console.error('Login error:', error);
        });
    });

    logoutButton.addEventListener('click', () => {
        showLogin();
    });

    // --- API-Aufrufe mit Authentifizierung ---
    function getAuthHeaders() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
    }

    function apiFetch(url, options = {}) {
        const defaultOptions = {
            headers: getAuthHeaders()
        };
        const mergedOptions = { ...defaultOptions, ...options };
        
        return fetch(url, mergedOptions).then(response => {
            if (response.status === 401) { // Unauthorized
                showLogin();
                throw new Error('Session abgelaufen. Bitte neu anmelden.');
            }
            if (!response.ok) {
                throw new Error('Netzwerkfehler oder Server-Problem.');
            }
            return response.json();
        });
    }

    // --- Füllt das Dropdown-Menü mit allen Fehlern ---
    function loadAllErrorsDropdown() {
        apiFetch('/api/all_errors')
            .then(errors => {
                errorDropdown.innerHTML = '<option value="">-- Aus Liste wählen --</option>';
                errors.forEach(error => {
                    const option = document.createElement('option');
                    option.value = error;
                    option.textContent = error;
                    errorDropdown.appendChild(option);
                });
                errorDropdown.disabled = false;
            })
            .catch(error => {
                console.error('Fehler beim Laden der Fehlerliste:', error);
                errorDropdown.innerHTML = '<option>Laden fehlgeschlagen</option>';
            });
    }

    // --- Event Listener für das Dropdown-Menü ---
    errorDropdown.addEventListener('change', () => {
        const selectedError = errorDropdown.value;
        errorSearch.value = '';
        suggestionsBox.style.display = 'none';
        if (selectedError) {
            fetchParts(selectedError);
        } else {
            remedySection.style.display = 'none';
            partsSection.style.display = 'none';
            resultSection.style.display = 'none';
        }
    });

    // --- Event Listener für die Fehlersuche ---
    errorSearch.addEventListener('input', () => {
        errorDropdown.selectedIndex = 0;
        const query = errorSearch.value;
        remedySection.style.display = 'none';
        partsSection.style.display = 'none';
        resultSection.style.display = 'none';
        partSelect.innerHTML = '';

        if (query.length < 2) {
            suggestionsBox.innerHTML = '';
            suggestionsBox.style.display = 'none';
            return;
        }

        apiFetch(`/api/search_errors?query=${encodeURIComponent(query)}`)
            .then(suggestions => {
                if (suggestions.length > 0) {
                    suggestionsBox.innerHTML = '';
                    suggestions.forEach(suggestion => {
                        const div = document.createElement('div');
                        div.textContent = suggestion;
                        div.classList.add('suggestion-item');
                        div.addEventListener('click', () => {
                            errorSearch.value = suggestion;
                            suggestionsBox.style.display = 'none';
                            fetchParts(suggestion);
                        });
                        suggestionsBox.appendChild(div);
                    });
                    suggestionsBox.style.display = 'block';
                } else {
                    suggestionsBox.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Fehler bei der Fehlersuche:', error);
            });
    });

    // --- Funktion zum Abrufen von Teilen und Lösungen ---
    function fetchParts(error) {
        apiFetch('/api/parts', {
            method: 'POST',
            body: JSON.stringify({ error: error })
        })
        .then(data => {
            remedyText.textContent = data.remedy;
            remedySection.style.display = 'block';
            partSelect.innerHTML = '<option value="">-- Bitte wählen --</option>';
            data.parts.forEach(part => {
                const option = document.createElement('option');
                option.value = part;
                option.textContent = part;
                partSelect.appendChild(option);
            });
            partsSection.style.display = 'block';
        })
        .catch(error => console.error('Fehler beim Laden der Teile:', error));
    }

    // --- Event Listener für Teilauswahl ---
    partSelect.addEventListener('change', () => {
        const selectedPart = partSelect.value;
        if (!selectedPart) {
            resultSection.style.display = 'none';
            return;
        }
        apiFetch('/api/schematic', {
            method: 'POST',
            body: JSON.stringify({ part: selectedPart })
        })
        .then(data => {
            if (data.schematic) {
                schematicResult.textContent = `'${data.schematic}'`;
                resultSection.style.display = 'block';
            } else {
                resultSection.style.display = 'none';
            }
        })
        .catch(error => console.error('Fehler beim Laden des Schaltplans:', error));
    });

    // --- Admin-spezifische Funktionen ---
    if (addUserForm) {
        addUserForm.addEventListener('submit', (e) => {
            e.preventDefault();
            addUserStatus.textContent = '';
            addUserStatus.classList.remove('error-message');

            const username = e.target['new-username'].value;
            const password = e.target['new-password'].value;
            const role = e.target['new-role'].value;

            apiFetch('/api/admin/users', {
                method: 'POST',
                body: JSON.stringify({ username, password, role })
            })
            .then(data => {
                addUserStatus.textContent = data.message || 'Benutzer erfolgreich erstellt!';
                loadUsers(); // Benutzerliste neu laden
                addUserForm.reset();
            })
            .catch(async (error) => {
                let errorMessage = 'Fehler beim Erstellen des Benutzers.';
                try {
                    // Versuchen, die Fehlerdetails aus der Antwort zu extrahieren
                    const errorData = await error.response.json();
                    if (errorData.detail) {
                        errorMessage = errorData.detail;
                    }
                } catch (e) {
                    // Fallback, wenn die Antwort kein JSON ist
                }
                addUserStatus.textContent = errorMessage;
                addUserStatus.classList.add('error-message');
            });
        });
    }

    if (backupUsersButton) {
        backupUsersButton.addEventListener('click', () => {
            apiFetch('/api/admin/backup/users')
                .then(response => response.blob()) // Die Antwort als Binärdaten (Blob) behandeln
                .then(blob => {
                    // Eine temporäre URL für die heruntergeladenen Daten erstellen
                    const url = window.URL.createObjectURL(blob);
                    // Einen unsichtbaren Link erstellen, um den Download zu starten
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'users_backup.json'; // Der Dateiname für den Download
                    document.body.appendChild(a);
                    a.click();
                    // Aufräumen: Die temporäre URL freigeben und den Link entfernen
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                })
                .catch(error => {
                    console.error('Fehler beim Herunterladen des Backups:', error);
                    alert('Das Backup konnte nicht heruntergeladen werden.');
                });
        });
    }

    function loadUsers() {
        apiFetch('/api/admin/users')
            .then(users => {
                userTableBody.innerHTML = '';
                users.forEach(user => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${user.username}</td>
                        <td>${user.role}</td>
                        <td class="actions">
                            <button class="edit-btn" data-username="${user.username}" data-role="${user.role}">Bearbeiten</button>
                            <button class="delete-btn" data-username="${user.username}">Löschen</button>
                        </td>
                    `;
                    userTableBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Fehler beim Laden der Benutzer:', error);
                userTableBody.innerHTML = '<tr><td colspan="3">Benutzer konnten nicht geladen werden.</td></tr>';
            });
    }

    userTableBody.addEventListener('click', (e) => {
        const target = e.target;
        const username = target.dataset.username;

        if (target.classList.contains('edit-btn')) {
            const role = target.dataset.role;
            editUsernameSpan.textContent = username;
            editUserOriginalUsername.value = username;
            editUserForm.elements['edit-role'].value = role;
            editUserForm.elements['edit-password'].value = '';
            editUserModal.style.display = 'block';
        }

        if (target.classList.contains('delete-btn')) {
            if (confirm(`Sind Sie sicher, dass Sie den Benutzer '${username}' löschen möchten?`)) {
                apiFetch(`/api/admin/users/${username}`, { method: 'DELETE' })
                    .then(data => {
                        alert(data.message || 'Benutzer gelöscht.');
                        loadUsers();
                    })
                    .catch(async (error) => {
                        let errorMessage = 'Fehler beim Löschen des Benutzers.';
                        try {
                            const errorData = await error.response.json();
                            if (errorData.detail) errorMessage = errorData.detail;
                        } catch (e) {}
                        alert(errorMessage);
                    });
            }
        }
    });

    // --- Modal-Logik ---
    closeModalButton.addEventListener('click', () => {
        editUserModal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target == editUserModal) {
            editUserModal.style.display = 'none';
        }
    });

    editUserForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = editUserOriginalUsername.value;
        const newPassword = e.target['edit-password'].value;
        const newRole = e.target['edit-role'].value;

        const updateData = {};
        if (newPassword) {
            updateData.new_password = newPassword;
        }
        updateData.new_role = newRole;

        apiFetch(`/api/admin/users/${username}`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        })
        .then(data => {
            alert(data.message || 'Benutzer aktualisiert.');
            editUserModal.style.display = 'none';
            loadUsers();
        })
        .catch(error => {
            console.error('Fehler beim Aktualisieren des Benutzers:', error);
            alert('Aktualisierung fehlgeschlagen.');
        });
    });


    // --- Hilfsfunktionen ---
    document.addEventListener('click', (event) => {
        if (!errorSearch.contains(event.target)) {
            suggestionsBox.style.display = 'none';
        }
    });

    // --- Initialer Ladezustand ---
    if (token && userRole) {
        showApp();
    } else {
        showLogin();
    }
});
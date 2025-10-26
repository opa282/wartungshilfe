document.addEventListener('DOMContentLoaded', () => {
    const errorSearch = document.getElementById('error-search');
    const suggestionsBox = document.getElementById('suggestions-box');
    const errorDropdown = document.getElementById('error-dropdown');
    const partsSection = document.getElementById('parts-section');
    const partSelect = document.getElementById('part-select');
    const resultSection = document.getElementById('result-section');
    const schematicResult = document.getElementById('schematic-result');

    // --- Füllt das Dropdown-Menü mit allen Fehlern ---
    function loadAllErrorsDropdown() {
        fetch('/api/all_errors')
            .then(response => response.json())
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
                errorDropdown.disabled = false; // KORREKTUR: Dropdown auch im Fehlerfall aktivieren
            });
    }

    // --- Event Listener für das Dropdown-Menü ---
    errorDropdown.addEventListener('change', () => {
        const selectedError = errorDropdown.value;
        
        // Interaktion synchronisieren
        errorSearch.value = '';
        suggestionsBox.style.display = 'none';
        
        if (selectedError) {
            fetchParts(selectedError);
        } else {
            partsSection.style.display = 'none';
            resultSection.style.display = 'none';
        }
    });

    // --- Event Listener für die Fehlersuche ---
    errorSearch.addEventListener('input', () => {
        // Interaktion synchronisieren
        errorDropdown.selectedIndex = 0;

        const query = errorSearch.value;
        
        partsSection.style.display = 'none';
        resultSection.style.display = 'none';
        partSelect.innerHTML = '';

        if (query.length < 2) {
            suggestionsBox.innerHTML = '';
            suggestionsBox.style.display = 'none';
            return;
        }

        fetch(`/api/search_errors?query=${encodeURIComponent(query)}`)
            .then(response => response.json())
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
                suggestionsBox.style.display = 'none';
            });
    });

    // --- Bestehende Funktionen ---
    function fetchParts(error) {
        const requestBody = { error: error };

        fetch('/api/parts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        })
        .then(response => response.json())
        .then(parts => {
            partSelect.innerHTML = '<option value="">-- Bitte wählen --</option>';
            parts.forEach(part => {
                const option = document.createElement('option');
                option.value = part;
                option.textContent = part;
                partSelect.appendChild(option);
            });
            partsSection.style.display = 'block';
        })
        .catch(error => {
            console.error('Fehler beim Laden der Teile:', error);
        });
    }

    partSelect.addEventListener('change', () => {
        const selectedPart = partSelect.value;

        if (!selectedPart) {
            resultSection.style.display = 'none';
            return;
        }
        
        const requestBody = { part: selectedPart };

        fetch('/api/schematic', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        })
        .then(response => response.json())
        .then(data => {
            if (data.schematic) {
                schematicResult.textContent = `\'${data.schematic}\'`;
                resultSection.style.display = 'block';
            } else {
                resultSection.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Fehler beim Laden des Schaltplans:', error);
        });
    });
    
    document.addEventListener('click', (event) => {
        if (!errorSearch.contains(event.target)) {
            suggestionsBox.style.display = 'none';
        }
    });

    // --- Initialer Aufruf beim Laden der Seite ---
    loadAllErrorsDropdown();
});
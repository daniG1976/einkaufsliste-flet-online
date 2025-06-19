# Basis-Image auswählen (Python 3.12 ist eine gute Wahl für die meisten Anwendungen)
FROM python:3.11-slim-buster

# Arbeitsverzeichnis im Container festlegen
WORKDIR /app

# Die Datei 'requirements.txt' in das Arbeitsverzeichnis kopieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den Rest deines App-Codes (einschließlich main.py) in das Arbeitsverzeichnis kopieren
COPY . .

# Eine Umgebungsvariable 'PORT' setzen, die Flet lesen wird
ENV PORT=8080 
# Den Port, auf dem die App lauscht, nach außen hin "freigeben"
EXPOSE 8080 

# Der Befehl, der die Anwendung startet, wenn der Container gestartet wird
CMD ["python", "main.py"]
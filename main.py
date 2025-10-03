import flet as ft
import json # Behalten wir für den Moment, falls noch Referenzen existieren, kann aber später entfernt werden.
import os # Ebenfalls beibehalten, falls noch Referenzen existieren.
import asyncio
import firebase_admin # NEU: Für die Firebase-Verwaltung
from firebase_admin import credentials, db # NEU: Für Authentifizierung und Datenbankzugriff
from zweiteseite import zweiteseite_view
import uuid
import platform
import base64
from fastapi import FastAPI
import asyncio
import sounddevice as sd
from google.cloud import speech
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware



os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "einkaufsliste-stt-b14b1464c759.json"

# FastAPI-App für Web-Audio
web_app = FastAPI()
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

speech_client = speech.SpeechClient()

@web_app.post("/upload_audio")
async def upload_audio(payload: dict):
    try:
        audio_bytes = base64.b64decode(payload["audio"])
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code="de-DE",
        )
        response = speech_client.recognize(config=config, audio=audio)
        text = response.results[0].alternatives[0].transcript if response.results else ""
        return {"text": text}
    except Exception as e:
        return {"error": str(e)}
    
@web_app.get("/set_text")
async def set_text(request: Request):
    text = request.query_params.get("text", "")
    # Achtung: text1 und page sind innerhalb von main() definiert, daher können wir sie hier nicht direkt nutzen.
    # Wir müssen diese Funktion stattdessen über eine Brücke oder Callback an main() weitergeben.
    return {"status": "ok"}


favoriten_dialog_state = {
    "selected_index": None,  # Index des aktuell ausgewählten Favoriten
    "fruits": []             # Liste der Favoriten
}

selected_category_index = 0 

def record_audio(duration=3, fs=16000):
    print("Aufnahme startet...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    print("Aufnahme beendet.")
    return audio.flatten().tobytes()


def speech_to_text(audio_bytes, encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, sample_rate_hertz=16000):
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=encoding,
        sample_rate_hertz=sample_rate_hertz,
        language_code="de-DE"
    )
    response = client.recognize(config=config, audio=audio)
    if response.results:
        return response.results[0].alternatives[0].transcript
    return ""



async def start_browser_recording(page: ft.Page, textfield: ft.TextField):
    js_code = """
    async function recordAudio() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            let chunks = [];

            mediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };

            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunks, { type: "audio/webm" });
                const reader = new FileReader();
                reader.onloadend = async () => {
                    const base64data = reader.result.split(",")[1];
                    const response = await fetch("/upload_audio", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ audio: base64data })
                    });
                    const result = await response.json();
                    // Flet-Feld in Python updaten
                    fetch(`/set_text?text=${encodeURIComponent(result.text)}`);
                };
                reader.readAsDataURL(blob);
            };

            mediaRecorder.start();
            setTimeout(() => mediaRecorder.stop(), 3000);
        } catch (err) {
            console.error("Fehler beim Zugriff auf Mikro:", err);
        }
    }
    recordAudio();
    """
    page.window_run_js(js_code)





class ShoppingItem:
    def __init__(self, name: str, amount: str, unit: str, is_offer: bool):
        self.name = name
        self.amount = amount
        self.unit = unit
        self.is_offer = is_offer
        self.uuid = str(uuid.uuid4())


    def to_dict(self):
        return {
            "name": self.name,
            "amount": self.amount,
            "unit": self.unit,
            "is_offer": self.is_offer
        }

    @classmethod
    def from_dict(cls, data_dict):
        return cls(
            name=data_dict.get("name", "Unbekannt"),
            amount=data_dict.get("amount", "1"),
            unit=data_dict.get("unit", "Stück"),
            is_offer=data_dict.get("is_offer", False)
        )

    def __eq__(self, other):
        if not isinstance(other, ShoppingItem):
            return NotImplemented
        return self.name == other.name and \
            self.amount == other.amount and \
            self.unit == other.unit and \
            self.is_offer == other.is_offer

    def __hash__(self):
        return hash((self.name, self.amount, self.unit, self.is_offer))

def main(page: ft.Page):

    page.resize_to_avoid_bottom_inset = True

    page.title = "Unsere Gemeinsame Einkaufsliste"

    #page.expand = True

    #page.vertical_alignment = ft.MainAxisAlignment.START

    page.bgcolor = ft.Colors.TRANSPARENT

    page.padding = 0 # Wichtig: Padding der Seite auf 0 setzen, damit der Gradient den ganzen Bildschirm füllt

    page.theme_mode = ft.ThemeMode.DARK

    #page.scroll = ft.ScrollMode.AUTO # Aktiviert Scrollen bei Bedarf, falls der Inhalt größer wird

    page.theme = ft.Theme(font_family="Roboto")

    #page.extend_body_behind_appbar = True
    
    selected_fruit_index = None  # global speichern
    
    try:

        # Versuchen, die Umgebungsvariable zu lesen

        firebase_credentials_json_string = os.getenv("FIREBASE_CREDENTIALS_JSON_CONTENT")

        # NEU: DEBUG-AUSGABE START - GESICHERT GEGEN NoneType

        if firebase_credentials_json_string: # Hinzugefügte Prüfung!

            print(f"DEBUG: Geladene Firebase-JSON-String (erste 100 Zeichen): {firebase_credentials_json_string[:100]}...")

            print(f"DEBUG: Länge des gelesenen Strings: {len(firebase_credentials_json_string)}")

        else: # Hinzugefügte else-Anweisung für Debug-Zwecke

            print("DEBUG: Umgebungsvariable FIREBASE_CREDENTIALS_JSON_CONTENT ist nicht gesetzt.")

        # NEU: DEBUG-AUSGABE ENDE


        if firebase_credentials_json_string:

            try:

                cred_data = json.loads(firebase_credentials_json_string)

                cred = credentials.Certificate(cred_data)

                print("Firebase-Anmeldeinformationen erfolgreich aus Umgebungsvariable geladen.")

            except json.JSONDecodeError as e:

                print(f"DEBUG: JSON-Parsing-Fehler: {e}")

                raise

        else:

            # Fallback für lokale Entwicklung: Versuchen Sie die Datei zu laden

            try: # Hier fehlte ein try-Block, der den FileNotFoundError fängt, wenn die lokale Datei nicht da ist.

                cred = credentials.Certificate("firebase_credentials.json")

                print("Firebase-Anmeldeinformationen erfolgreich aus lokaler Datei geladen.")

            except FileNotFoundError:

                print("DEBUG: Lokale 'firebase_credentials.json' nicht gefunden.")

                raise FileNotFoundError("firebase_credentials.json nicht gefunden.") # Wirft ihn zur äußeren Behandlung


        # Initialisiere Firebase nur, wenn es noch nicht initialisiert wurde

        if not firebase_admin._apps:

            firebase_admin.initialize_app(cred, {

                'databaseURL': 'https://einkaufs-app-ae8e9-default-rtdb.europe-west1.firebasedatabase.app/'

            })

            print("Firebase erfolgreich initialisiert.")

        else:

            print("Firebase bereits initialisiert (Hot Reload).")


        db_ref = db.reference('/einkaufsliste')


    except FileNotFoundError:

        error_msg = "Fehler: 'firebase_credentials.json' nicht gefunden. Stellen Sie sicher, dass sie lokal vorhanden ist oder die Umgebungsvariable auf Render gesetzt ist."

        print(error_msg)

        page.add(ft.Text(f"Fehler beim Starten der App: {error_msg}", color=ft.Colors.RED))

        page.update()

        return


    except json.JSONDecodeError as e:

        error_msg = f"Fehler beim Parsen der Firebase-Anmeldeinformationen aus der Umgebungsvariable: {e}. Überprüfen Sie das Format."

        print(error_msg)

        page.add(ft.Text(f"Fehler beim Starten der App: {error_msg}", color=ft.Colors.RED))

        page.update()

        return


    except Exception as e:
        error_msg = f"Ein unerwarteter Fehler bei der Firebase-Initialisierung ist aufgetreten: {e}"
        print(error_msg)
        page.add(ft.Text(f"Fehler beim Starten der App: {error_msg}", color=ft.Colors.RED))
        page.update()
        return

    def alles_loeschen(e):
        einkaufsliste_daten.clear()
        page.run_task(update_einkaufsliste_ui)
        save_data()
        page.update()

    def open_hitprospekt(e):
        page.go("/zweiteseite")
       
    def save_data():
        try:
            data_to_save = [item.to_dict() for item in einkaufsliste_daten]
            db_ref.set(data_to_save)
            print("Daten erfolgreich in Firebase gespeichert.")
        except Exception as e:
            print(f"Fehler beim Speichern der Daten in Firebase: {e}")


    def load_and_listen_data():
        try:
            def firebase_data_listener(event):
                print(f"Firebase-Datenänderung erkannt: {event.event_type} at {event.path}")
                if event.data:
                    new_data_from_firebase = []
                    if isinstance(event.data, dict):
                        sorted_keys = sorted(event.data.keys(), key=lambda k: int(k))
                        for key in sorted_keys:
                            new_data_from_firebase.append(ShoppingItem.from_dict(event.data[key]))
                    elif isinstance(event.data, list):
                        for item_dict in event.data:
                            new_data_from_firebase.append(ShoppingItem.from_dict(item_dict))
                    else:
                        print(f"Unerwartetes Datenformat von Firebase: {type(event.data)}. Leere Liste.")
                        new_data_from_firebase = [] # Bei unerwartetem Format leeren
                    einkaufsliste_daten.clear()
                    einkaufsliste_daten.extend(new_data_from_firebase)
                    page.run_task(update_einkaufsliste_ui)
                else:
                    if einkaufsliste_daten: # Nur leeren, wenn nicht schon leer
                        einkaufsliste_daten.clear()
                        page.run_task(update_einkaufsliste_ui)
            db_ref.listen(firebase_data_listener)
            print("Firebase-Echtzeit-Listener erfolgreich gestartet.")

        except Exception as e:
            print(f"Fehler beim Starten des Firebase-Listeners: {e}")
            page.run_task(lambda: page.add(ft.Text(f"Fehler beim Laden der Einkaufsliste: {e}", color=ft.Colors.RED)))



    async def show_duplicate_bottom_sheet(page: ft.Page, item_name: str):

   

        # NEU: Die Funktion zum Schließen des Dialogs

        def close_duplicate_sheet(e):

            duplicate_sheet.open = False

            page.update()


        bottom_sheet_content = ft.Container(

            width=page.width,

            bgcolor="#213745",

            content=ft.Column(

                [

                    ft.Text(

                        f'"{item_name}" ist bereits in der Einkaufsliste!',

                        weight=ft.FontWeight.BOLD,

                        size=18,

                        text_align=ft.TextAlign.CENTER

                    ),

                    ft.ElevatedButton(

                        "OK",

                        color="#EAD9C9",

                        bgcolor="#FF5B8E",

                        on_click=close_duplicate_sheet, # HIER: die neue Funktion zuweisen

                        width=300,

                        height=40,

                    ),

                ],

                tight=True,

                horizontal_alignment=ft.CrossAxisAlignment.CENTER

            ),

            padding=ft.padding.all(20),

        )


        duplicate_sheet = ft.CupertinoBottomSheet(

            content=bottom_sheet_content,

            modal=True

        )

       

        page.overlay.append(duplicate_sheet)

        duplicate_sheet.open = True

        page.update()


   

    def scroll_to_control(e):

        einkaufsliste_ref.current.scroll_to(offset=-1, duration=500) # -1 scrollt zum Ende

        page.update()



    einkaufsliste_daten: list[ShoppingItem] = []

    einkaufsliste_ref = ft.Ref[ft.ListView]()

    new_item_name_input = ft.Ref[ft.TextField]()


    async def fab_clicked(e):
        page.open(dlg_modal)

        # Favoriten laden und Picker aktualisieren
        await load_favorites()

        # Textfeld leeren beim Öffnen, damit alte Auswahl nicht bleibt
        if new_item_name_input.current:
            new_item_name_input.current.value = ""
            new_item_name_input.current.update()

        page.update()

        # Fokus auf Textfeld setzen
        async def set_focus_on_dialog_input():
            await asyncio.sleep(0.1)
            if new_item_name_input.current:
                new_item_name_input.current.focus()
                page.update()
            else:
                print("Fehler: new_item_name_input.current ist nicht verfügbar nach Dialogöffnung.")

        page.run_task(set_focus_on_dialog_input)

    favoriten_anzeige = ft.Ref[ft.Text]()

    async def load_favorites():
        try:
            favorites_from_db = db.reference('favorites').get()
            if favorites_from_db is None:
                favorites_from_db = []

            # Globalen State aktualisieren
            favoriten_dialog_state["fruits"] = list(favorites_from_db)
            favoriten_dialog_state["selected_index"] = None  # keine Auswahl beim Öffnen

            # Picker neu aufbauen
            cupertino_picker_widget.controls = [
                ft.Text(value=f, color="EAD9C9") for f in favoriten_dialog_state["fruits"]
            ]
            cupertino_picker_widget.selected_index = None
            cupertino_picker_widget.update()

            print(f"Favoriten neu geladen: {favoriten_dialog_state['fruits']}")

        except Exception as ex:
            print(f"Fehler beim Laden der Favoriten: {ex}")

  
    async def favorit_hinzufuegen(e):
        new_fav = text1.value.strip()  # text1 ist dein TextField
        if not new_fav:
            return

        fruits = favoriten_dialog_state["fruits"]
        if new_fav not in fruits:
            fruits.append(new_fav)
            fruits.sort()
            favoriten_dialog_state["fruits"] = fruits

            # Firebase aktualisieren
            try:
                db.reference("favorites").set(fruits)
                print(f"Neuer Favorit hinzugefügt: {new_fav}")
            except Exception as ex:
                print(f"Fehler beim Aktualisieren: {ex}")

            # Picker neu aufbauen
            cupertino_picker_widget.controls = [ft.Text(value=f, color="EAD9C9") for f in fruits]
            cupertino_picker_widget.update()

        # Textfeld leeren
        text1.value = ""
        text1.update()

    
    def favorit_loeschen(e):
        idx = favoriten_dialog_state.get("selected_index")
        fruits = favoriten_dialog_state["fruits"]

        if idx is None or idx < 0 or idx >= len(fruits):
            print("Kein gültiger Favorit ausgewählt.")
            return

        item_to_delete = fruits.pop(idx)
        print(f"Lösche Favorit: {item_to_delete}")

        # Firebase aktualisieren
        try:
            db.reference("favorites").set(fruits)
            print("Favoritenliste in Firebase aktualisiert.")
        except Exception as ex:
            print(f"Fehler beim Aktualisieren: {ex}")

        # Picker neu aufbauen und Auswahl zurücksetzen
        cupertino_picker_widget.controls = [ft.Text(value=f, color="EAD9C9") for f in fruits]
        cupertino_picker_widget.selected_index = None
        favoriten_dialog_state["selected_index"] = None
        cupertino_picker_widget.update()
        page.update()


    text1 =ft.TextField(
        value="",
        label="Artikel eingeben",
        border_color=ft.Colors.WHITE,
        expand=True,
        label_style=ft.TextStyle(color="EAD9C9"),
        text_style=ft.TextStyle(color="EAD9C9"),
        cursor_color="EAD9C9",
        border_radius=ft.border_radius.all(8),
        on_focus=scroll_to_control,
        ref=new_item_name_input,
        )


    numbers_field =ft.TextField(
        #keyboard_type=ft.KeyboardType.NUMBER,
        value="",
        label="Anzahl eingeben",
        border_color=ft.Colors.WHITE,
        expand=True,
        label_style=ft.TextStyle(color="EAD9C9"),
        text_style=ft.TextStyle(color="EAD9C9"),
        cursor_color="EAD9C9",
        border_radius=ft.border_radius.all(8),
        on_focus=scroll_to_control
        )


    weight_field =ft.TextField(
        #keyboard_type=ft.KeyboardType.NUMBER,
        value="",
        label="Gewicht eingeben",
        border_color=ft.Colors.WHITE,
        expand=True,
        label_style=ft.TextStyle(color="EAD9C9"),
        text_style=ft.TextStyle(color="EAD9C9"),
        cursor_color="EAD9C9",
        border_radius=ft.border_radius.all(8),
        on_focus=scroll_to_control
        )


    def handle_picker_change(e):
        idx = e.control.selected_index
        favoriten_dialog_state["selected_index"] = idx
        print(f"Picker Auswahl geändert: {idx}")

        # Textfeld aktualisieren
        if idx is not None and 0 <= idx < len(favoriten_dialog_state["fruits"]):
            selected_value = favoriten_dialog_state["fruits"][idx]
            print(f"Ausgewählter Favorit: {selected_value}")

            if new_item_name_input.current:  # Ref auf Textfeld
                new_item_name_input.current.value = selected_value
                new_item_name_input.current.update()


    cupertino_picker_widget = ft.CupertinoPicker(
        selected_index=0,
        magnification=1.15,  # Weniger Zoom
        squeeze=1.1,         # Etwas enger
        #use_magnifier=True,
        on_change=handle_picker_change,
        controls=[ft.Text(size=16, value=f, color="EAD9C9") for f in favoriten_dialog_state["fruits"]],
        height=150,          # Kleiner als vorher (200)
        item_extent=32,      # Weniger Platz pro Eintrag
    )
    
    Kategorien = [
        "Obst&Gemüse",
        "Milchprodukte",
        "Fleisch&Wurst",
        "Sonstiges",
        "Tiefkühl",
        "Vorräte"
    ]
    
    def handle_category_change(e):
        global selected_category_index
        selected_category_index = e.control.selected_index
        print(f"Kategorie ausgewählt: {Kategorien[selected_category_index]}")
    
    cupertino_picker_widget2 = ft.CupertinoPicker(
        selected_index=0,
        magnification=1.15,  
        squeeze=1.1,         
        use_magnifier=True,
        on_change= handle_category_change,
        controls=[ft.Text(size=16, value=f, color="EAD9C9") for f in Kategorien],
        height=150,          # Kleiner als vorher (200)
        item_extent=32,      # Weniger Platz pro Eintrag
    )


    
    cupertino_picker_widget.on_change = handle_picker_change

    def handle_drag_accept(e):
        dragged_draggable = page.get_control(e.src_id)
        dragged_item_data = dragged_draggable.data
        target_item_data = e.control.data # DragTarget hat das ShoppingItem als data        
        if dragged_item_data and target_item_data:
            try:
                old_index = einkaufsliste_daten.index(dragged_item_data)
                new_index = einkaufsliste_daten.index(target_item_data)
            except ValueError:
                print("Fehler: Gezogenes oder Ziel-Element nicht in der Datenliste gefunden.")
                return

            einkaufsliste_daten.pop(old_index)    
            einkaufsliste_daten.insert(new_index, dragged_item_data)
            save_data()
            page.run_task(update_einkaufsliste_ui)


    async def update_einkaufsliste_ui():
        if einkaufsliste_ref.current is not None:
            # Alte Controls entfernen
            einkaufsliste_ref.current.controls = [
                create_shopping_card(item) for item in einkaufsliste_daten
            ]
            einkaufsliste_ref.current.update()
            # page.update() ist hier nicht nötig, ListView.update() reicht


    def add_favorite(e):
        if favoriten_anzeige.current and favoriten_anzeige.current.value:
            text1.value = favoriten_anzeige.current.value # Setze den Wert des Textfeldes
            text1.update()


    def create_shopping_card(item: ShoppingItem):
        offer_icon_color = ft.Colors.RED if item.is_offer else ft.Colors.WHITE

        def handle_dismiss(e: ft.DismissibleDismissEvent):
            if item in einkaufsliste_daten:
                einkaufsliste_daten.remove(item)
                save_data()
            page.run_task(update_einkaufsliste_ui)

        # Die gesamte visuelle Karte, die verschoben werden soll
        card_content = ft.Card(
            content=ft.Container(
                border_radius=ft.border_radius.all(10),
                gradient=ft.LinearGradient(
                    begin=ft.alignment.center_left,
                    end=ft.alignment.center_right,
                    colors=["#213745", "#FF5B8E"],
                ),

                padding=ft.padding.symmetric(vertical=4, horizontal=10),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[

                        ft.Row(
                            controls=[
                                ft.Icon(
                                    name=ft.Icons.FONT_DOWNLOAD,
                                    color=offer_icon_color,
                                ),

                                ft.Text(

                                    value=f"  {item.unit} {item.amount} {item.name}",

                                    color=ft.Colors.WHITE,

                                    size=24,

                                    expand=True,

                                    text_align=ft.TextAlign.START,

                                ),

                            ],

                            expand=True

                        ),

                        # Rechter Teil: Das DRAG_INDICATOR Icon ist jetzt das Draggable

                        ft.Draggable(

                            group="shopping_items",

                            content=ft.IconButton(

                                icon=ft.Icons.DRAG_INDICATOR,

                                icon_color=ft.Colors.WHITE,

                            ),

                            content_when_dragging=ft.Container(

                                width=100, # Passe die Größe des "Schattenbildes" an

                                height=60,

                                bgcolor=ft.Colors.with_opacity(0.5, "#213745"),

                                border_radius=ft.border_radius.all(10),

                                alignment=ft.alignment.center,

                            ),

                            data=item,

                        ),

                    ]

                )

            ),

            elevation=5,

        )


        return ft.DragTarget(

            group="shopping_items",

            content=ft.Dismissible(

                key=item.uuid, # Wichtig: Nutze einen eindeutigen Schlüssel für jedes Element

                content=card_content,

                dismiss_direction=ft.DismissDirection.HORIZONTAL,

                background=ft.Container(

                    alignment=ft.alignment.center_left,

                    border_radius=ft.border_radius.all(10),

                    bgcolor=ft.Colors.GREEN_700,

                    content=ft.Icon(ft.Icons.CHECK, color=ft.Colors.WHITE, size=40),

                    padding=ft.padding.only(left=20)

                ),

                secondary_background=ft.Container(

                    alignment=ft.alignment.center_right,

                    border_radius=ft.border_radius.all(10),

                    bgcolor=ft.Colors.RED_700,

                    content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=40),

                    padding=ft.padding.only(right=20)

                ),

                on_dismiss=handle_dismiss,

                dismiss_thresholds={

                    ft.DismissDirection.START_TO_END: 0.2,

                    ft.DismissDirection.END_TO_START: 0.2,

                },

            ),

            on_accept=handle_drag_accept,

            data=item,

        )


    dialog_offer_button = ft.IconButton(icon=ft.Icons.FONT_DOWNLOAD, icon_color=ft.Colors.WHITE, icon_size=30)


    def toggle_dialog_offer_button(e):

        if dialog_offer_button.icon_color == ft.Colors.WHITE:

            dialog_offer_button.icon_color = ft.Colors.RED

        else:

            dialog_offer_button.icon_color = ft.Colors.WHITE


        dialog_offer_button.update()


    dialog_offer_button.on_click = toggle_dialog_offer_button # Zuweisung der Toggle-Funktion


    def dialog_add_clicked(e):

        item_name = text1.value if text1.value else favoriten_anzeige.current.value

        if item_name and any(item.name.lower() == item_name.lower() for item in einkaufsliste_daten):

            page.close(dlg_modal)


            page.run_task(show_duplicate_bottom_sheet, page, item_name)

            text1.value = ""

            numbers_field.value = ""

            weight_field.value = ""

            dialog_offer_button.icon_color = ft.Colors.WHITE

            dialog_offer_button.update()

            page.update()

            return


        item_amount = numbers_field.value

        item_unit = weight_field.value

        is_offer = dialog_offer_button.icon_color == ft.Colors.RED


        new_item = ShoppingItem(

            name=item_name,

            amount=item_amount,

            unit=item_unit,

            is_offer=is_offer

        )


        einkaufsliste_daten.append(new_item)

        save_data()

        # Nachdem ein neues Item hinzugefügt wurde, die UI komplett aktualisieren

        page.run_task(update_einkaufsliste_ui)

        page.close(dlg_modal)# Schließe den Dialog über die Seitenreferenz


        text1.value = ""

        numbers_field.value = ""

        weight_field.value = ""

        dialog_offer_button.icon_color = ft.Colors.WHITE

        dialog_offer_button.update()

        page.update()


    dialog_add_button = ft.IconButton(icon=ft.Icons.ADD, icon_color=ft.Colors.WHITE, icon_size=30, on_click=dialog_add_clicked)
    

    def speech_button_clicked(e):
        if platform.system() in ["Windows", "Linux", "Darwin"]:  # Desktop
            audio = record_audio(duration=3)
            text = speech_to_text(audio)
            if text:
                text1.value = text
                page.update()
        else:  # Web (iPhone / Browser)
            asyncio.create_task(start_browser_recording(page, text1))


    speech_add_button = ft.IconButton(
        icon=ft.Icons.MIC,
        icon_color=ft.Colors.WHITE,
        icon_size=30,
        on_click=speech_button_clicked
    )


    dialog_gradient = ft.LinearGradient(

        begin=ft.alignment.top_center,

        end=ft.alignment.bottom_center,

        colors=[

            "#213745",
            #"EAD9C9", # Startfarbe des Dialog-Gradients
            "#FF5B8E", # Endfarbe des Dialog-Gradients
        ],
    )

    dialog_content_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[                        
                        ft.IconButton(icon=ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.WHITE, icon_size=30, on_click=favorit_loeschen),
                        ft.Container(
                            content=cupertino_picker_widget,
                            expand=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(

                    controls=[

                        ft.IconButton(icon=ft.Icons.FAVORITE, icon_color=ft.Colors.WHITE, icon_size=30, on_click=favorit_hinzufuegen),
                        ft.Container(
                            content=text1,
                            expand=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.IconButton(icon=ft.Icons.NUMBERS, icon_color=ft.Colors.WHITE, icon_size=30, on_click=None),
                        ft.Container(
                            content=numbers_field,
                            expand=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.IconButton(icon=ft.Icons.SCALE, icon_color=ft.Colors.WHITE, icon_size=30, on_click=None),
                        ft.Container(
                            content=weight_field,
                            expand=True,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[                        
                        ft.IconButton(icon=ft.Icons.CATEGORY, icon_color=ft.Colors.WHITE, icon_size=30, on_click=None),
                        ft.Container(
                            content=cupertino_picker_widget2,
                            expand=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            scroll="auto",
            spacing=25,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=350,
        height=580,
        padding=20,
        border_radius=ft.border_radius.all(10),
        )

   


    gradient_dialog_container = ft.Container(
        expand= True,
        content=ft.Column( # Nutze eine Column, um Titel, den Haupt-Content und die Aktionen zu stapeln
        [
            ft.Text("Wir brauchen:", color=(0xFFEAD9C9), size=30, weight=ft.FontWeight.BOLD),
            dialog_content_container,
            ft.Row(
                controls=[speech_add_button, dialog_offer_button, dialog_add_button],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
        spacing=10, # Abstand zwischen den Elementen in dieser Column
        horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Zentriere den Inhalt horizontal in der Column
    ),
    padding=12, # Innenabstand für den gesamten Dialoginhalt
    gradient=dialog_gradient, # Hier wird der Gradient angewendet!
    border_radius=ft.border_radius.all(10), # Abgerundete Ecken für den Dialog

)



    dlg_modal = ft.AlertDialog(
        bgcolor=ft.Colors.TRANSPARENT,
        content=gradient_dialog_container,
        scrollable=True,
        shape=ft.RoundedRectangleBorder(radius=ft.border_radius.all(10)),
        content_padding=ft.padding.all(10),
        )


    def route_change(route):

        page.views.clear()

       

        if page.route == "/":

            main_view_controls = [

                ft.Stack(

                    [

                        ft.Container(

                            expand=True,

                            gradient=ft.LinearGradient(

                                begin=ft.alignment.top_center,

                                end=ft.alignment.bottom_center,

                                colors=["#EAD9C9", "#FF5B8E"],

                            ),

                            padding=0,

                            margin=0,

                            border=ft.border.all(0, ft.Colors.TRANSPARENT),

                        ),

                        ft.Column(

                            [

                                ft.Container(

                                    content=ft.Row(

                                        [

                                            ft.Container(width=30),

                                            ft.Container(

                                                expand=True,

                                                content=ft.Text(

                                                    "Meine Einkaufsliste",

                                                    size=30,

                                                    weight=ft.FontWeight.BOLD,

                                                    color="#213745",

                                                    text_align=ft.TextAlign.CENTER,

                                                ),

                                            ),

                                            ft.Container(

                                                ft.PopupMenuButton(

                                                    icon_color="#213745",

                                                    bgcolor=ft.Colors.TRANSPARENT,

                                                    items=[

                                                        ft.PopupMenuItem(text="Liste Löschen", on_click=alles_loeschen),

                                                        ft.PopupMenuItem(text="HIT Angebote", on_click=lambda _: page.go("/zweiteseite")),

                                                        ft.PopupMenuItem(text="Über"),

                                                    ]

                                                ),

                                                width=50,

                                            ),

                                        ],

                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,

                                    ),

                                    padding=ft.padding.only(top=30, bottom=12),

                                    alignment=ft.alignment.center,

                                ),

                                ft.ListView(

                                    ref=einkaufsliste_ref,

                                    expand=True,

                                    spacing=6,

                                    padding=12,

                                ),

                            ],

                            expand=True,

                            alignment=ft.MainAxisAlignment.START,

                        ),

                    ],

                    expand=True,

                )

            ]

            page.views.append(

                ft.View(

                    route="/",

                    controls=main_view_controls,

                    padding=0,

                    floating_action_button=ft.FloatingActionButton(

                        content=ft.Icon(name=ft.Icons.ADD, color="#EAD9C9"),

                        on_click=fab_clicked,

                        bgcolor="#213745",

                        shape=ft.CircleBorder(),

                    ),

                    floating_action_button_location=ft.FloatingActionButtonLocation.CENTER_FLOAT

                )

            )



        elif page.route == "/zweiteseite":
            page.views.append(zweiteseite_view(page))

        page.update()

    page.on_route_change = route_change
    page.go(page.route)
    page.update()
    
    load_and_listen_data()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8550)), host="0.0.0.0")
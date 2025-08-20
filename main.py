import flet as ft
import json # Behalten wir für den Moment, falls noch Referenzen existieren, kann aber später entfernt werden.
import os # Ebenfalls beibehalten, falls noch Referenzen existieren.
import asyncio
import firebase_admin # NEU: Für die Firebase-Verwaltung
from firebase_admin import credentials, db # NEU: Für Authentifizierung und Datenbankzugriff
import threading

class ShoppingItem:
    def __init__(self, name: str, amount: str, unit: str, is_offer: bool):
        self.name = name
        self.amount = amount
        self.unit = unit
        self.is_offer = is_offer

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
        
    
    def save_data():
        try:
            # Konvertiere die aktuelle Liste der ShoppingItem-Objekte in eine Liste von Dictionaries
            data_to_save = [item.to_dict() for item in einkaufsliste_daten]
            # Speichere die gesamte Liste unter dem definierten Pfad in Firebase
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

    def fab_clicked(e):
        page.open(dlg_modal) 

        async def set_focus_on_dialog_input():
            await asyncio.sleep(0.1) 
            if new_item_name_input.current:
                new_item_name_input.current.focus()
                page.update() 
            else:
                print("Fehler: new_item_name_input.current ist nicht verfügbar nach Dialogöffnung.")
        page.run_task(set_focus_on_dialog_input)



    page.floating_action_button = ft.FloatingActionButton(  
            content=ft.Icon(name=ft.Icons.ADD, color="#EAD9C9"),
            on_click=fab_clicked, # Funktion korrekt zugewiesen
            bgcolor="#213745",
            shape=ft.CircleBorder(),
        )

    page.floating_action_button_location = ft.FloatingActionButtonLocation.CENTER_FLOAT
    page.update()


    favoriten_anzeige = ft.Ref[ft.Text]()

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


    fruits = [
        "Äpfel",
        "Bananen",

        "Milch",

        "Quark",

        "Wurst",

        "Käse",

        "Joghurt",

        "O-Saft",

        "Nudeln",

        "Nutella",

        "Kaffee"

    ]



    def handle_picker_change(e):

        selected_index = int(e.control.selected_index)

        if selected_index < len(fruits):

            selected_value = fruits[selected_index]

        else:

            selected_value = "N/A"


        # HIER ist die entscheidende Prüfung

        if favoriten_anzeige.current: # Nur aktualisieren, wenn das Widget existiert

            favoriten_anzeige.current.value = selected_value

            favoriten_anzeige.current.update()

        page.update() # Dialog aktualisieren, damit Ref-Text sichtbar wird


    cupertino_picker_widget = ft.CupertinoPicker(

        selected_index=0,

        magnification=1.22,

        squeeze=1.2,

        use_magnifier=True,

        on_change=handle_picker_change,

        controls=[ft.Text(value=f, color="EAD9C9") for f in fruits],

        height=200,

       item_extent=40,

    )

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
        if einkaufsliste_ref.current:
            einkaufsliste_ref.current.controls.clear()
            for item in einkaufsliste_daten:
                einkaufsliste_ref.current.controls.append(create_shopping_card(item))
            einkaufsliste_ref.current.update() 
            page.update()

    def add_favorite(e):
        if favoriten_anzeige.current and favoriten_anzeige.current.value:
            text1.value = favoriten_anzeige.current.value # Setze den Wert des Textfeldes
            text1.update()

    def create_shopping_card(item: ShoppingItem):
        offer_icon_color = ft.Colors.RED if item.is_offer else ft.Colors.WHITE
        def handle_dismiss(e: ft.DismissibleDismissEvent):
            if item in einkaufsliste_daten: # Überprüfen, ob das Element noch in der Datenliste ist
                einkaufsliste_daten.remove(item)
                save_data()
            page.run_task(update_einkaufsliste_ui)


        

        dismissible_card = ft.Dismissible(

            content=ft.Card(

                content=ft.Container(

                    border_radius=ft.border_radius.all(10),

                    gradient=ft.LinearGradient(

                        begin=ft.alignment.center_left,

                        end=ft.alignment.center_right,

                        colors=[

                        "#213745",

                        "#FF5B8E",

                        ],

                    ),

                    padding=10,

                    content=ft.Row(

                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,

                        vertical_alignment=ft.CrossAxisAlignment.CENTER,

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

                            ft.IconButton(

                                icon=ft.Icons.DRAG_INDICATOR,

                                icon_color=ft.Colors.WHITE,

                                on_click=None,

                            )

                        ]

                    )

                ),
                elevation=5,
            ),

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

            on_dismiss=handle_dismiss, # Diese Closure bindet 'item' korrekt
            dismiss_thresholds={
                ft.DismissDirection.START_TO_END: 0.2,
                ft.DismissDirection.END_TO_START: 0.2,
            },
        )


        return ft.DragTarget(
            group="shopping_items", # Muss derselben Gruppe wie der Draggable angehören
            content=ft.Draggable(
                group="shopping_items",
                content=dismissible_card,
                content_when_dragging=ft.Container(
                    width=dismissible_card.content.width,
                    height=dismissible_card.content.height,
                    bgcolor=0x80213745,
                    border_radius=ft.border_radius.all(10),
                    alignment=ft.alignment.center,
                ),
                data=item, # Das ShoppingItem wird mit dem Draggable mitgegeben
            ),
            on_accept=handle_drag_accept, # Event-Handler, wenn ein Element auf dieses Ziel fällt
            data=item, # Das ShoppingItem wird auch mit dem DragTarget mitgegeben, damit on_accept es identifizieren kann
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
                ft.Text(
                ref=favoriten_anzeige, # Behalte die Referenz, aber mache den Text unsichtbar
                value="", # Setze den Wert auf einen leeren String
                visible=False, # Der entscheidende Schritt: Das Widget ist nicht sichtbar
                ),
                ft.Row(
                    controls=[
                        ft.IconButton(icon=ft.Icons.FAVORITE, icon_color=ft.Colors.WHITE, icon_size=30, on_click=add_favorite),
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
                        ft.IconButton(icon=ft.Icons.NEW_LABEL, icon_color=ft.Colors.WHITE, icon_size=30, on_click=None),
                        ft.Container(
                            content=text1,
                            expand=True,
                        )
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
                        )
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
            ],
            scroll=True,
            spacing=25,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=350,
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
                controls=[dialog_offer_button, dialog_add_button],
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
        shape=ft.RoundedRectangleBorder(radius=ft.border_radius.all(10)),
        content_padding=ft.padding.only(left=18, right=18)

)

    #page.padding = 0
    #page.spacing = 0

    page.add(
        ft.Stack(
            [
                # Schicht 1: Der Hintergrund, der den ganzen Platz einnimmt
                ft.Container(
                    expand=True,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.top_center,
                        end=ft.alignment.bottom_center,
                        colors=["#EAD9C9", "#FF5B8E"],
                    ),
                ),
                # Schicht 2: Der Hauptinhalt der App, der den ganzen Platz einnimmt
                ft.Column(
                    [
                        # Header
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Container(width=50),
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
                                            bgcolor= ft.Colors.TRANSPARENT,
                                            items=[
                                                ft.PopupMenuItem(text="Liste Löschen", on_click=alles_loeschen),
                                                ft.PopupMenuItem(text="Über"),
                                            ]
                                        ),
                                        width=50,
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            padding=ft.padding.only(top=40, bottom=20),
                            alignment=ft.alignment.center,
                        ),
                        # Liste der Elemente
                        ft.ListView(
                            ref=einkaufsliste_ref,
                            expand=True,
                            spacing=10,
                            padding=20,
                        ),
                    ],
                    expand=True,
                    alignment=ft.MainAxisAlignment.START,
                ),
            ],
            expand=True,
        )
    )

    page.update()
    load_and_listen_data()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8550)), host="0.0.0.0")  
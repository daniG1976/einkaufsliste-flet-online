import flet as ft
import json
import os
import asyncio
import firebase_admin
from firebase_admin import credentials, db
import logging
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
        # Sicherstellen, dass alle Schlüssel vorhanden sind und Standardwerte haben
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
    page.title = "Unsere Gemeinsame Einkaufsliste"
    page.expand = True
    page.vertical_alignment = ft.CrossAxisAlignment.START
    page.bgcolor = ft.colors.TRANSPARENT
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(font_family="Roboto")
    page.extend_body_behind_appbar = True


    if page.window.width is None or page.window.width == 0:
        page.window.width = 400
    if page.window.height is None or page.window.height == 0:
        page.window.height = 800


    # --- Firebase-Initialisierung ---
    global db_ref
    db_ref = None
    global update_event
    update_event = threading.Event()

    try:
        firebase_credentials_json_string = os.getenv("FIREBASE_CREDENTIALS_JSON_CONTENT")
        if firebase_credentials_json_string:
            try:
                cred_data = json.loads(firebase_credentials_json_string)
                cred = credentials.Certificate(cred_data)
                print("DEBUG: Firebase-Anmeldeinformationen erfolgreich aus Umgebungsvariable geladen.")
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON-Parsing-Fehler bei Firebase-Anmeldeinformationen: {e}")
                raise
        else:
            try:
                cred = credentials.Certificate("firebase_credentials.json")
                print("DEBUG: Firebase-Anmeldeinformationen erfolgreich aus lokaler Datei geladen.")
            except FileNotFoundError:
                print("DEBUG: Lokale 'firebase_credentials.json' nicht gefunden und Umgebungsvariable nicht gesetzt.")
                raise

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://einkaufs-app-ae8e9-default-rtdb.europe-west1.firebasedatabase.app'
            })
            print("DEBUG: Firebase erfolgreich initialisiert.")
        else:
            print("DEBUG: Firebase bereits initialisiert (Hot Reload oder mehrfacher Aufruf).")
        db_ref = db.reference('/einkaufsliste')

    except Exception as e:
        error_msg = f"Ein Fehler bei der Firebase-Initialisierung ist aufgetreten: {e}"
        print(f"FEHLER: {error_msg}")
        page.add(ft.Text(f"Fehler beim Starten der App: {error_msg}", color=ft.colors.RED))
        page.update()
        return

    einkaufsliste_daten: list[ShoppingItem] = []
    # --- Referenzen für Flet-Widgets ---

    einkaufsliste_ref = ft.Ref[ft.ListView]()
    new_item_name_input = ft.Ref[ft.TextField]()
    numbers_field_ref = ft.Ref[ft.TextField]()
    weight_field_ref = ft.Ref[ft.TextField]()

    def save_data():
        """Speichert die aktuelle Einkaufsliste in Firebase."""
        if db_ref is None:
            print("FEHLER: Firebase db_ref ist nicht initialisiert. Daten können nicht gespeichert werden.")
            return
        try:
            data_to_save = [item.to_dict() for item in einkaufsliste_daten]
            db_ref.set(data_to_save)
            print("DEBUG: Daten erfolgreich in Firebase gespeichert.")
        except Exception as e:
            print(f"FEHLER: Fehler beim Speichern der Daten in Firebase: {e}")

    async def update_einkaufsliste_ui():
 
        logging.debug("update_einkaufsliste_ui wurde aufgerufen.")
        
        # Flet-Controls löschen und neu erstellen
        app_state.einkaufsliste_ref.current.controls.clear()
        
        with db_lock:
            docs = db.collection("einkaufsliste").stream()
            
        sorted_docs = sorted(docs, key=lambda doc: doc.id)

        # Erstelle die UI-Controls in einer Schleife
        new_controls = []
        for doc in sorted_docs:
            item_data = doc.to_dict()
            # WICHTIG: 'await' die asynchrone Funktion, um das Control-Objekt zu erhalten
            control = await create_list_item(item_data, doc.id)
            new_controls.append(control)

        app_state.einkaufsliste_ref.current.controls.extend(new_controls)

        logging.debug(f"Erstelle {len(new_controls)} neue UI-Controls für die ListView.")
        
        # WICHTIG: Asynchrones Update der Seite
        await app_state.einkaufsliste_ref.current.update_async()


    # --- NEU: load_and_listen_data Funktion START (inkl. Echtzeit-Listener) ---
    def firebase_listener_thread(page, update_event, db_ref):
        """
        Diese Funktion läuft in einem separaten Thread und startet den Firebase-Listener.
        Sie setzt das `update_event`, wenn Datenänderungen erkannt werden.
        """
        print("DEBUG: firebase_listener_thread gestartet.")

        def firebase_data_listener(event):
            """Der synchrone Callback-Handler für den Firebase-Listener."""
            print(f"DEBUG: Firebase-Datenänderung erkannt: {event.event_type}")
            new_data_from_firebase = []
            if event.data:
                if isinstance(event.data, dict):
                    try:
                        sorted_keys = sorted(event.data.keys(), key=lambda k: int(k))
                        for key in sorted_keys:
                            item_dict = event.data[key]
                            if item_dict:
                                new_data_from_firebase.append(ShoppingItem.from_dict(item_dict))
                    except (ValueError, AttributeError):
                        for item_dict in event.data.values():
                            if item_dict:
                                new_data_from_firebase.append(ShoppingItem.from_dict(item_dict))
                elif isinstance(event.data, list):
                    for item_dict in event.data:
                        if item_dict:
                            new_data_from_firebase.append(ShoppingItem.from_dict(item_dict))
            
            # Vergleiche und aktualisiere lokale Daten
            if set(einkaufsliste_daten) != set(new_data_from_firebase):
                einkaufsliste_daten.clear()
                einkaufsliste_daten.extend(new_data_from_firebase)
                print("DEBUG: update_event gesetzt.")
                update_event.set()
            else:
                print("DEBUG: Firebase-Update war identisch mit lokaler Liste, keine UI-Aktualisierung nötig.")

        db_ref.listen(firebase_data_listener)
        print("DEBUG: Firebase-Echtzeit-Listener erfolgreich gestartet.")
        
        # Der Thread muss offen bleiben, um auf Änderungen zu warten.

    async def start_app_logic(page, db_ref):
        """Lade initial Daten und starte den Listener."""
        print("DEBUG: start_app_logic wurde aufgerufen.")
        
        # 1. Globale Events für die Kommunikation zwischen den Threads
        update_event = threading.Event()
        stop_event = threading.Event()

        # 2. Initialen Datenabruf
        try:
            snapshot = db_ref.get()
            einkaufsliste_daten.clear()
            if snapshot:
                new_data_from_firebase = []
                if isinstance(snapshot, dict):
                    try:
                        sorted_keys = sorted(snapshot.keys(), key=lambda k: int(k))
                        for key in sorted_keys:
                            item_dict = snapshot[key]
                            if item_dict:
                                new_data_from_firebase.append(ShoppingItem.from_dict(item_dict))
                    except (ValueError, AttributeError):
                        for item_dict in snapshot.values():
                            if item_dict:
                                new_data_from_firebase.append(ShoppingItem.from_dict(item_dict))
                elif isinstance(snapshot, list):
                    for item_dict in snapshot:
                        if item_dict:
                            new_data_from_firebase.append(ShoppingItem.from_dict(item_dict))
                
                einkaufsliste_daten.extend(new_data_from_firebase)
                print(f"DEBUG: einkaufsliste_daten enthält jetzt {len(einkaufsliste_daten)} Items nach initialem Laden.")
            
            await update_einkaufsliste_ui()
        except Exception as e:
            print(f"FEHLER: Fehler beim initialen Laden der Daten: {e}")
            page.run_task(lambda: page.add(ft.Text(f"Fehler beim Laden der Einkaufsliste: {e}", color=ft.colors.RED)))
            return

        # 3. Listener-Thread starten
        listener_thread = threading.Thread(target=firebase_listener_thread, args=(page, update_event, db_ref), daemon=True)
        listener_thread.start()
        
        # 4. Endlosschleife im Flet-Thread, die auf das Event wartet
        while not stop_event.is_set():
            if update_event.wait(timeout=1.0):
                update_event.clear()
                await update_einkaufsliste_ui()
            if page.window_destroy_event_handler:
                stop_event.set()

        page.on_close = lambda e: stop_event.set()

    def show_duplicate_bottom_sheet(page: ft.Page, item_name: str):

        duplicate_sheet = ft.CupertinoBottomSheet(

            modal=True,

        )

        def close_sheet(e):

            duplicate_sheet.open = False

            page.update()


            def remove_sheet():

                page.overlay.remove(duplicate_sheet)

                page.update()


        duplicate_sheet.content = ft.Container(

            width=page.width,

            height=120,

            bgcolor="#FF5B8E",

            #border=ft.border.all(3, ft.colors.RED),

            content=ft.Column(

                [

                    ft.Text(

                        f'{item_name} ist bereits in der Einkaufsliste!',

                        weight=ft.FontWeight.BOLD,

                        size=18,

                        text_align=ft.TextAlign.CENTER,

                        color=ft.colors.WHITE,

                    ),

                    ft.ElevatedButton(

                        "OK",

                        color= "#EAD9C9",

                        bgcolor= "#213745",

                        on_click=close_sheet,

                        width=100,

                        height=40,

                    ),

                ],

                alignment=ft.MainAxisAlignment.CENTER,

                horizontal_alignment=ft.CrossAxisAlignment.CENTER,

            ),

            padding=20,

            border_radius=12,

        )


        # Sheet anzeigen

        page.overlay.append(duplicate_sheet)

        duplicate_sheet.open = True

        page.update()





    def scroll_to_control(e):

        """Scrollt die ListView zum Ende."""

        if einkaufsliste_ref.current:

            einkaufsliste_ref.current.scroll_to(offset=-1, duration=500)

            page.update()


    def handle_drag_accept(e: ft.ControlEvent):

        """Verarbeitet das Ablegen eines Elements beim Drag-and-Drop."""

        # e.src_id ist die ID des gezogenen Controls (Draggable)

        # e.control ist das Ziel-Control (DragTarget)

       

        dragged_draggable = page.get_control(e.src_id)

        dragged_item_data = dragged_draggable.data # Das ShoppingItem-Objekt des gezogenen Items


        target_item_data = e.control.data # Das ShoppingItem-Objekt des Ziel-Items (wo es abgelegt wurde)


        if dragged_item_data and target_item_data:

            try:

                old_index = einkaufsliste_daten.index(dragged_item_data)

                new_index = einkaufsliste_daten.index(target_item_data)

            except ValueError:

                print("FEHLER: Gezogenes oder Ziel-Element nicht in der Datenliste gefunden.")

                return


            # Elemente in der Liste verschieben

            item_to_move = einkaufsliste_daten.pop(old_index)

            einkaufsliste_daten.insert(new_index, item_to_move)

           

            save_data() # Änderungen in Firebase speichern

            page.run_task(update_einkaufsliste_ui) # UI neu zeichnen


    def add_favorite(e):

        """Fügt den ausgewählten Favoriten aus dem Picker in die Eingabefelder ein."""

        print(f"DEBUG: add_favorite wurde geklickt. cupertino_picker_widget.selected_index: {cupertino_picker_widget.selected_index}")

        selected_index = cupertino_picker_widget.selected_index

       

        if 0 <= selected_index < len(fruits):

            selected_value = fruits[selected_index]

            print(f"DEBUG: Favorit ausgewählt: {selected_value}")

           

            if new_item_name_input.current:

                print(f"DEBUG: Vor Zuweisung (new_item_name_input): '{new_item_name_input.current.value}'")

                new_item_name_input.current.value = selected_value

                new_item_name_input.current.update()

                print(f"DEBUG: Nach Zuweisung (new_item_name_input): '{new_item_name_input.current.value}'")

            else:

                print("FEHLER: new_item_name_input.current ist None in add_favorite.")

           

            if numbers_field_ref.current:

                print(f"DEBUG: Vor Zuweisung (numbers_field_ref): '{numbers_field_ref.current.value}'")

                numbers_field_ref.current.value = "1"

                numbers_field_ref.current.update()

                print(f"DEBUG: Nach Zuweisung (numbers_field_ref): '{numbers_field_ref.current.value}'")

            else:

                print("FEHLER: numbers_field_ref.current ist None in add_favorite.")

           

            if weight_field_ref.current:

                print(f"DEBUG: Vor Zuweisung (weight_field_ref): '{weight_field_ref.current.value}'")

                weight_field_ref.current.value = "Stück"

                weight_field_ref.current.update()

                print(f"DEBUG: Nach Zuweisung (weight_field_ref): '{weight_field_ref.current.value}'")

            else:

                print("FEHLER: weight_field_ref.current ist None in add_favorite.")

           

            if dialog_offer_button:

                dialog_offer_button.icon_color = ft.colors.WHITE # Reset Angebots-Status

                dialog_offer_button.update()

           

            page.update() # Wichtig, um UI-Änderungen zu pushen

        else:

            print(f"DEBUG: Ungültiger selected_index im Picker: {selected_index} oder fruits ist leer.")



    def handle_picker_change(e):

        """Wird aufgerufen, wenn sich der Wert im CupertinoPicker ändert."""

        # Der Wert wird direkt über selected_index aus den fruits-Liste ausgelesen.

        # Es ist nicht nötig, hier einen Text anzuzeigen, da der Wert direkt in das

        # Textfeld übertragen wird, wenn der Favoriten-Button geklickt wird.

        selected_index = int(e.control.selected_index)

        if 0 <= selected_index < len(fruits):

            selected_value = fruits[selected_index]

            print(f"DEBUG: Picker geändert zu: {selected_value}")

        else:

            print(f"DEBUG: Picker geändert zu ungültigem Index: {selected_index}")

        # page.update() # Hier nicht unbedingt nötig, da keine direkten UI-Änderungen am Dialog stattfinden,

                      # die sofort sichtbar sein müssen.



    async def create_shopping_card(item: ShoppingItem):
        """Erstellt eine Flet Card für ein einzelnes ShoppingItem."""
        offer_icon_color = ft.colors.RED if item.is_offer else ft.colors.WHITE

        def handle_dismiss(e: ft.DismissibleDismissEvent):
            # Finden des Index des gelöschten/erledigten Elements
            try:
                idx_to_remove = einkaufsliste_daten.index(item)
            except ValueError:
                # Loggen, aber keinen Fehler werfen, falls das Item aus irgendeinem Grund nicht gefunden wird
                print(f"FEHLER: Item {item.name} nicht in lokaler Liste gefunden beim Dismiss.")
                return

            if e.data == "end_to_start": # Löschen (Swipe von rechts nach links)
                print(f"DEBUG: Lösche Item: {item.name}")
                einkaufsliste_daten.pop(idx_to_remove) # Entferne es aus der Datenliste
                save_data() # Speichert die Änderung in Firebase
                # KORREKTUR: UI wird sofort aktualisiert
                einkaufsliste_ref.current.controls.remove(e.control) # Entferne das UI-Control direkt
                einkaufsliste_ref.current.update()
                page.update()
            elif e.data == "start_to_end": # Erledigt (Swipe von links nach rechts)
                print(f"DEBUG: Markiere Item als erledigt: {item.name}")
                einkaufsliste_daten.pop(idx_to_remove) # Entfernt es aus der Liste
                save_data() # Speichert die Änderung in Firebase
                # KORREKTUR: UI wird sofort aktualisiert
                einkaufsliste_ref.current.controls.remove(e.control) # Entferne das UI-Control direkt
                einkaufsliste_ref.current.update()
                page.update()


                page.run_task(update_einkaufsliste_ui) # UI nach Löschen/Erledigen aktualisieren


        dismissible_card = ft.Dismissible(

            content=ft.Card(

                content=ft.Container(

                    border_radius=ft.border_radius.all(10),

                    gradient=ft.LinearGradient(

                        begin=ft.alignment.center_left,

                        end=ft.alignment.center_right,

                        colors=["#213745", "#FF5B8E"],

                    ),

                    padding=10,

                    content=ft.Row(

                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,

                        vertical_alignment=ft.CrossAxisAlignment.CENTER,

                        controls=[

                            ft.Icon(

                                name=ft.icons.FONT_DOWNLOAD, # Hier evtl. ein besser passendes Icon wählen

                                color=offer_icon_color,

                            ),

                            ft.Text(

                                value=f"   {item.amount} {item.unit} {item.name}",

                                color=ft.colors.WHITE,

                                size=24,

                                expand=True,

                                text_align=ft.TextAlign.START,

                            ),

                            ft.IconButton(

                                icon=ft.icons.DRAG_INDICATOR, # Icon für Drag-and-Drop

                                icon_color=ft.colors.WHITE,

                                on_click=None, # Kein Klick-Handler, da es nur ein visueller Indikator ist

                            )

                        ]

                    )

                ),

                elevation=5,

            ),

            dismiss_direction=ft.DismissDirection.HORIZONTAL,

            background=ft.Container( # Hintergrund beim Swipe nach rechts (Erledigt)

                alignment=ft.alignment.center_left,

                border_radius=ft.border_radius.all(10),

                bgcolor=ft.colors.GREEN_700,

                content=ft.Icon(ft.icons.CHECK, color=ft.colors.WHITE, size=40),

                padding=ft.padding.only(left=20)

            ),

            secondary_background=ft.Container( # Hintergrund beim Swipe nach links (Löschen)

                alignment=ft.alignment.center_right,

                border_radius=ft.border_radius.all(10),

                bgcolor=ft.colors.RED_700,

                content=ft.Icon(ft.icons.DELETE, color=ft.colors.WHITE, size=40),

                padding=ft.padding.only(right=20)

            ),

            on_dismiss=handle_dismiss,

            dismiss_thresholds={ # Schwellenwerte für das Auslösen des Dismiss

                ft.DismissDirection.START_TO_END: 0.2, # 20% Swipe von links nach rechts

                ft.DismissDirection.END_TO_START: 0.2, # 20% Swipe von rechts nach links

            },

        )


        return ft.DragTarget(

            group="shopping_items",

            content=ft.Draggable(

                group="shopping_items",

                content=dismissible_card, # Das ist die normale Darstellung der Karte

                # Die Darstellung, wenn das Element gezogen wird

                content_when_dragging=ft.Container(

                    width=dismissible_card.content.width, # Versucht, die Breite der Karte zu übernehmen

                    height=dismissible_card.content.height, # Versucht, die Höhe der Karte zu übernehmen

                    bgcolor=ft.colors.with_opacity(0.5, ft.colors.BLUE_GREY_900), # Halbtransparenter Hintergrund

                    border_radius=ft.border_radius.all(10),

                    alignment=ft.alignment.center,

                    content=ft.Text("Verschiebe...", color=ft.colors.WHITE54, size=16), # Ein Text für Debugging/Feedback

                ),

                data=item, # Wichtig: Das tatsächliche ShoppingItem-Objekt für Drag-and-Drop Logik

            ),

            on_accept=handle_drag_accept,

            data=item, # Wichtig: Das ShoppingItem-Objekt des Ziels für Drag-and-Drop Logik

        )
        
# --- Dialog- und Eingabefelder Definitionen ---

    # on_change Handler für Textfelder, um Wertänderungen zu beobachten

    def text1_on_change(e):

        print(f"DEBUG: Artikel-Eingabe geändert: '{e.control.value}'")

       

    def numbers_field_on_change(e):

        print(f"DEBUG: Anzahl-Eingabe geändert: '{e.control.value}'")

       

    def weight_field_on_change(e):

        print(f"DEBUG: Einheit-Eingabe geändert: '{e.control.value}'")


    text1 = ft.TextField(

        value="",

        label="Artikel eingeben",

        border_color=ft.colors.WHITE,

        label_style=ft.TextStyle(color="EAD9C9"),

        text_style=ft.TextStyle(color="EAD9C9"),

        cursor_color="EAD9C9",

        border_radius=ft.border_radius.all(8),

        on_focus=scroll_to_control,

        ref=new_item_name_input,

        on_change=text1_on_change,

        autofocus=True # Setzt den Fokus automatisch, wenn der Dialog geöffnet wird

    )


    numbers_field = ft.TextField(

        value="",

        label="Anzahl eingeben",

        border_color=ft.colors.WHITE,

        label_style=ft.TextStyle(color="EAD9C9"),

        text_style=ft.TextStyle(color="EAD9C9"),

        cursor_color="EAD9C9",

        border_radius=ft.border_radius.all(8),

        on_focus=scroll_to_control,

        ref=numbers_field_ref,

        on_change=numbers_field_on_change,

        keyboard_type=ft.KeyboardType.NUMBER # Tastaturtyp für Zahlen

    )


    weight_field = ft.TextField(

        value="",

        label="Einheit eingeben (z.B. kg, Stück)",

        border_color=ft.colors.WHITE,

        label_style=ft.TextStyle(color="EAD9C9"),

        text_style=ft.TextStyle(color="EAD9C9"),

        cursor_color="EAD9C9",

        border_radius=ft.border_radius.all(8),

        on_focus=scroll_to_control,

        ref=weight_field_ref,

        on_change=weight_field_on_change,

    )


    fruits = [

        "Äpfel", "Bananen", "Milch", "Quark", "Wurst", "Käse", "Joghurt",

        "O-Saft", "Nudeln", "Nutella", "Kaffee", "Brot", "Eier", "Wasser",

        "Zwiebeln", "Kartoffeln", "Tomaten", "Gurken"

    ]

    # Sortiere die Favoriten alphabetisch für bessere Übersichtlichkeit

    fruits.sort()


    cupertino_picker_widget = ft.CupertinoPicker(

        selected_index=0, # Startet immer beim ersten Favoriten

        magnification=1.22,

        squeeze=1.2,

        use_magnifier=True,

        on_change=handle_picker_change,

        controls=[ft.Text(value=f, color="EAD9C9") for f in fruits],

        height=200,

        item_extent=40,

    )


    dialog_offer_button = ft.IconButton(icon=ft.icons.FONT_DOWNLOAD, icon_color=ft.colors.WHITE, icon_size=30)


    def toggle_dialog_offer_button(e):

        """Schaltet den Angebots-Status-Icon im Dialog um."""

        if dialog_offer_button.icon_color == ft.colors.WHITE:

            dialog_offer_button.icon_color = ft.colors.RED

        else:

            dialog_offer_button.icon_color = ft.colors.WHITE

        dialog_offer_button.update()

    dialog_offer_button.on_click = toggle_dialog_offer_button


    def dialog_add_clicked(e):

        """Verarbeitet den Klick auf den "Hinzufügen"-Button im Dialog."""

        print("DEBUG: dialog_add_clicked wurde aufgerufen.")

       

        # Den Wert aus dem TextField 'new_item_name_input' bevorzugen.

        # Wenn es leer ist, den Wert vom ersten Favoriten nehmen (aus dem Picker)

        item_name = new_item_name_input.current.value.strip() if new_item_name_input.current and new_item_name_input.current.value else fruits[cupertino_picker_widget.selected_index] if fruits else ""

       

        item_amount = numbers_field_ref.current.value.strip() if numbers_field_ref.current and numbers_field_ref.current.value else "1"

        item_unit = weight_field_ref.current.value.strip() if weight_field_ref.current and weight_field_ref.current.value else "Stück"


        print(f"DEBUG: Werte vor dem Hinzufügen: Name='{item_name}', Anzahl='{item_amount}', Einheit='{item_unit}'")


        if not item_name:

            print("FEHLER: Artikelname ist leer. Kann kein Item hinzufügen.")

            # Optional: Hier könnte eine kleine Fehlermeldung im Dialog angezeigt werden

            return


        # Duplikatsprüfung (case-insensitive)

        if any(item.name.lower() == item_name.lower() for item in einkaufsliste_daten):

            # Felder zurücksetzen

            new_item_name_input.current.value = ""

            numbers_field_ref.current.value = ""

            weight_field_ref.current.value = ""

            dialog_offer_button.icon_color = ft.colors.WHITE


            new_item_name_input.current.update()

            numbers_field_ref.current.update()

            weight_field_ref.current.update()

            dialog_offer_button.update()


            # ZUERST: Dialog schließen und Seite updaten

            page.close(dlg_modal)

            page.update()


            # DANN: Bottom Sheet zeigen

            show_duplicate_bottom_sheet(page, item_name)

            return

       

        is_offer = dialog_offer_button.icon_color == ft.colors.RED


        new_item = ShoppingItem(

            name=item_name,

            amount=item_amount,

            unit=item_unit,

            is_offer=is_offer

        )


        einkaufsliste_daten.append(new_item)

        save_data() # Speichert Daten in Firebase

        page.run_task(update_einkaufsliste_ui) # Aktualisiert die UI


        page.close(dlg_modal)

        # Wichtig: Felder nach erfolgreichem Hinzufügen zurücksetzen und aktualisieren

        new_item_name_input.current.value = ""

        numbers_field_ref.current.value = ""

        weight_field_ref.current.value = ""

        dialog_offer_button.icon_color = ft.colors.WHITE

        # Diese Updates sind entscheidend, damit die Felder beim nächsten Öffnen des Dialogs leer sind

        new_item_name_input.current.update()

        numbers_field_ref.current.update()

        weight_field_ref.current.update()

        dialog_offer_button.update()

        page.update() # Die Seite muss aktualisiert werden, um die Änderungen nach dem Schließen des Dialogs anzuzeigen


    dialog_add_button = ft.IconButton(icon=ft.icons.ADD, icon_color=ft.colors.WHITE, icon_size=30, on_click=dialog_add_clicked)


    dialog_gradient = ft.LinearGradient(

        begin=ft.alignment.top_center,

        end=ft.alignment.bottom_center,

        colors=["#213745", "#FF5B8E"],

    )


    dialog_content_container = ft.Container(

        content=ft.Column(

            controls=[

                ft.Row( # Row für den Favoriten-Picker

                    controls=[

                        ft.IconButton(icon=ft.icons.FAVORITE, icon_color=ft.colors.WHITE, icon_size=30, on_click=add_favorite),

                        ft.Container(

                            content=cupertino_picker_widget,

                            width=250,

                            height=200 # Sicherstellen, dass der Picker genug Platz hat

                        ),

                    ],

                    alignment=ft.MainAxisAlignment.START,

                    vertical_alignment=ft.CrossAxisAlignment.CENTER,

                ),

                ft.Row( # Row für den Artikelnamen

                    controls=[

                        ft.IconButton(icon=ft.icons.NEW_LABEL, icon_color=ft.colors.WHITE, icon_size=30, on_click=None),

                        ft.Container(

                            content=text1,

                            width=250,

                        )

                    ],

                    alignment=ft.MainAxisAlignment.START,

                    vertical_alignment=ft.CrossAxisAlignment.CENTER,

                ),

                ft.Row( # Row für die Anzahl

                    controls=[

                        ft.IconButton(icon=ft.icons.NUMBERS, icon_color=ft.colors.WHITE, icon_size=30, on_click=None),

                        ft.Container(

                            content=numbers_field,

                            width=250,

                        )

                    ],

                    alignment=ft.MainAxisAlignment.START,

                    vertical_alignment=ft.CrossAxisAlignment.CENTER,

                ),

                ft.Row( # Row für das Gewicht/Einheit

                    controls=[

                        ft.IconButton(icon=ft.icons.SCALE, icon_color=ft.colors.WHITE, icon_size=30, on_click=None),

                        ft.Container(

                            content=weight_field,

                            width=250,

                        )

                    ],

                    alignment=ft.MainAxisAlignment.START,

                    vertical_alignment=ft.CrossAxisAlignment.CENTER,

                ),

            ],

            spacing=25,

            horizontal_alignment=ft.CrossAxisAlignment.CENTER,

        ),

        width=350,

        padding=20,

        border_radius=ft.border_radius.all(10),

    )


    dlg_modal = ft.AlertDialog(

        bgcolor=ft.colors.TRANSPARENT,

        content=ft.Container(

            content=ft.Column(

                [

                    ft.Text("Wir brauchen:", color=(0xFFEAD9C9), size=30, weight=ft.FontWeight.BOLD),

                    dialog_content_container,

                    ft.Row(

                        controls=[dialog_offer_button, dialog_add_button],

                        alignment=ft.MainAxisAlignment.END,

                    ),

                ],

                spacing=10,

                horizontal_alignment=ft.CrossAxisAlignment.CENTER,

            ),

            padding=12,

            gradient=dialog_gradient,

            border_radius=ft.border_radius.all(10),

        ),

        shape=ft.RoundedRectangleBorder(radius=ft.border_radius.all(10)),

    )


    def fab_clicked(e):

        """Wird aufgerufen, wenn der Floating Action Button geklickt wird, um den Dialog zu öffnen."""

        print("DEBUG: fab_clicked wurde aufgerufen.")

        # Felder beim Öffnen des Dialogs zurücksetzen, um eine saubere Eingabe zu ermöglichen

        new_item_name_input.current.value = ""

        numbers_field_ref.current.value = ""

        weight_field_ref.current.value = ""

       

        # Setze den Favoriten-Picker auf den ersten Wert zurück (Index 0)

        cupertino_picker_widget.selected_index = 0

       

        dialog_offer_button.icon_color = ft.colors.WHITE # Angebots-Button zurücksetzen


        # Jetzt den Dialog öffnen. Alle Controls sind jetzt "on the page"

        page.open(dlg_modal)

       

        # Erst nach page.open() können Controls im Dialog aktualisiert werden!

        new_item_name_input.current.update()

        numbers_field_ref.current.update()

        weight_field_ref.current.update()

        cupertino_picker_widget.update()

        dialog_offer_button.update()

       

        page.update() # Die Seite selbst muss aktualisiert werden, um den geöffneten Dialog zu zeigen


    # --- Haupt-Layout des Bildschirms mit ft.Stack ---

    main_layout_stack = ft.Stack(

        expand=True,

        controls=[

            ft.Container( # Dieser Container ist der Hintergrund

                expand=True,

                gradient=ft.LinearGradient(

                    begin=ft.alignment.top_center,

                    end=ft.alignment.bottom_center,

                    colors=[

                        "#EAD9C9", # Startfarbe (heller Beige/Rosa)

                        "#FF5B8E", # Endfarbe (dunkleres Pink)

                    ],

                ),

            ),

            ft.Column( # Das ist der Inhalt, der ÜBER dem Hintergrund liegen soll

                [

                    # Header-Bereich

                    ft.Container(

                        content=ft.Row(

                            [

                                ft.Container(width=50), # Placeholder für Symmetrie

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

                                    ft.PopupMenuButton( # Menü-Button oben rechts

                                        icon_color=ft.colors.WHITE,

                                        items=[

                                            ft.PopupMenuItem(text="Einstellungen"), # Beispiel-Menüpunkt

                                            ft.PopupMenuItem(text="Über"), # Beispiel-Menüpunkt

                                        ]

                                    ),

                                    width=50, # Platz für den Menü-Button

                                ),

                            ],

                            vertical_alignment=ft.CrossAxisAlignment.CENTER,

                        ),

                        padding=ft.padding.only(top=40, bottom=20),

                        alignment=ft.alignment.center,

                        width=page.width, # Stellen Sie sicher, dass der Header die volle Breite hat

                    ),


                    # Liste der Items

                    ft.Column(
                        [
                            ft.ListView(
                                ref=einkaufsliste_ref,
                                expand=True,
                                spacing=10,
                                padding=10,
                                auto_scroll=True, # Automatisches Scrollen zum Ende
                            ),
                        ],
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                    ),
                ],
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),

        ]

    )


    # --- Seiten-Setup und Start-Logik ---

    page.controls = [main_layout_stack]


    page.floating_action_button = ft.FloatingActionButton(

        content=ft.Icon(name=ft.icons.ADD, color="#EAD9C9"),

        on_click=fab_clicked,

        bgcolor="#213745",

        shape=ft.CircleBorder(),

    )

    page.floating_action_button_location = ft.FloatingActionButtonLocation.CENTER_FLOAT

    page.on_ready = lambda e: page.run_task(start_app_logic, page, db_ref)

    page.update()

if __name__ == "__main__":
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        port=int(os.environ.get("PORT", 8550)),
        host="127.0.0.1"
    )  
import os
import flet as ft

class ShoppingItem:
    def __init__(self, name: str, amount: str, unit: str, is_offer: bool):
        self.name = name
        self.amount = amount
        self.unit = unit
        self.is_offer = is_offer # True, wenn Angebot (rote Farbe), False, wenn normal (weiße Farbe)

def main(page: ft.Page):
    page.title = "Unsere Gemeinsame Einkaufsliste"
    page.expand = True
    page.vertical_alignment = ft.CrossAxisAlignment.START # Elemente oben starten
    page.bgcolor = ft.Colors.TRANSPARENT
    page.padding = 0 # Wichtig: Padding der Seite auf 0 setzen, damit der Gradient den ganzen Bildschirm füllt
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO # Aktiviert Scrollen bei Bedarf, falls der Inhalt größer wird
    page.theme = ft.Theme(font_family="Roboto")
    page.extend_body_behind_appbar = True 

    # --- NEU: Liste zum Speichern der ShoppingItem-Objekte ---
    einkaufsliste_daten: list[ShoppingItem] = []

    # --- NEU: Referenz für die ListView, die die Karten anzeigen wird ---
    einkaufsliste_ref = ft.Ref[ft.ListView]()

    def fab_clicked(e):
            page.open(dlg_modal)
            page.update()


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
        border_radius=ft.border_radius.all(8)
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
        border_radius=ft.border_radius.all(8)
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
        border_radius=ft.border_radius.all(8)
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
    
    def add_favorite(e):
        if favoriten_anzeige.current and favoriten_anzeige.current.value:
            text1.value = favoriten_anzeige.current.value # Setze den Wert des Textfeldes
            text1.update()
            
    def create_shopping_card(item: ShoppingItem):
        offer_icon_color = ft.Colors.RED if item.is_offer else ft.Colors.WHITE

        def handle_dismiss(e: ft.DismissibleDismissEvent):
            # Element aus der visuellen Liste (ListView) entfernen
            if einkaufsliste_ref.current:
                einkaufsliste_ref.current.controls.remove(e.control)
            
            # Element aus der Datenliste (einkaufsliste_daten) entfernen
            # e.control.data ist hier das ShoppingItem vom Draggable
            if e.control.data in einkaufsliste_daten:
                einkaufsliste_daten.remove(e.control.data)
            
            page.update()

        dismissible_card = ft.Dismissible(
            content=ft.Card(
                content=ft.Container(
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
                                value=f"{item.name} ({item.amount} {item.unit})",
                                color=ft.Colors.WHITE,
                                size=16,
                                expand=True,
                                text_align=ft.TextAlign.START,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DRAG_INDICATOR,
                                icon_color=ft.Colors.WHITE,
                            )
                        ]
                    )
                ),
                color="#FF5B8E",
                elevation=5,
            ),
            dismiss_direction=ft.DismissDirection.HORIZONTAL, # Kann nach links oder rechts gewischt werden
            background=ft.Container( # Hintergrund beim Wischen von links nach rechts (z.B. "erledigt")
                alignment=ft.alignment.center_left,
                bgcolor=ft.Colors.GREEN_700,
                content=ft.Icon(ft.Icons.CHECK, color=ft.Colors.WHITE, size=40),
                padding=ft.padding.only(left=20)
            ),
            secondary_background=ft.Container( # Hintergrund beim Wischen von rechts nach links (z.B. "löschen")
                alignment=ft.alignment.center_right,
                bgcolor=ft.Colors.RED_700,
                content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=40),
                padding=ft.padding.only(right=20)
            ),
            on_dismiss=handle_dismiss, # Wird direkt aufgerufen, sobald der Schwellenwert erreicht ist
            # on_confirm_dismiss wurde hier entfernt
            dismiss_thresholds={
                ft.DismissDirection.START_TO_END: 0.2, # Von links nach rechts wischen
                ft.DismissDirection.END_TO_START: 0.2, # Von rechts nach links wischen
            },
        )

        draggable_card = ft.Draggable(
            group="shopping_items",
            content=dismissible_card,
            content_when_dragging=ft.Container(
                width=dismissible_card.content.width,
                height=dismissible_card.content.height,
                bgcolor="#FF5B8E",
                border_radius=ft.border_radius.all(10),
                content=ft.Text(f"Ziehe {item.name}", color=ft.Colors.WHITE70),
                alignment=ft.alignment.center
            ),
            data=item, # Übergib das ShoppingItem-Objekt beim Ziehen, wichtig für handle_dismiss
        )
        return draggable_card

    dialog_offer_button = ft.IconButton(icon=ft.Icons.FONT_DOWNLOAD, icon_color=ft.Colors.WHITE, icon_size=30)
    # Beachte: on_click für dialog_offer_button wird weiter unten im dialog_add_clicked gesetzt
    # oder du verwendest eine Ref, um seinen Status abzufragen.
    # Hier eine separate Funktion für den Offer-Button im Dialog
    def toggle_dialog_offer_button(e):
        if dialog_offer_button.icon_color == ft.Colors.WHITE:
            dialog_offer_button.icon_color = ft.Colors.RED
        else:
            dialog_offer_button.icon_color = ft.Colors.WHITE
        dialog_offer_button.update()
    dialog_offer_button.on_click = toggle_dialog_offer_button # Zuweisung der Toggle-Funktion


    def dialog_add_clicked(e):
        # 1. Werte aus Textfeldern und Picker abrufen
        item_name = text1.value if text1.value else favoriten_anzeige.current.value
        item_amount = numbers_field.value
        item_unit = weight_field.value
        is_offer = dialog_offer_button.icon_color == ft.Colors.RED # Status des Offer-Buttons

        # 2. Neues ShoppingItem erstellen
        new_item = ShoppingItem(
            name=item_name,
            amount=item_amount,
            unit=item_unit,
            is_offer=is_offer
        )

        # 3. Item zur Datenliste hinzufügen
        einkaufsliste_daten.append(new_item)

        # 4. Visuelle Karte erstellen
        item_card = create_shopping_card(new_item)

        # 5. Karte zur ListView hinzufügen und aktualisieren
        if einkaufsliste_ref.current:
            einkaufsliste_ref.current.controls.append(item_card)
            einkaufsliste_ref.current.update()

        # 6. Dialog schließen und Felder zurücksetzen
        dlg_modal.open = False
        text1.value = ""
        numbers_field.value = ""
        weight_field.value = ""
        dialog_offer_button.icon_color = ft.Colors.WHITE # Offer-Status zurücksetzen
        dialog_offer_button.update() # Wichtig, damit der Button-Zustand zurückgesetzt wird
        page.update() # Seite aktualisieren, um den geschlossenen Dialog und die neue Karte zu zeigen

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
                ft.Row(
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(icon=ft.Icons.FAVORITE, icon_color=ft.Colors.WHITE, icon_size=30, on_click=add_favorite),
                        ft.Container(
                            content=cupertino_picker_widget,
                            expand=True,
                        ),
                        ft.Text(ref=favoriten_anzeige, value=fruits[0], color=ft.Colors.WHITE, size=16, visible=False),
                    ],
                    expand=True
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(icon=ft.Icons.NEW_LABEL, icon_color=ft.Colors.WHITE, icon_size=30, on_click=()),
                        text1,
                    ],
                    expand=True
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(icon=ft.Icons.NUMBERS, icon_color=ft.Colors.WHITE, icon_size=30, on_click=()),
                        numbers_field,
                    ],
                    expand=True
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(icon=ft.Icons.SCALE, icon_color=ft.Colors.WHITE, icon_size=30, on_click=()),
                        weight_field,
                    ],
                    expand=True
                )
            ],
            spacing=25
        ),
        width=350,
        padding=20,
        #bgcolor=ft.Colors.BLUE_400,
        border_radius=ft.border_radius.all(10),
    )
    
  
    gradient_dialog_container = ft.Container(
        content=ft.Column( # Nutze eine Column, um Titel, den Haupt-Content und die Aktionen zu stapeln
        [
        
            ft.Text("Wir brauchen:", color=(0xFFEAD9C9), size=30, weight=ft.FontWeight.BOLD),
            #ft.Divider(height=10, color=ft.Colors.WHITE24), # Optional: Ein Trenner nach dem Titel
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
        elevation=3,
        shadow_color="#213745",
)


    gradient_background_container = ft.Container(
        expand=True,
        width=page.width,
        height=page.height,
        content=ft.Column(
            [
                ft.Row(
                    [
        ft.Container(width=50),  # linker Platzhalter
        ft.Container(
            expand=True,
            content=ft.Text(
                "Meine Einkaufsliste",
                size=28,
                weight=ft.FontWeight.BOLD,
                color="#213745",
                text_align=ft.TextAlign.CENTER,
            ),
        ),
        ft.Container(
            ft.PopupMenuButton(
                icon_color = "#213745",
                items=[
                    ft.PopupMenuItem(text="Item 1"),
                    ft.PopupMenuItem(text="Item 2"),
                ]
            ),
            width=50,  # rechter Bereich
        ),
    ],
    width=page.width,
    vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
                
        ft.ListView(
                ref=einkaufsliste_ref, # Referenz zur ListView
                expand=True, # Wichtig, damit die Liste den verfügbaren Platz einnimmt
                spacing=10, # Abstand zwischen den Karten
                padding=10,
                # controls werden dynamisch hinzugefügt
            ),
       
    ],

        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20 # Abstand zwischen den Elementen in der Spalte
        ),
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_center, # Startpunkt des Verlaufs (oben mittig)
            end=ft.alignment.bottom_center, # Endpunkt des Verlaufs (unten mittig
            # Deine gewählten Farben
            colors=[
                "#EAD9C9", # Ein tiefes Lila
                "#FF5B8E", # Ein dunkleres Lila
            ],
        ),
    )

    page.add(gradient_background_container)


ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8550)), host="0.0.0.0") 
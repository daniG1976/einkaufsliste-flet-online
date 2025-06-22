import os # Neu: Import für den Zugriff auf Umgebungsvariablen
import flet as ft


def main(page: ft.Page):
    
    page.title = "Unsere Gemeinsame Einkaufsliste"
    page.expand = True
    page.vertical_alignment = ft.CrossAxisAlignment.START # Elemente oben starten
    #page.horizontal_alignment = ft.CrossAxisAlignment.CENTER # Elemente horizontal zentrieren
    page.bgcolor = ft.Colors.TRANSPARENT 
    page.padding = 0 # Wichtig: Padding der Seite auf 0 setzen, damit der Gradient den ganzen Bildschirm füllt
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO # Aktiviert Scrollen bei Bedarf, falls der Inhalt größer wird
    page.theme = ft.Theme(font_family="Roboto") 


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
                ft.OutlinedButton(
                    style=ft.ButtonStyle(
                        shape=ft.CircleBorder(),  # Runde Form
                        color=ft.Colors.BLUE_300,  # Textfarbe
                        side=ft.BorderSide(  # Rand mit Hex-Farbe
                            width=2,
                            color=ft.Colors.WHITE,
                        ),
                        icon_size=24,
                    ),
                    icon=ft.Icons.ADD,
                    on_click=(),  # Verweis auf die Funktion (jetzt korrekt)
                    height=50,  # Initiale Höhe
                    width=50,  # Initiale Breite
                ),
            ],
            # WICHTIG: Die Spalte muss sich ebenfalls ausdehnen,
            # um den gesamten vertikalen Raum im Container zu füllen.
            expand=True, 
            #alignment=ft.MainAxisAlignment.CENTER, # Inhalt in der Mitte der Spalte zentrieren
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Inhalt horizontal zentrieren
            spacing=20 # Abstand zwischen den Elementen in der Spalte
        ),
        # Gradient-Definition für den Hintergrund des Containers
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_center, # Startpunkt des Verlaufs (oben mittig)
            end=ft.alignment.bottom_center, # Endpunkt des Verlaufs (unten mittig)
            # Deine gewählten Farben
            colors=[
                "#EAD9C9", # Ein tiefes Lila
                "#FF5B8E", # Ein dunkleres Lila

            ], 
        ),
    )
    
    # Füge den Haupt-Container zur Seite hinzu
    page.add(gradient_background_container)
        


    
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8550)), host="0.0.0.0")



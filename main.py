import os # Neu: Import für den Zugriff auf Umgebungsvariablen
import flet as ft
import threading

def main(page: ft.Page):
    
    page.title = "Unsere Gemeinsame Einkaufsliste"
    page.vertical_alignment = ft.CrossAxisAlignment.START # Elemente oben starten
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER # Elemente horizontal zentrieren
    page.bgcolor = ft.Colors.BLUE_GREY_900
    page.padding = 20
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    
    page.add(
        ft.Text(
            "Flet App Läuft! (Workaround) - Alles Driss Du Ei", # Text anpassen
            color=ft.Colors.WHITE,
            size=24,
            weight=ft.FontWeight.BOLD
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
        on_click=(),  # Verweise auf die Funktion
        height=50,  # Initiale Höhe
        width=50,   # Initiale Breite
   
    ),
        

    )
    
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", 8550)), host="0.0.0.0")

# iphone: http://192.168.178.63:8550/
import flet as ft

def main(page: ft.Page):
    page.title = "Flet Diagnose Test"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.bgcolor = ft.colors.BLUE_GREY_900 # Ein ganz dunkler, einfacher Hintergrund
    page.padding = 0
    page.expand = True

    page.add(
        ft.Container(
            content=ft.Text(
                "Hallo Flet-Welt!",
                size=40,
                weight=ft.FontWeight.BOLD,
                color=ft.colors.WHITE
            ),
            width=300, # Feste Breite
            height=200, # Feste Höhe
            alignment=ft.alignment.center,
            bgcolor=ft.colors.GREEN_ACCENT_700, # Knallgrüner Container
            border_radius=15,
            padding=20,
        )
    )
    page.update() # Sicherstellen, dass das Update aufgerufen wird

# Probier zuerst den Webbrowser-Modus
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550, host="0.0.0.0")

# Wenn der Webbrowser-Modus nicht geht, probier dann den Desktop-Modus (Kommentiere die Zeile oben aus)
# ft.app(target=main)
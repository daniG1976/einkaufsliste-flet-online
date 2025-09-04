import flet as ft
import flet_webview as ftwv

def zweiteseite_view(page: ft.Page):
    prospekt_url = "https://www.hit.de/maerkte/sankt-augustin/prospekte/wochenprospekt?seite=1"

    web_view_control = ftwv.WebView(
        url=prospekt_url,
        expand=True,
    )
    
    def on_back_click(e):
        page.go("/")

    return ft.View(
        route="/zweiteseite",
        # Setze einen transparenten Hintergrund für die View
        bgcolor="#FF5B8E",
        padding=0,
        controls=[
            # Der Haupt-Container, der die gesamte Seite umhüllt
            ft.Container(
                expand=True,
                margin=ft.margin.all(10),  # Abstand von den Rändern des Bildschirms
                padding=ft.padding.all(15), # Innerer Abstand für den Inhalt
                gradient=ft.LinearGradient(
                                begin=ft.alignment.top_center,
                                end=ft.alignment.bottom_center,
                                colors=["#EAD9C9", "#FF5B8E"],
                            ),
                border_radius=ft.border_radius.all(14),
                content=ft.Column(
                    expand=True,
                    controls=[
                        # Die AppBar ist jetzt Teil des Containers
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK,
                                    icon_color="#213745",
                                    on_click=on_back_click
                                ),
                                ft.Text(
                                    "Aktueller HIT Prospekt",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                    color="#213745"
                                )
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        # Der WebView befindet sich jetzt in der Spalte des Containers
                        web_view_control
                    ]
                )
            )
        ]
    )
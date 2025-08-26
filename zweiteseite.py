import flet as ft
import flet_webview as ftwv

def zweiteseite_view(page: ft.Page):
    #prospekt_url = "https://www.hit.de/maerkte/sankt-augustin/prospekte/wochenprospekt?seite=1"

    #web_view_control = ftwv.WebView(
        #url=prospekt_url,
        #expand=True,
    #)
    
    def on_back_click(e):
        page.go("/")

    # Gib die View mit dem vereinfachten Layout zurück
    return ft.View(
        route="/zweiteseite",
        # Setze eine Hintergrundfarbe, um den Stil beizubehalten
        bgcolor=ft.Colors.with_opacity(0.6, "#FF5B8E"), 
        controls=[
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                icon_color="#213745",
                                on_click=on_back_click
                            ),
                            ft.Text(
                                "Aktueller Prospekt",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color="#213745"
                            )
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    #ft.Divider(),
                    #web_view_control,
                ],
                expand=True,
            )
        ]
    )
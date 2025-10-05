import flet as ft
import asyncio
import platform

def main(page: ft.Page):
    page.title = "JS & iOS Test"
    
    result_text = ft.Text(value="Noch keine Rückmeldung", size=20)
    
    async def handle_js_message(e):
        data = e.data
        if isinstance(data, dict):
            if data.get("type") == "speech_error":
                result_text.value = f"JS-Message: {data.get('message')}"
                page.update()
            elif data.get("type") == "speech_result":
                result_text.value = f"Speech Result: {data.get('text')}"
                page.update()
    
    page.on_message = handle_js_message
    
    async def test_button_clicked(e):
        js_code = """
        // Nachricht direkt beim Start
        window.parent.postMessage({ type: "speech_error", message: "JS gestartet" }, "*");
        
        (async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                window.parent.postMessage({ type: "speech_error", message: "getUserMedia erfolgreich" }, "*");
                
                const mediaRecorder = new MediaRecorder(stream);
                let chunks = [];
                mediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
                
                mediaRecorder.onstop = async () => {
                    window.parent.postMessage({ type: "speech_error", message: "Aufnahme gestoppt" }, "*");
                };
                
                mediaRecorder.start();
                setTimeout(() => mediaRecorder.stop(), 3000);
            } catch (err) {
                window.parent.postMessage({ type: "speech_error", message: "Fehler: " + err.message }, "*");
            }
        })();
        """
        await page.eval_js(js_code)
    
    test_button = ft.ElevatedButton("JS Test starten", on_click=lambda e: asyncio.create_task(test_button_clicked(e)))

    
    page.add(ft.Column([test_button, result_text]))

ft.app(target=main, view=ft.AppView.WEB_BROWSER)

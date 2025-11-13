import flet as ft
from voice_assistant import VoiceAssistant
import threading
def main(page: ft.Page):
    # configuracion de la ventana
    page.title = "🎤 Asistente de Voz"
    page.window.width = 600
    page.window.height = 750
    page.theme_mode = ft.ThemeMode.DARK
    
    # inicializa el asistente
    assistant = VoiceAssistant()
    
    # commponentes de la interfaz del usuario
    title = ft.Text(
        "🎤 Asistente de Voz",
        size=24,
        weight=ft.FontWeight.BOLD,
        color=ft.colors.BLUE_400
    )
    
    status_text = ft.Text(
        "🟢 Listo para recibir comandos",
        size=14,
        color=ft.colors.GREEN_400
    )
    
    log_output = ft.Text(
        value="",
        size=12,
        color=ft.colors.WHITE,
        font_family="Courier New"
    )
    
    log_container = ft.Container(
        content=ft.Column([log_output], scroll=ft.ScrollMode.AUTO),
        height=400,
        bgcolor=ft.colors.BLACK26,
        border_radius=10,
        padding=10
    )
    
    def stop_assistant_click(e):
        assistant.stop_assistant(log_output, page)
        status_text.value = "🔴 Asistente detenido - Di 'iniciar' para reactivar"
        status_text.color = ft.colors.RED_400
        start_button.disabled = False
        stop_button.disabled = True
        page.update()
    
    def start_assistant_click(e):
        assistant.start_assistant(log_output, page)
        status_text.value = "🟢 Listo para recibir comandos"
        status_text.color = ft.colors.GREEN_400
        start_button.disabled = True
        stop_button.disabled = False
        page.update()
    
    start_button = ft.ElevatedButton(
        "🟢 Iniciar Asistente",
        on_click=start_assistant_click,
        bgcolor=ft.colors.GREEN_600,
        color=ft.colors.WHITE,
        disabled=True
    )
    
    stop_button = ft.ElevatedButton(
        "🛑 Detener Asistente",
        on_click=stop_assistant_click,
        bgcolor=ft.colors.RED_600,
        color=ft.colors.WHITE
    )
    
    # texto de instrucciones 
    instructions = ft.Text(
        "Comandos de voz: 'iniciar' para activar, 'parar' para detener\n"
        "También puedes usar los botones de la interfaz",
        size=11,
        color=ft.colors.GREY_400,
        text_align=ft.TextAlign.CENTER
    )
    
    # estructura
    page.add(
        ft.Column([
            title,
            status_text,
            instructions,
            ft.Divider(),
            log_container,
            ft.Row([start_button, stop_button], alignment=ft.MainAxisAlignment.CENTER)
        ], spacing=15, expand=True)
    )
    
    # mensaje de bienvenida
    assistant.log_message("🚀 Asistente iniciado", log_output)
    assistant.speak("Hola! Soy tu asistente de voz. Di 'comandos' para conocer las opciones disponibles. el primer comando talvez necesite ser dicho dos veces.")
    
    # inicializacion del asistente
    assistant.assistant_thread = threading.Thread(
        target=assistant.assistant_loop,
        args=(log_output, page),
        daemon=True
    )
    assistant.assistant_thread.start()

if __name__ == "__main__":
    ft.app(target=main)
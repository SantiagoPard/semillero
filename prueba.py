import flet as ft
import speech_recognition as sr
import pyttsx3
import os
import shutil
import threading
import time
import sys
import subprocess
from queue import Queue
import json
from datetime import datetime

class VoiceAssistant:
    def __init__(self):
        self.assistant_active = True
        self.setup_speech_recognition()
        self.voice_queue = Queue()
        self.log = []
        self.tts_engine = None
        self.tts_lock = threading.Lock()  # Agregar lock para thread safety
        self.setup_voice_worker()
        
        # Run diagnosis after setup
        time.sleep(0.5)  # Give time for everything to initialize
        self.diagnose_voice_system()
    
    def diagnose_voice_system(self):
        """Diagnose voice system status"""
        print("🔍 Ejecutando diagnóstico del sistema de voz...")
        
        # Check TTS engine
        if self.tts_engine:
            print("✅ Motor TTS: Funcionando")
        else:
            print("❌ Motor TTS: No disponible")
        
        # Check microphone
        try:
            with self.mic as source:
                print("🎤 Probando micrófono...")
                # Brief test
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("✅ Micrófono: Funcionando")
        except Exception as e:
            print(f"❌ Micrófono: Error - {e}")
        
        # Check voice thread
        if self.voice_thread.is_alive():
            print("✅ Hilo de voz: Activo")
        else:
            print("❌ Hilo de voz: Inactivo")
        
        # Check voice queue
        print(f"📊 Cola de voz: {self.voice_queue.qsize()} mensajes pendientes")
        
        print("🔍 Diagnóstico completado")
    
    def setup_voice_worker(self):
        """Setup voice worker thread with TTS initialization inside thread"""
        print("🎤 Iniciando hilo de voz...")
        self.voice_thread = threading.Thread(target=self.voice_worker, daemon=True)
        self.voice_thread.start()
        
        # Verify thread is running
        time.sleep(0.1)
        if self.voice_thread.is_alive():
            print("✅ Hilo de voz iniciado correctamente")
        else:
            print("❌ Error: Hilo de voz no se inició")
        
        # Test the voice queue with a simple message
        self.speak("Prueba de sistema de voz")
        time.sleep(1)  # Give time for the test message to process
    
    def setup_tts_in_thread(self):
        """Initialize TTS engine inside the worker thread"""
        try:
            self.tts_engine = pyttsx3.init()
            voices = self.tts_engine.getProperty('voices')
            
            print("🔊 Configurando motor TTS en hilo de trabajo...")
            print(f"Voces disponibles: {len(voices) if voices else 0}")
            
            # Try to find Spanish voice
            spanish_voice_found = False
            if voices:
                for i, voice in enumerate(voices):
                    print(f"Voz {i}: {voice.name} - {voice.id}")
                    if 'spanish' in voice.name.lower() or 'es_' in voice.id or 'mexico' in voice.name.lower() or 'spain' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        spanish_voice_found = True
                        print(f"✅ Voz en español seleccionada: {voice.name}")
                        break
            
            if not spanish_voice_found:
                print("⚠️ No se encontró voz en español, usando voz predeterminada")
            
            # Set speech rate and volume
            self.tts_engine.setProperty('rate', 150)  # Slower speech
            self.tts_engine.setProperty('volume', 1.0)  # Maximum volume
            
            # Test TTS
            print("🔊 Probando TTS...")
            self.tts_engine.say("Sistema de voz inicializado")
            self.tts_engine.runAndWait()
            print("✅ TTS funcionando correctamente")
            
        except Exception as e:
            print(f"❌ Error inicializando TTS: {e}")
            self.tts_engine = None
    
    def setup_speech_recognition(self):
        """Initialize speech recognition"""
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        
        # Adjust for ambient noise
        with self.mic as source:
            print("Calibrando micrófono...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
    
    def voice_worker(self):
        """Process voice messages in sequence - TTS initialization happens here"""
        print("🎤 Hilo de voz iniciado - Worker funcionando")
        
        # Initialize TTS engine in this thread
        self.setup_tts_in_thread()
        
        try:
            while True:
                print("🔄 Esperando mensaje en cola...")
                message_data = self.voice_queue.get(timeout=30)  # 30 second timeout
                
                if message_data is None:
                    print("🛑 Señal de parada recibida - Deteniendo hilo de voz")
                    break
                
                # Handle different message types
                if isinstance(message_data, dict):
                    text = message_data.get('text', '')
                    priority = message_data.get('priority', False)
                else:
                    text = str(message_data)
                    priority = False
                
                if self.tts_engine is None:
                    print("❌ Motor TTS no disponible, saltando mensaje")
                    self.voice_queue.task_done()
                    continue
                
                print(f"🔊 Procesando mensaje: '{text}'" + (" [PRIORITARIO]" if priority else ""))
                
                try:
                    with self.tts_lock:  # Usar lock para thread safety
                        self.tts_engine.say(text)
                        self.tts_engine.runAndWait()
                    print(f"✅ Mensaje reproducido: '{text}'")
                except Exception as tts_error:
                    print(f"❌ Error reproduciendo mensaje: {tts_error}")
                
                self.voice_queue.task_done()
                
                # Pausa más corta para mensajes prioritarios
                time.sleep(0.1 if priority else 0.2)
                
        except Exception as e:
            print(f"❌ Error crítico en voice_worker: {e}")
            import traceback
            traceback.print_exc()
        
        print("🏁 Hilo de voz terminado")
    
    def speak(self, text, priority=False):
        """Add message to voice queue with validation and priority support"""
        if not text.strip():
            return
            
        message_data = {
            'text': text,
            'priority': priority,
            'timestamp': time.time()
        }
        
        print(f"🔊 Agregando a cola de voz: {text}" + (" [PRIORITARIO]" if priority else ""))
        
        if priority:
            # Para mensajes prioritarios, limpiar la cola primero
            temp_queue = Queue()
            try:
                while not self.voice_queue.empty():
                    temp_queue.put(self.voice_queue.get_nowait())
            except:
                pass
            
            # Agregar mensaje prioritario
            self.voice_queue.put(message_data)
            
            # Reagregar mensajes no prioritarios
            try:
                while not temp_queue.empty():
                    self.voice_queue.put(temp_queue.get_nowait())
            except:
                pass
        else:
            self.voice_queue.put(message_data)
        
        # Debug: Check queue size
        print(f"📊 Cola de voz tiene {self.voice_queue.qsize()} mensajes")
    
    def speak_priority(self, text):
        """Speak with priority (clears queue first)"""
        self.speak(text, priority=True)
    
    def log_message(self, message, output_widget=None):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log.append(formatted_message)
        
        if output_widget:
            output_widget.value = "\n".join(self.log[-20:])  # Show last 20 messages
    
    def open_file(self, filepath):
        """Open file with system default application"""
        try:
            if sys.platform.startswith("win"):
                os.startfile(filepath)
            elif sys.platform.startswith("darwin"):
                subprocess.call(["open", filepath])
            else:
                subprocess.call(["xdg-open", filepath])
            return True
        except Exception as e:
            print(f"Error opening file: {e}")
            return False
    
    def get_desktop_files(self):
        """Get list of files on desktop"""
        try:
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            files = os.listdir(desktop)
            return files, desktop
        except Exception as e:
            print(f"Error accessing desktop: {e}")
            return [], ""
    
    def find_file(self, target, files):
        """Find file by partial name match"""
        files_lower = {f.lower(): f for f in files}
        
        # Exact match first
        if target in files_lower:
            return files_lower[target]
        
        # Partial match
        for low, orig in files_lower.items():
            if target in low:
                return orig
        
        return None
    
    def recognize_speech(self):
        """Recognize speech with improved error handling"""
        with self.mic as source:
            print("🎤 Escuchando...")
            try:
                # Listen with timeout and phrase limit
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                print("🔊 Audio capturado")
                
                # Recognize speech
                command = self.recognizer.recognize_google(audio, language="es-ES").lower().strip()
                print(f"✅ Comando reconocido: {command}")
                
                # Confirm command recognition with voice (priority)
                self.speak_priority(f"Comando reconocido: {command}")
                return command
                
            except sr.WaitTimeoutError:
                print("⏰ Timeout esperando audio")
                return ""
            except sr.UnknownValueError:
                print("❌ No se entendió el audio")
                self.speak("No entendí lo que dijiste")
                return ""
            except sr.RequestError as e:
                print(f"❌ Error del servicio: {e}")
                self.speak("Error con el servicio de reconocimiento")
                return ""
            except Exception as e:
                print(f"❌ Error inesperado: {e}")
                self.speak("Ha ocurrido un error")
                return ""
    
    def execute_command(self, cmd, output_widget, page):
        """Execute voice command"""
        self.log_message(f"Comando: {cmd}", output_widget)
        
        files, desktop = self.get_desktop_files()
        if not desktop:
            self.log_message("❌ No se puede acceder al escritorio", output_widget)
            self.speak("No puedo acceder al escritorio")
            return
        
        # Command processing
        if "abrir" in cmd:
            self.handle_open_command(cmd, files, desktop, output_widget)
        elif "eliminar" in cmd or "borrar" in cmd:
            self.handle_delete_command(cmd, files, desktop, output_widget)
        elif "mover" in cmd:
            self.handle_move_command(cmd, files, desktop, output_widget)
        elif "renombrar" in cmd:
            self.handle_rename_command(cmd, files, desktop, output_widget)
        elif any(phrase in cmd for phrase in ["listar", "mostrar", "qué archivos"]):
            self.handle_list_command(files, output_widget)
        elif "comandos" in cmd or "ayuda" in cmd:
            self.handle_help_command(output_widget)
        elif "crear carpeta" in cmd:
            self.handle_create_folder_command(cmd, desktop, output_widget)
        else:
            self.log_message("❓ Comando no reconocido", output_widget)
            self.speak("No reconozco ese comando. Di 'comandos' para ver opciones disponibles.")
        
        page.update()
    
    def handle_open_command(self, cmd, files, desktop, output_widget):
        """Handle file opening command"""
        target = cmd.replace("abrir", "").strip()
        found_file = self.find_file(target, files)
        
        if found_file:
            filepath = os.path.join(desktop, found_file)
            if self.open_file(filepath):
                self.log_message(f"✅ Abriendo: {found_file}", output_widget)
                self.speak(f"Abriendo {found_file}")
            else:
                self.log_message(f"❌ Error abriendo: {found_file}", output_widget)
                self.speak("Error al abrir el archivo")
        else:
            self.log_message("❌ Archivo no encontrado", output_widget)
            self.speak("Archivo no encontrado")
    
    def handle_delete_command(self, cmd, files, desktop, output_widget):
        """Handle file deletion command"""
        target = cmd.replace("eliminar", "").replace("borrar", "").strip()
        found_file = self.find_file(target, files)
        
        if found_file:
            try:
                os.remove(os.path.join(desktop, found_file))
                self.log_message(f"🗑️ Eliminado: {found_file}", output_widget)
                self.speak(f"{found_file} eliminado")
            except Exception as e:
                self.log_message(f"❌ Error eliminando: {e}", output_widget)
                self.speak("Error al eliminar el archivo")
        else:
            self.log_message("❌ Archivo no encontrado", output_widget)
            self.speak("Archivo no encontrado")
    
    def handle_move_command(self, cmd, files, desktop, output_widget):
        """Handle file moving command"""
        if " a " not in cmd:
            self.log_message("❓ Formato: mover <archivo> a <carpeta>", output_widget)
            self.speak("Debes decir: mover archivo a carpeta")
            return
        
        parts = cmd.split(" a ")
        target = parts[0].replace("mover", "").strip()
        dest_folder = parts[1].strip()
        
        found_file = self.find_file(target, files)
        if found_file:
            dest_path = os.path.join(desktop, dest_folder)
            os.makedirs(dest_path, exist_ok=True)
            
            try:
                shutil.move(os.path.join(desktop, found_file), dest_path)
                self.log_message(f"📁 {found_file} movido a {dest_folder}", output_widget)
                self.speak(f"{found_file} movido a {dest_folder}")
            except Exception as e:
                self.log_message(f"❌ Error moviendo: {e}", output_widget)
                self.speak("Error al mover el archivo")
        else:
            self.log_message("❌ Archivo no encontrado", output_widget)
            self.speak("Archivo no encontrado")
    
    def handle_rename_command(self, cmd, files, desktop, output_widget):
        """Handle file renaming command"""
        if " como " not in cmd:
            self.log_message("❓ Formato: renombrar <archivo> como <nuevo_nombre>", output_widget)
            self.speak("Debes decir: renombrar archivo como nuevo nombre")
            return
        
        parts = cmd.split(" como ")
        target = parts[0].replace("renombrar", "").strip()
        new_name = parts[1].strip()
        
        found_file = self.find_file(target, files)
        if found_file:
            try:
                old_path = os.path.join(desktop, found_file)
                new_path = os.path.join(desktop, new_name)
                os.rename(old_path, new_path)
                
                self.log_message(f"✏️ {found_file} renombrado a {new_name}", output_widget)
                self.speak(f"{found_file} renombrado a {new_name}")
            except Exception as e:
                self.log_message(f"❌ Error renombrando: {e}", output_widget)
                self.speak("Error al renombrar el archivo")
        else:
            self.log_message("❌ Archivo no encontrado", output_widget)
            self.speak("Archivo no encontrado")
    
    def handle_list_command(self, files, output_widget):
        """Handle file listing command"""
        files, desktop = self.get_desktop_files()
        
        if files:
            # Classify files and folders
            items_info = []
            for item in files:
                item_path = os.path.join(desktop, item)
                if os.path.isdir(item_path):
                    items_info.append((item, "carpeta"))
                else:
                    items_info.append((item, "archivo"))
            
            total_count = len(items_info)
            folder_count = sum(1 for _, tipo in items_info if tipo == "carpeta")
            file_count = sum(1 for _, tipo in items_info if tipo == "archivo")
            
            self.log_message(f"📋 Elementos en escritorio ({total_count}):", output_widget)
            self.log_message(f"   📁 Carpetas: {folder_count}", output_widget)
            self.log_message(f"   📄 Archivos: {file_count}", output_widget)
            
            # Speak count with classification
            if folder_count > 0 and file_count > 0:
                count_message = f"Encontré {total_count} elementos: {folder_count} carpetas y {file_count} archivos"
            elif folder_count > 0:
                count_message = f"Encontré {folder_count} carpetas"
            else:
                count_message = f"Encontré {file_count} archivos"
            
            self.speak(count_message)
            
            # Speak all items individually with type
            self.speak("Los elementos son:")
            
            for i, (item, tipo) in enumerate(items_info, 1):
                # Clean filename for speech
                item_limpio = item.replace('.txt', ' punto txt').replace('.pdf', ' punto pdf').replace('.jpg', ' punto jpg').replace('.png', ' punto png').replace('.docx', ' punto docx').replace('.lnk', ' enlace').replace('.url', ' url')
                
                if tipo == "carpeta":
                    message = f"{i}: carpeta {item_limpio}"
                    icon = "📁"
                else:
                    message = f"{i}: archivo {item_limpio}"
                    icon = "📄"
                
                self.speak(message)
                self.log_message(f"  {i}. {icon} {item} ({tipo})", output_widget)
        else:
            self.log_message("📭 No hay elementos en el escritorio", output_widget)
            no_files_msg = "No hay elementos en el escritorio"
            self.speak(no_files_msg)
    
    def handle_help_command(self, output_widget):
        """Handle help command"""
        commands = [
            "📖 Comandos disponibles:",
            "• Abrir [archivo] - Abre un archivo",
            "• Eliminar [archivo] - Elimina un archivo", 
            "• Mover [archivo] a [carpeta] - Mueve archivo a carpeta",
            "• Renombrar [archivo] como [nuevo] - Cambia nombre",
            "• Listar archivos - Muestra todos los archivos",
            "• Crear carpeta [nombre] - Crea nueva carpeta",
            "• Parar - Detiene el asistente",
            "• Comandos - Muestra esta ayuda"
        ]
        
        for cmd in commands:
            self.log_message(cmd, output_widget)
        
        self.speak("Los comandos disponibles son: abrir, eliminar, mover, renombrar, listar archivos, crear carpeta, y parar")
    
    def handle_create_folder_command(self, cmd, desktop, output_widget):
        """Handle folder creation command"""
        folder_name = cmd.replace("crear carpeta", "").strip()
        if folder_name:
            try:
                folder_path = os.path.join(desktop, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                self.log_message(f"📁 Carpeta creada: {folder_name}", output_widget)
                self.speak(f"Carpeta {folder_name} creada")
            except Exception as e:
                self.log_message(f"❌ Error creando carpeta: {e}", output_widget)
                self.speak("Error al crear la carpeta")
        else:
            self.log_message("❓ Especifica el nombre de la carpeta", output_widget)
            self.speak("Debes especificar el nombre de la carpeta")
    
    def assistant_loop(self, output_widget, page):
        """Main assistant loop"""
        print("🚀 Asistente iniciado")
        
        while self.assistant_active:
            command = self.recognize_speech()
            
            if not command:
                continue
            
            if any(word in command for word in ["parar", "detener", "terminar"]):
                self.assistant_active = False
                self.log_message("🛑 Asistente detenido", output_widget)
                self.speak("Deteniéndome. ¡Hasta luego!")
                page.update()
                break
            
            self.execute_command(command, output_widget, page)
            time.sleep(0.5)


def main(page: ft.Page):
    # Page configuration
    page.title = "🎤 Asistente de Voz Inteligente"
    page.window.width = 600
    page.window.height = 700
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    
    # Initialize assistant
    assistant = VoiceAssistant()
    
    # UI Components
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
    
    # Container for log
    log_container = ft.Container(
        content=ft.Column([log_output], scroll=ft.ScrollMode.AUTO),
        height=400,
        bgcolor=ft.colors.BLACK26,
        border_radius=10,
        padding=10
    )
    
    # Control buttons
    def stop_assistant(e):
        assistant.assistant_active = False
        status_text.value = "🔴 Asistente detenido"
        status_text.color = ft.colors.RED_400
        page.update()
    
    stop_button = ft.ElevatedButton(
        "🛑 Detener Asistente",
        on_click=stop_assistant,
        bgcolor=ft.colors.RED_600,
        color=ft.colors.WHITE
    )
    
    # Layout
    page.add(
        ft.Column([
            title,
            status_text,
            ft.Divider(),
            log_container,
            ft.Row([stop_button], alignment=ft.MainAxisAlignment.CENTER)
        ], spacing=20, expand=True)
    )
    
    # Welcome message
    assistant.log_message("🚀 Asistente iniciado", log_output)
    
    welcome_msg = (
        "¡Hola! Soy tu asistente de voz inteligente. "
        "Estoy listo para ayudarte con la gestión de archivos en tu escritorio. "
        "Di 'comandos' para conocer todas las opciones disponibles."
    )
    
    assistant.speak(welcome_msg)
    
    # Start assistant loop
    threading.Thread(
        target=assistant.assistant_loop,
        args=(log_output, page),
        daemon=True
    ).start()

if __name__ == "__main__":
    ft.app(target=main)
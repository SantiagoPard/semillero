import flet as ft
import speech_recognition as sr
import pyttsx3
import os
import shutil
import threading
import time
from queue import Queue
from datetime import datetime


class VoiceAssistant:
    def __init__(self):
        self.assistant_active = True
        self.is_speaking = False
        self.speaking_lock = threading.Lock()
        self.setup_speech_recognition() 
        self.voice_queue = Queue()
        self.log = []
        self.tts_engine = None
        self.current_directory = os.path.join(os.path.expanduser('~'), 'Desktop')  # Directorio actual
        self.assistant_thread = None
        self.setup_voice_worker()
    
    # inicializacion hilo voz sintetica
    def setup_voice_worker(self):
        self.voice_thread = threading.Thread(target=self.voice_worker, daemon=True)
        self.voice_thread.start()
        time.sleep(0.1)
        self.speak("Sistema de voz inicializado")
    
    # inicializacion motor TTS y adicion al hilo voice_worker
    def setup_tts_in_thread(self): 
        try:    
            self.tts_engine = pyttsx3.init()
            voices = self.tts_engine.getProperty('voices')
            
            # encontrar voz en español
            if voices:
                for voice in voices:
                    if any(term in voice.name.lower() for term in ['spanish', 'es_', 'mexico', 'spain']):
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            #configuracion de las propiedades
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 1.0)
            
        except Exception as e:
            print(f"Error inicializando TTS: {e}")
            self.tts_engine = None
    
    #Parámetros para speechRecognition
    def setup_speech_recognition(self):
        
        self.recognizer = sr.Recognizer()
        self.mic_lock = threading.Lock()  # Lock para el micrófono
        
        # Configurar parámetros del reconocedor
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.operation_timeout = None
    
    #procesa la cola de los mensajes
    def voice_worker(self):
        self.setup_tts_in_thread()
        
        try:
            while True:
                message_data = self.voice_queue.get(timeout=20)
                
                if message_data is None:
                    break
                
                text = message_data.get('text', '') if isinstance(message_data, dict) else str(message_data)
                
                if self.tts_engine and text:
                    try:
                        with self.speaking_lock:
                            self.is_speaking = True
                        
                        self.tts_engine.say(text)
                        self.tts_engine.runAndWait()
                        time.sleep(0.2)
                        
                    except Exception as e:
                        print(f"Error reproduciendo mensaje: {e}")
                    finally:
                        with self.speaking_lock:
                            self.is_speaking = False
                
                self.voice_queue.task_done()
                
        except Exception as e:
            print(f"Error en voice_worker: {e}")
        finally:
            with self.speaking_lock:
                self.is_speaking = False
    
    #añade un mensaje a la cola
    def speak(self, text): 
        print("jola")
       # if text.strip():
       #    self.voice_queue.put({'text': text, 'timestamp': time.time()})
    
    #espera a que el asistente pare de hablar
    def wait_for_speech_to_finish(self):
        while True:
            with self.speaking_lock:
                if not self.is_speaking and self.voice_queue.empty():
                    break
            time.sleep(0.1)
        time.sleep(0.3)

    #añadir mensaje de log 
    def log_message(self, message, output_widget=None):
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log.append(formatted_message)
        
        if output_widget:
            output_widget.value = "\n".join(self.log[-20:])
            
    #obtener los archivos del directorio en el que se esta ubicado
    def get_current_files(self):
        try:
            files = os.listdir(self.current_directory) #obtiene los archivos y carpetas del directorio actual
            return files, self.current_directory #devuelve los archivos encontrados y el directorio de donde los extrajo
        except Exception:
            return [], ""   #controla el error que se genera en caso de no encontrar nada

    #funcion para el reconocimiento de comandos
    def recognize_speech(self):
        
        self.wait_for_speech_to_finish() # evita que capte la voz sintetica como comando

        try:
            mic = sr.Microphone() # Crear nuevo micrófono para cada uso (evita problemas de estados)
                
            with mic as source:
                # Ajustar para ruido ambiente solo ocasionalmente
                if not hasattr(self, '_ambient_adjusted') or not self._ambient_adjusted:
                    try:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        self._ambient_adjusted = True
                    except Exception:
                        # Si falla el ajuste, continuar sin él
                        pass
                
                # Escuchar con timeout
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
            # Reconocer fuera del contexto del micrófono
            command = self.recognizer.recognize_google(audio, language="es-ES").lower().strip()
            return command
                
        except (sr.WaitTimeoutError, sr.UnknownValueError): # maneja error si no se habla
            return "sin comando"
        except sr.RequestError as e:# maneja error en caso de que no se entienda el comando
            print(f"Error con el servicio de reconocimiento: {e}")
            self._reset_ambient_flag()
            return ""
        except (OSError, AttributeError) as e: #maneja error en caso de que sea algo de hardware
            print(f"Error de audio: {e}")
            self._reset_ambient_flag()
            return ""
        except Exception as e: #maneja errores genericos
            print(f"Error inesperado en reconocimiento: {e}")
            self._reset_ambient_flag()
            return ""
        finally:
            # Limpiar referencias
                mic = None
    
    #resetear el ajuste de la flag del sonido ambiente
    def _reset_ambient_flag(self):
        try:
            self._ambient_adjusted = False
        except:
            pass
    
    
    #met para ejecutar los comandos
    def execute_command(self, cmd, output_widget, page):
        
        self.log_message(f"Comando: {cmd}", output_widget) # agrega el comando a los logs
        
        files, current_dir = self.get_current_files() # obtiene los archivos del directorio actual 
        if not current_dir:
            self.speak("No puedo acceder al directorio actual")
            return
        
        
        # procesa los comandos detectando la palabra clave y ejecutando el metodo correspondiente
        
        if "sin comando" in cmd:
            self.speak("por favor , dime un comando")
        elif "eliminar" in cmd or "borrar" in cmd:
            self.handle_delete_command(cmd, files, current_dir, output_widget)
        elif "mover" in cmd:
            self.handle_move_command(cmd, files, current_dir, output_widget)
        elif "renombrar" in cmd:
            self.handle_rename_command(cmd, files, current_dir, output_widget)
        elif any(phrase in cmd for phrase in ["listar", "mostrar", "qué archivos"]):
            self.handle_list_command(files, current_dir, output_widget)
        elif "entrar a" in cmd or "ir a" in cmd or "entrar" in cmd:
            self.handle_enter_folder_command(cmd, files, output_widget)
        elif "volver" in cmd or "salir" in cmd or "regresar" in cmd:
            self.handle_go_back_command(output_widget)
        elif "dónde estoy" in cmd or "ubicación" in cmd:
            self.handle_location_command(output_widget)
        elif "comandos" in cmd or "ayuda" in cmd:
            self.handle_help_command(output_widget)
        elif "crear carpeta" in cmd:
            self.handle_create_folder_command(cmd, current_dir, output_widget)
        elif "crear archivo" in cmd:
            # Solo permitir el formato específico con tipo
            if any(type_word in cmd for type_word in ["archivo de texto" , "texto", "word", "excel", "powerpoint", "power point", "presentación", "presentacion"]) and "llamado" in cmd:
                self.handle_create_file_with_type_command(cmd, current_dir, output_widget)
            else:
                self.speak("Usa el formato: crear archivo de texto llamado nombre, crear archivo word llamado nombre, crear archivo excel llamado nombre, o crear archivo powerpoint llamado nombre")
            
        else:
            self.speak("No reconozco ese comando. Di 'comandos' para ver opciones disponibles.")
        
        page.update()
    
    #funcion para eliminar un archivo
    def handle_delete_command(self, cmd, files, current_dir, output_widget):
        target = cmd.replace("eliminar", "").replace("borrar", "").strip()# quita la palabra del comando y deja solo el nombre del archivo
        found_file = self.find_file(target, files) 
        
        if found_file:
            try:
                filepath = os.path.join(current_dir, found_file)
                if os.path.isdir(filepath): # distingen entre archivo y carpeta
                    shutil.rmtree(filepath)
                    self.log_message(f"🗑️ Carpeta eliminada: {found_file}", output_widget) # pone en logs la carpeta eliminada
                    self.speak(f"Carpeta {found_file} eliminada") #el asistente avisa la carpeta que se elimino
                else:
                    os.remove(filepath)
                    self.log_message(f"🗑️ Archivo eliminado: {found_file}", output_widget) # pone en logs el archivo eliminada
                    self.speak(f"Archivo {found_file} eliminado") #el asistente avisa que archivo se elimino
            except Exception as e:
                self.log_message(f"❌ Error eliminando: {e}", output_widget)
                self.speak("Error al eliminar")
        else:
            self.speak("Archivo no encontrado")

    def find_file(self, target, files):

        target = target.lower().strip()
        files_lower = {f.lower(): f for f in files}
        
        for low, orig in files_lower.items(): # Recorre cada archivo
            if target in low:  # verifica si el nombre está contenido en el nombre del archivo
                return orig 
        
        return None
    
    # funcion para mover un archivo
    def handle_move_command(self, cmd, files, current_dir, output_widget):
    
        if " a " not in cmd: # si a no se encuentra en el mensaje 
            self.speak("Debes decir: mover archivo a carpeta")
            return
        
        parts = cmd.split(" a ") 
        target = parts[0].replace("mover", "").strip() # quita la palabra mover y elimina espacios
        dest_folder = parts[1].strip() # elimina espacios de la ruta destino
        
        found_file = self.find_file(target, files) #fucnion auxiliar para encontrar el archivo
        if found_file:
            dest_path = os.path.join(current_dir, dest_folder)
            os.makedirs(dest_path, exist_ok=True)
            
            try:
                shutil.move(os.path.join(current_dir, found_file), dest_path) # recibe como parametro la direccion en la que esta y la direccion a la que se quiere mover el archivo
                self.log_message(f"📁 {found_file} movido a {dest_folder}", output_widget) # accion agregada al log
                self.speak(f"{found_file} movido a {dest_folder}") # output de voz por parte de el asistente
            except Exception as e:
                self.log_message(f"❌ Error moviendo: {e}", output_widget)
                self.speak("Error al mover el archivo")
        else:
            self.speak("Archivo no encontrado")
 
    #funcion para renombrar archivo   
    def handle_rename_command(self, cmd, files, current_dir, output_widget):
 
        if " como " not in cmd:
            self.speak("Debes decir: renombrar archivo como nuevo nombre")
            return
        
        parts = cmd.split(" como ")
        target = parts[0].replace("renombrar", "").strip() # quita la palabra renombrar y elimina espacios
        new_name = parts[1].strip() # elimina espacios del nuevo nombre
        
        found_file = self.find_file(target, files) # busca si el archivo existe
        if found_file:
            try:
                old_path = os.path.join(current_dir, found_file)
                
               
                file_extension = os.path.splitext(found_file) # Obtener la extensión del archivo original
                
          
                if file_extension:      # Si el archivo original tiene extensión, se conserva
                    new_name_lower = new_name.lower() 
                    extension_lower = file_extension.lower()
                    
                    if not new_name_lower.endswith(extension_lower):
                        final_new_name = new_name + file_extension # Agrega la extensión original al nuevo nombre
                        self.log_message(f"🔧 Conservando extensión: {file_extension}", output_widget)
                    else:
                      
                        final_new_name = new_name  # El usuario ya incluyó la extensión
                else:
                    final_new_name = new_name  # El archivo original no tiene extensión
                
                new_path = os.path.join(current_dir, final_new_name)
                
              
                if os.path.exists(new_path) and new_path != old_path:  # Verificar si ya existe un archivo con el nuevo nombre
                    self.log_message(f"❌ Ya existe un archivo llamado: {final_new_name}", output_widget)
                    self.speak(f"Ya existe un archivo llamado {final_new_name}")
                    return
                
                os.rename(old_path, new_path)
                
                self.log_message(f"✏️ {found_file} renombrado a {final_new_name}", output_widget)
                self.speak(f"{found_file} renombrado a {final_new_name}")
                
            except Exception as e:
                self.log_message(f"❌ Error renombrando: {e}", output_widget)
                self.speak("Error al renombrar el archivo")
        else:
            self.speak("Archivo no encontrado")
            
    # funcion para crear un archivo (txt,word.excel, powerpoint)
    def handle_create_file_with_type_command(self, cmd, current_dir, output_widget):
        
        
        # Mapeo de tipos permitidos únicamente
        type_extensions = {
            'archivo de texto': '.txt',
            'texto': '.txt',
            'word': '.docx',
            'excel': '.xlsx',
            'powerpoint': '.pptx',
            'power point': '.pptx',
            'presentación': '.pptx',
            'presentacion': '.pptx'
        }
        
        # Buscar el tipo en el comando
        file_type = None
        file_name = None
        
        for type_name, ext in type_extensions.items():
            if type_name in cmd.lower(): # verifica si el comando trae la clave ej:texto
                file_type = ext #si trae la clave entonces se le asigna una extencion  ej:.txt
                # Extraer el nombre después de "llamado"
                if "llamado" in cmd:
                    parts = cmd.split("llamado") 
                    if len(parts) > 1:
                        file_name = parts[1].strip()
                break
        
        if not file_type:
            self.speak("Solo puedo crear archivos usando: crear archivo de texto llamado nombre, crear archivo word llamado nombre, crear archivo excel llamado nombre, o crear archivo powerpoint llamado nombre")
            return
        
        if not file_name:
            self.speak("Debes especificar el nombre del archivo después de 'llamado'")
            return
        
   
        full_file_name = file_name + file_type  # Agregar la extensión
        
        try:
            file_path = os.path.join(current_dir, full_file_name)
            
            # Verificar si el archivo ya existe
            if os.path.exists(file_path):
                self.log_message(f"❌ El archivo {full_file_name} ya existe", output_widget)
                self.speak(f"El archivo {file_name} ya existe")
                return
            
            # Crear el archivo según su tipo
            if file_type == ".txt":
                # Crear archivo de texto plano
                open(file_path, 'x', encoding='utf-8') # se crea el archivo gracias a la "x"
                self.log_message(f"📄 Archivo de texto creado: {full_file_name}", output_widget)
                self.speak(f"Archivo de texto {file_name} creado exitosamente")
            
            elif file_type == ".docx":
                # Crear archivo Word vacío
                open(file_path, 'x', encoding='utf-8') 
                self.log_message(f"📄 Archivo Word creado: {full_file_name}", output_widget)
                self.speak(f"Archivo Word {file_name} creado exitosamente.")
            
            elif file_type == ".xlsx":
                # Crear archivo Excel vacío
                open(file_path, 'x', encoding='utf-8')
                self.log_message(f"📄 Archivo Excel creado: {full_file_name}", output_widget)
                self.speak(f"Archivo Excel {file_name} creado exitosamente.")
            
            elif file_type == ".pptx":
                # Crear archivo PowerPoint vacío  
                open(file_path, 'x', encoding='utf-8')
                self.log_message(f"📄 Archivo PowerPoint creado: {full_file_name}", output_widget)
                self.speak(f"Archivo PowerPoint {file_name} creado. Ábrelo en Microsoft PowerPoint para editarlo")
            
        except Exception as e:
            self.log_message(f"❌ Error creando archivo: {e}", output_widget)
            self.speak("Error al crear el archivo")
        
    #funcion para leer los archivos y carpetas del directorio en el que se encuetre
    def handle_list_command(self, files, current_dir, output_widget):
       
        if files: # verifica si hay archivos
            total_count = len(files)
            folders = [f for f in files if os.path.isdir(os.path.join(current_dir, f))] #verifica si es una carpeta
            files_only = [f for f in files if not os.path.isdir(os.path.join(current_dir, f))]
            folder_count = len(folders)
            file_count = total_count - folder_count 
            
            # Mostrar directorio actual
            current_folder_name = os.path.basename(current_dir)
            self.log_message(f"📍 Ubicación: {current_folder_name}", output_widget)
            self.log_message(f"📋 Elementos ({total_count}):", output_widget)
            self.log_message(f"   📁 Carpetas: {folder_count} | 📄 Archivos: {file_count}", output_widget)
            
            self.speak(f"Estás en {current_folder_name}. Encontré {total_count} elementos: {folder_count} carpetas y {file_count} archivos")
            
            # lectura de folders en caso de existier alguno
            if folders:
                self.log_message("📁 CARPETAS:", output_widget)
                self.speak("Carpetas disponibles:")
                for i, folder in enumerate(folders, 1):
                    self.log_message(f"  {i}. 📁 {folder}", output_widget)
                    self.speak(f"Carpeta {i}: {folder}")
            
            # mostrar archivos
            if files_only:
                self.log_message("📄 ARCHIVOS:", output_widget)
                self.speak("Archivos disponibles:")
                for i, file in enumerate(files_only, 1):
                    self.log_message(f"  {i}. 📄 {file}", output_widget)
                    format_file = file.replace('.txt', ' punto txt').replace('.pdf', ' punto pdf').replace('.jpg', ' punto jpg').replace('.png', ' punto png').replace('.docx', ' punto docx').replace('.xlsx', ' punto excel').replace('.mp3', ' punto mp3').replace('.mp4', ' punto mp4').replace('_', ' ').replace('-', ' ')
                    self.speak(f"Archivo {i}: {format_file}")
     
                    
        else:
            current_folder_name = os.path.basename(current_dir)
            self.log_message(f"No hay elementos en {current_folder_name}", output_widget)
            self.speak(f"No hay elementos en {current_folder_name}")
    
    #funcion para entrar a una carpeta
    def handle_enter_folder_command(self, cmd, files, output_widget):
    
        # extraccion del nombre de la carpeta
        folder_name = cmd.replace("entrar a", "").replace("entrar","").replace("ir a", "").replace("en", "").replace("a la", "").replace("al", "").strip()
        
        if not folder_name:
            self.speak("Debes especificar el nombre de la carpeta")
            return
        
        folders_only = [f for f in files if os.path.isdir(os.path.join(self.current_directory, f))] # filtra y almacena solo los directorios
        
        if not folders_only:
            self.log_message("❌ No hay carpetas en esta ubicación", output_widget)
            self.speak("No hay carpetas disponibles en esta ubicación")
            return
        
        found_folder = self.find_file(folder_name, folders_only) # busca el directorio al que se quiere ir
        
        if found_folder: #verifica que lo encontro
            folder_path = os.path.join(self.current_directory, found_folder)
            
            if os.path.isdir(folder_path): #verifica que sea un directorio
                self.current_directory = folder_path #cambia el directorio
                self.log_message(f"📂 Entrando a: {found_folder}", output_widget)
                self.speak(f"Entrando a la carpeta {found_folder}")
                
            
                new_files, _ = self.get_current_files() #obtiene los archivos que tiene la carpeta
                if new_files:
                    self.speak(f"Esta carpeta contiene {len(new_files)} elementos") # dice la cantidad de archivos que existen
                else:
                    self.speak("Esta carpeta está vacía")
            else:
                self.speak(f"{found_folder} no es una carpeta")
        else:
            self.log_message(f"❌ No se encontró carpeta que coincida con: '{folder_name}'", output_widget)
            self.speak(f"No encontré una carpeta llamada {folder_name}. recuerda que las carptas disponibles son")
            for i, folder in enumerate(folders_only, 1):
                self.speak(folder)
            
    #funcion para volver a un directorio anterior
    def handle_go_back_command(self, output_widget):
        parent_dir = os.path.dirname(self.current_directory) #devuelve directorio padre

        home_dir = os.path.join(os.path.expanduser('~'), 'Desktop') 
        if os.path.commonpath([home_dir, parent_dir]) == home_dir and parent_dir != self.current_directory: # valida que la ruta actual no sea el escritorio 
            self.current_directory = parent_dir
            folder_name = os.path.basename(self.current_directory)
            self.log_message(f"Regresando a: {folder_name}", output_widget)
            self.speak(f"Regresando a {folder_name}")
            
            #obtiene automaticamente los archivos de la carpeta a la que se ingreso
            files, _ = self.get_current_files()
            if files:
                self.speak(f"Esta carpeta contiene {len(files)} elementos")
        else:
            self.speak("No puedo regresar más")
    
    #funcion para saber el directorio actual
    def handle_location_command(self, output_widget):
        current_folder = os.path.basename(self.current_directory)
        
        self.log_message(f"Ubicación actual: {current_folder}", output_widget)
        self.speak(f"Estás en la carpeta {current_folder}")
    
    #funcion para manejar el listado de comandos por parte del asistente de voz
    def handle_help_command(self, output_widget):
        commands = [
            "Comandos disponibles:",
            "• Eliminar [nombre_archivo] - Elimina un archivo o carpeta", 
            "• Mover [nombre_archivo] a [nombre_carpeta] - Mueve archivo",
            "• Renombrar [nombre_archivo] como [nuevo_nombre] - Cambia nombre",
            "• Listar archivos - Muestra todos los archivos",
            "• Entrar [carpeta_destino] - Entra en una carpeta",
            "• Volver - Regresa a la carpeta anterior",
            "• Dónde estoy - Muestra la ubicación actual",
            "• Crear carpeta [nombre] - Crea nueva carpeta",
            "• Crear archivo de texto/word/excel/powerpoint llamado [nombre]",
            "• Parar - Detiene el asistente",
            "• Iniciar - Reinicia el asistente"
        ]
        
        for cmd in commands:
            self.log_message(cmd, output_widget)
        
        for cmd in commands:
            self.speak(cmd)
    
    #funcion para crear carpetas
    def handle_create_folder_command(self, cmd, current_dir, output_widget):
        folder_name = cmd.replace("crear carpeta", "").strip()
        if folder_name:
            try:
                folder_path = os.path.join(current_dir, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                self.log_message(f"📁 Carpeta creada: {folder_name}", output_widget)
                self.speak(f"Carpeta {folder_name} creada")
            except Exception as e:
                self.log_message(f"❌ Error creando carpeta: {e}", output_widget)
                self.speak("Error al crear la carpeta")
        else:
            self.speak("Debes especificar el nombre de la carpeta")
    
    #funcion para iniciar el asistente
    def start_assistant(self, output_widget, page):
        if not self.assistant_active:
            self.assistant_active = True
            self.log_message("🟢 Asistente reiniciado", output_widget)
            self.speak("Asistente reiniciado. ¡Listo para recibir comandos!")
            page.update()
            
            
            self.assistant_thread = threading.Thread(
                target=self.assistant_loop,
                args=(output_widget, page),
                daemon=True
            )
            self.assistant_thread.start()
    
    #funcion para parar el asistente
    def stop_assistant(self, output_widget, page):
        self.assistant_active = False
        self.log_message("🛑 Asistente detenido", output_widget)
        self.speak("Deteniéndome. Di 'iniciar' para reactivarme")
        page.update()
    
    #funcion principaal para escuchar siempre los comandos de voz
    def assistant_loop(self, output_widget, page):
        consecutive_errors = 0
        max_errors = 5
        error_delay = 1
        
        while True:  # Siempre escucha
            try:
                command = self.recognize_speech()
                consecutive_errors = 0  # reinicia el numero de errores
                error_delay = 1  # reinicia el delay
                
                if not command:
                    continue
                
                # Comandos que funcionan siempre
                if any(word in command for word in ["iniciar", "empezar", "activar"]):
                    if not self.assistant_active:
                        self.start_assistant(output_widget, page)
                    else:
                        self.speak("Ya estoy activo")
                    continue
                elif any(word in command for word in ["parar", "detener", "terminar"]):
                    if self.assistant_active:
                        self.stop_assistant(output_widget, page)
                    else:
                        self.speak("Ya estoy detenido")
                    continue
                
                # Solo procesa otros comandos si está activo
                if self.assistant_active:
                    self.execute_command(command, output_widget, page)
                # Si está detenido, ignora silenciosamente otros comandos
                
            except Exception as e:
                consecutive_errors += 1
                print(f"Error en assistant_loop ({consecutive_errors}/{max_errors}): {e}")
                
                if consecutive_errors >= max_errors:
                    print("Demasiados errores consecutivos, esperando más tiempo...")
                    error_delay = min(error_delay * 2, 10)  # Incrementar delay exponencialmente
                    consecutive_errors = 0
                
                time.sleep(error_delay)
                continue
            
            time.sleep(0.3)  # Delay más corto para mejor respuesta


def main(page: ft.Page):
    # configuracion de la ventana
    page.title = "🎤 Asistente de Voz"
    page.window.width = 600
    page.window.height = 750
    page.theme_mode = ft.ThemeMode.DARK
    
    # inicializa el asistente
    assistant = VoiceAssistant()
    
    # commponentes de la interfas del usuario
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
    
    # Instructions text
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
    assistant.speak("Hola! Soy tu asistente de voz. Di 'comandos' para conocer las opciones disponibles.")
    
    # inicializacion del asistente
    assistant.assistant_thread = threading.Thread(
        target=assistant.assistant_loop,
        args=(log_output, page),
        daemon=True
    )
    assistant.assistant_thread.start()

if __name__ == "__main__":
    ft.app(target=main)
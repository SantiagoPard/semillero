import os
import threading
import time
from queue import Queue
from datetime import datetime
import speech_recognition as sr
import pyttsx3
import shutil
import winsound 
from command_handlers import CommandHandlers

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
    
    def play_listening_beep(self):
        #Reproduce un pitido para indicar que está empezando a escuchar"""
        try:
            # Un solo pitido claro para indicar "¡AHORA HABLA!"
            winsound.Beep(1200, 1000)  # Pitido agudo y claro
        except Exception as e:
            print(f"No se pudo reproducir el pitido: {e}")
            
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
        self.recognizer.pause_threshold = 0.5
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
       if text.strip():
            self.voice_queue.put({'text': text, 'timestamp': time.time()})
    
    #espera a que el asistente pare de hablar
    def wait_for_speech_to_finish(self):
        while True:
            with self.speaking_lock:
                if not self.is_speaking and self.voice_queue.empty():
                    break
          
  

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
            
            self.play_listening_beep()

            mic = sr.Microphone() # Crear nuevo micrófono para cada uso (evita problemas de estados)
                
            with mic as source:
                # Ajustar para ruido ambiente solo ocasionalmente
                if not hasattr(self, '_ambient_adjusted') or not self._ambient_adjusted:
                    try:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                        self._ambient_adjusted = True
                    except Exception:
                        # Si falla el ajuste, continuar sin él
                        pass
                
                # Escuchar con timeout
                audio = self.recognizer.listen(source, timeout=0, phrase_time_limit=0)
                
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
        
        handlers = CommandHandlers(self)
        # procesa los comandos detectando la palabra clave y ejecutando el metodo correspondiente
        
        if "sin comando" in cmd:
            handlers.speak("por favor , dime un comando")
        elif "eliminar" in cmd or "borrar" in cmd:
            handlers.handle_delete_command(cmd, files, current_dir, output_widget)
        elif "mover" in cmd:
            handlers.handle_move_command(cmd, files, current_dir, output_widget)
        elif "renombrar" in cmd:
            handlers.handle_rename_command(cmd, files, current_dir, output_widget)
        elif any(phrase in cmd for phrase in ["listar", "mostrar", "qué archivos"]):
            handlers.handle_list_command(files, current_dir, output_widget)
        elif "entrar a" in cmd or "ir a" in cmd or "entrar" in cmd:
            handlers.handle_enter_folder_command(cmd, files, output_widget)
        elif "volver" in cmd or "salir" in cmd or "regresar" in cmd:
            handlers.handle_go_back_command(output_widget)
        elif "dónde estoy" in cmd or "ubicación" in cmd:
            handlers.handle_location_command(output_widget)
        elif "comandos" in cmd or "ayuda" in cmd:
            handlers.handle_help_command(output_widget)
        elif "crear carpeta" in cmd:
            handlers.handle_create_folder_command(cmd, current_dir, output_widget)
        elif "crear archivo" in cmd:
            # Solo permitir el formato específico con tipo
            if any(type_word in cmd for type_word in ["archivo de texto" , "texto", "word", "excel", "powerpoint", "power point", "presentación", "presentacion"]) and "llamado" in cmd:
                handlers.handle_create_file_with_type_command(cmd, current_dir, output_widget)
            else:
                self.speak("Usa el formato: crear archivo de texto llamado nombre, crear archivo word llamado nombre, crear archivo excel llamado nombre, o crear archivo powerpoint llamado nombre")
            
        else:
            self.speak("No reconozco ese comando. Di 'comandos' para ver opciones disponibles.")
        
        page.update()
    
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
            

    
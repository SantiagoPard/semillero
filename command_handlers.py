import os
import shutil
import send2trash
import time

class CommandHandlers:
    def __init__(self, voice_assistant):
        self.assistant = voice_assistant
        # self.assistant.current_directory = voice_assistant.current_directory
    def get_current_files(self):
        try:
            files = os.listdir(self.assistant.current_directory) #obtiene los archivos y carpetas del directorio actual
            return files, self.assistant.current_directory #devuelve los archivos encontrados y el directorio de donde los extrajo
        except Exception:
            return [], ""   #controla el error que se genera en caso de no encontrar nada    
        
    def find_file(self, target, files):
        target = target.lower().strip()
        # Si no se especifica un archivo, retornar None
        if not target:
            return None
            
        files_lower = {f.lower(): f for f in files}
        
        for low, orig in files_lower.items():# Recorre cada archivo
            if target in low:               # verifica si el nombre está contenido en el nombre del archivo
                return orig 
        
        return None
    
    def handle_delete_command(self, cmd, files, current_dir, output_widget):
        target = cmd.replace("eliminar", "").replace("borrar", "").strip()
                
        if not target:
            self.assistant.speak("Debes especificar qué archivo o carpeta quieres eliminar")
            return
            
        found_file = self.find_file(target, files)
        
        if not found_file:
            self.assistant.speak("Archivo o carpeta no encontrada")
            return
        
        try:
            filepath = os.path.join(current_dir, found_file)
            item_type = "carpeta" if os.path.isdir(filepath) else "archivo"
            
            
            # Pedir confirmación
            self.assistant.speak(f"¿Estás seguro que deseas eliminar {item_type} {found_file}? Di 'sí' para confirmar o 'no' para cancelar")
            
            time.sleep(0.1)
            
            # CRÍTICO: Esperar a que termine de hablar ANTES de hacer el beep
            self.assistant.wait_for_speech_to_finish()
            
            
            
            # Esperar respuesta de confirmación
            confirmation = self.assistant.recognize_speech()
            
            if not confirmation:
                self.assistant.log_message(f"❌ No se recibió respuesta. Eliminación cancelada", output_widget)
                self.assistant.speak("No se recibió respuesta. Operación cancelada")
                return
            
            confirmation = confirmation.lower().strip()
            
            if confirmation in ["sí", "si", "yes", "afirmativo"]:
                send2trash.send2trash(filepath)
                
                self.assistant.log_message(f"🗑️ {item_type.capitalize()} enviado a la papelera: {found_file}", output_widget)
                self.assistant.speak(f"{item_type.capitalize()} {found_file} enviado a la papelera de reciclaje")
            else:
                self.assistant.log_message(f"❌ Eliminación cancelada: {found_file}", output_widget)
                self.assistant.speak("Eliminación cancelada")
                
        except Exception as e:
            error_msg = f"Error enviando a la papelera: {str(e)}"
            self.assistant.log_message(f"❌ {error_msg}", output_widget)
            self.assistant.speak("Error al enviar a la papelera. Verifica los permisos")
    
    def handle_move_command(self, cmd, files, current_dir, output_widget):
    
        if " a " not in cmd: # si a no se encuentra en el mensaje 
            self.assistant.speak("Debes decir: mover archivo a carpeta")
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
                self.assistant.log_message(f"📁 {found_file} movido a {dest_folder}", output_widget) # accion agregada al log
                self.assistant.speak(f"{found_file} movido a {dest_folder}") # output de voz por parte de el asistente
            except Exception as e:
                self.assistant.log_message(f"❌ Error moviendo: {e}", output_widget)
                self.assistant.speak("Error al mover el archivo")
        else:
            self.assistant.speak("Archivo no encontrado")
 
    #funcion para renombrar archivo   
    def handle_rename_command(self, cmd, files, current_dir, output_widget):
 
        if " como " not in cmd:
            self.assistant.speak("Debes decir: renombrar archivo como nuevo nombre")
            return
        
        parts = cmd.split(" como ")
        target = parts[0].replace("renombrar", "").strip() # quita la palabra renombrar y elimina espacios
        new_name = parts[1].strip() # elimina espacios del nuevo nombre
        
        found_file = self.find_file(target, files) # busca si el archivo existe
        if found_file:
            try:
                old_path = os.path.join(current_dir, found_file)
                
                file_extension = os.path.splitext(found_file)[1] # Obtener la extensión del archivo original
                
          
                if file_extension:      # Si el archivo original tiene extensión, se conserva
                    new_name_lower = new_name.lower() 
                    extension_lower = file_extension.lower()
                    
                    if not new_name_lower.endswith(extension_lower):
                        final_new_name = new_name + file_extension # Agrega la extensión original al nuevo nombre
                        self.assistant.log_message(f"🔧 Conservando extensión: {file_extension}", output_widget)
                    else:
                      
                        final_new_name = new_name  # El usuario ya incluyó la extensión
                else:
                    final_new_name = new_name  # El archivo original no tiene extensión
                
                new_path = os.path.join(current_dir, final_new_name)
                
              
                if os.path.exists(new_path) and new_path != old_path:  # Verificar si ya existe un archivo con el nuevo nombre
                    self.assistant.log_message(f"❌ Ya existe un archivo llamado: {final_new_name}", output_widget)
                    self.assistant.speak(f"Ya existe un archivo llamado {final_new_name}")
                    return
                
                os.rename(old_path, new_path)
                
                self.assistant.log_message(f"✏️ {found_file} renombrado a {final_new_name}", output_widget)
                self.assistant.speak(f"{found_file} renombrado a {final_new_name}")
                
            except Exception as e:
                self.assistant.log_message(f"❌ Error renombrando: {e}", output_widget)
                self.assistant.speak("Error al renombrar el archivo")
        else:
            self.assistant.speak("Archivo no encontrado")
            
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
            self.assistant.speak("Solo puedo crear archivos usando: crear archivo de texto llamado nombre, crear archivo word llamado nombre, crear archivo excel llamado nombre, o crear archivo powerpoint llamado nombre")
            return
        
        if not file_name:
            self.assistant.speak("Debes especificar el nombre del archivo después de 'llamado'")
            return
        
   
        full_file_name = file_name + file_type  # Agregar la extensión
        
        try:
            file_path = os.path.join(current_dir, full_file_name)
            
            # Verificar si el archivo ya existe
            if os.path.exists(file_path):
                self.assistant.log_message(f"❌ El archivo {full_file_name} ya existe", output_widget)
                self.assistant.speak(f"El archivo {file_name} ya existe")
                return
            
            # Crear el archivo según su tipo
            if file_type == ".txt":
                # Crear archivo de texto plano
                open(file_path, 'x', encoding='utf-8') # se crea el archivo gracias a la "x"
                self.assistant.log_message(f"📄 Archivo de texto creado: {full_file_name}", output_widget)
                self.assistant.speak(f"Archivo de texto {file_name} creado exitosamente")
            
            elif file_type == ".docx":
                # Crear archivo Word vacío
                open(file_path, 'x', encoding='utf-8') 
                self.assistant.log_message(f"📄 Archivo Word creado: {full_file_name}", output_widget)
                self.assistant.speak(f"Archivo Word {file_name} creado exitosamente.")
            
            elif file_type == ".xlsx":
                # Crear archivo Excel vacío
                open(file_path, 'x', encoding='utf-8')
                self.assistant.log_message(f"📄 Archivo Excel creado: {full_file_name}", output_widget)
                self.assistant.speak(f"Archivo Excel {file_name} creado exitosamente.")
            
            elif file_type == ".pptx":
                # Crear archivo PowerPoint vacío  
                open(file_path, 'x', encoding='utf-8')
                self.assistant.log_message(f"📄 Archivo PowerPoint creado: {full_file_name}", output_widget)
                self.assistant.speak(f"Archivo PowerPoint {file_name} creado. Ábrelo en Microsoft PowerPoint para editarlo")
            
        except Exception as e:
            self.assistant.log_message(f"❌ Error creando archivo: {e}", output_widget)
            self.assistant.speak("Error al crear el archivo")
        
    #funcion para leer los archivos y carpetas del directorio en el que se encuetre
    def handle_list_command(self, files, current_dir, output_widget):
       
        if files: # verifica si hay archivos
            total_count = len(files)
            folders = [f for f in files if os.path.isdir(os.path.join(current_dir, f))] #verifica si es una carpeta
            files_only = [f for f in files if not os.path.isdir(os.path.join(current_dir, f))]
            folder_count = len(folders)
            file_count = total_count - folder_count 
            
            # Mostrar directorio current_dir
            current_folder_name = os.path.basename(current_dir)
            self.assistant.log_message(f"📍 Ubicación: {current_folder_name}", output_widget)
            self.assistant.log_message(f"📋 Elementos ({total_count}):", output_widget)
            self.assistant.log_message(f"   📁 Carpetas: {folder_count} | 📄 Archivos: {file_count}", output_widget)
            
            self.assistant.speak(f"Estás en {current_folder_name}. Encontré {total_count} elementos: {folder_count} carpetas y {file_count} archivos")
            
            # lectura de folders en caso de existier alguno
            if folders:
                self.assistant.log_message("📁 CARPETAS:", output_widget)
                self.assistant.speak("Carpetas disponibles:")
                for i, folder in enumerate(folders, 1):
                    self.assistant.log_message(f"  {i}. 📁 {folder}", output_widget)
                    self.assistant.speak(f"Carpeta {i}: {folder}")
            
            # mostrar archivos
            if files_only:
                self.assistant.log_message("📄 ARCHIVOS:", output_widget)
                self.assistant.speak("Archivos disponibles:")
                for i, file in enumerate(files_only, 1):
                    self.assistant.log_message(f"  {i}. 📄 {file}", output_widget)
                    format_file = file.replace('.txt', ' punto txt').replace('.pdf', ' punto pdf').replace('.jpg', ' punto jpg').replace('.png', ' punto png').replace('.docx', ' punto docx').replace('.xlsx', ' punto excel').replace('.mp3', ' punto mp3').replace('.mp4', ' punto mp4').replace('_', ' ').replace('-', ' ')
                    self.assistant.speak(f"Archivo {i}: {format_file}")
     
                    
        else:
            current_folder_name = os.path.basename(current_dir)
            self.assistant.log_message(f"No hay elementos en {current_folder_name}", output_widget)
            self.assistant.speak(f"No hay elementos en {current_folder_name}")
    
    #funcion para entrar a una carpeta
    def handle_enter_folder_command(self, cmd, files, output_widget):
    
        # extraccion del nombre de la carpeta
        folder_name = cmd.replace("entrar a", "").replace("entrar","").replace("ir a", "").replace("en", "").replace("a la", "").replace("al", "").strip()
        
        if not folder_name:
            self.assistant.speak("Debes especificar el nombre de la carpeta")
            return
        
        folders_only = [f for f in files if os.path.isdir(os.path.join(self.assistant.current_directory, f))] # filtra y almacena solo los directorios
        
        if not folders_only:
            self.assistant.log_message("❌ No hay carpetas en esta ubicación", output_widget)
            self.assistant.speak("No hay carpetas disponibles en esta ubicación")
            return
        
        found_folder = self.find_file(folder_name, folders_only) # busca el directorio al que se quiere ir
        
        if found_folder: #verifica que lo encontro
            folder_path = os.path.join(self.assistant.current_directory, found_folder)
            
            if os.path.isdir(folder_path): #verifica que sea un directorio
                self.assistant.current_directory = folder_path #cambia el directorio
                self.assistant.log_message(f"📂 Entrando a: {found_folder}", output_widget)
                self.assistant.speak(f"Entrando a la carpeta {found_folder}")
                
            
                new_files, _ = self.get_current_files() #obtiene los archivos que tiene la carpeta
                if new_files:
                    self.assistant.speak(f"Esta carpeta contiene {len(new_files)} elementos") # dice la cantidad de archivos que existen
                else:
                    self.assistant.speak("Esta carpeta está vacía")
            else:
                self.assistant.speak(f"{found_folder} no es una carpeta")
        else:
            self.assistant.log_message(f"❌ No se encontró carpeta que coincida con: '{folder_name}'", output_widget)
            self.assistant.speak(f"No encontré una carpeta llamada {folder_name}. recuerda que las carptas disponibles son")
            for i, folder in enumerate(folders_only, 1):
                self.assistant.speak(folder)
            
    #funcion para volver a un directorio anterior
    def handle_go_back_command(self, output_widget):
        parent_dir = os.path.dirname(self.assistant.current_directory) #devuelve directorio padre

        home_dir = os.path.join(os.path.expanduser('~'), 'Desktop') 
        if os.path.commonpath([home_dir, parent_dir]) == home_dir and parent_dir != self.assistant.current_directory: # valida que la ruta actual no sea el escritorio 
            self.assistant.current_directory = parent_dir
            folder_name = os.path.basename(self.assistant.current_directory)
            self.assistant.log_message(f"Regresando a: {folder_name}", output_widget)
            self.assistant.speak(f"Regresando a {folder_name}")
            
            #obtiene automaticamente los archivos de la carpeta a la que se ingreso
            files, _ = self.get_current_files()
            if files:
                self.assistant.speak(f"Esta carpeta contiene {len(files)} elementos")
        else:
            self.assistant.speak("No puedo regresar más")
    
    #funcion para saber el directorio actual
    def handle_location_command(self, output_widget):
        current_folder = os.path.basename(self.assistant.current_directory)
        
        self.assistant.log_message(f"Ubicación actual: {current_folder}", output_widget)
        self.assistant.speak(f"Estás en la carpeta {current_folder}")
    
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
            self.assistant.log_message(cmd, output_widget)
        
        for cmd in commands:
            self.assistant.speak(cmd)
    
    #funcion para crear carpetas
    def handle_create_folder_command(self, cmd, current_dir, output_widget):
        folder_name = cmd.replace("crear carpeta", "").strip()
        if folder_name:
            try:
                folder_path = os.path.join(current_dir, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                self.assistant.log_message(f"📁 Carpeta creada: {folder_name}", output_widget)
                self.assistant.speak(f"Carpeta {folder_name} creada")
            except Exception as e:
                self.assistant.log_message(f"❌ Error creando carpeta: {e}", output_widget)
                self.assistant.speak("Error al crear la carpeta")
        else:
            self.assistant.speak("Debes especificar el nombre de la carpeta")
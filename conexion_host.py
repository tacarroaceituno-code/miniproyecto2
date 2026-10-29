"""Estructura recomendada para gestionar la comunicación SSH/SFTP con el host central."""

import json
from pathlib import Path

import paramiko


class ConexionHost:
    def __init__(self, config: dict):
        self.host = config["host"]
        self.port = config.get("port", 22)
        self.username = config["username"]
        self.password = config["password"]
        self.remote_inbox = config.get("remote_inbox", "/inbox")
        self.remote_outbox = config.get("remote_outbox", "/outbox")

        self.ssh = None
        self.sftp = None
        self.mensajes_leidos = set()

    def conectar(self):
        """Establece la conexión SSH y abre el canal SFTP."""
        # TODO:
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            self.sftp = self.ssh.open_sftp()
            print(f"Conexión SFTP establecida con {self.host}")
        except Exception as e:
            print(f"Error al conectar con {self.host}: {e}")
            self.cerrar_conexion()
            raise

    def cerrar_conexion(self):
        """Cierra de forma ordenada las conexiones SFTP y SSH."""
        # TODO:
        if self.sftp:
            try:
                self.sftp.close()
            except Exception:
                pass
            self.sftp = None

        if self.ssh:
            try:
                self.ssh.close()
            except Exception:
                pass
            self.ssh = None

    def verificar_conexion(self):
        """Comprueba si la conexión SSH/SFTP se encuentra disponible."""
        # TODO:
        if not self.ssh or not self.sftp:
            return False
        try:
            transport = self.ssh.get_transport()
            if transport and transport.is_active():
                self.sftp.normalize('.')
                return True
        except Exception:
            pass
        return False

    def enviar_json(self, mensaje: dict):
        """Transfiere un mensaje JSON al directorio /inbox del host central."""
        # TODO:
        if not self.verificar_conexion():
            self.conectar()
        event_id = mensaje.get("EventID", uuid.uuid4())
        nombre_archivo = f"evento_{event_id}_{int(time.time())}.json"
        nombre_temporal = f".tmp_{nombre_archivo}"
        ruta_remota_final = f"{self.remote_inbox.rstrip('/')}/{nombre_archivo}"
        ruta_remota_temporal = f"{self.remote_inbox.rstrip('/')}/{nombre_temporal}"
        contenido_json = json.dumps(mensaje, ensure_ascii=False, indent=4)
        try:
            with self.sftp.file(ruta_remota_temporal, 'w') as f:
                f.write(contenido_json)
                self.sftp.rename(ruta_remota_temporal, ruta_remota_final)
                print(f"Mensaje enviado exitosamente a {ruta_remota_final}")

        except Exception as e:
            print(f"Error al enviar el JSON por SFTP: {e}")
            try:
                self.sftp.remove(ruta_remota_temporal)
            except Exception:
                pass
            raise

    def leer_nuevos_json(self):
        """Lee los mensajes JSON nuevos disponibles en /outbox."""
        # TODO:
        if not self.verificar_conexion():
            self.conectar()

        mensajes_nuevos = []

        try:
            archivos_remotos = self.sftp.listdir(self.remote_outbox)
            
            for archivo in archivos_remotos:
                if not archivo.endswith(".json"):
                    continue

                if archivo not in self.mensajes_leidos:
                    ruta_archivo = f"{self.remote_outbox.rstrip('/')}/{archivo}"
                    
                    with self.sftp.file(ruta_archivo, 'r') as f:
                        contenido = f.read().decode('utf-8')
                        datos_json = json.loads(contenido)
                        mensajes_nuevos.append(datos_json)
                    self.mensajes_leidos.add(archivo)

        except Exception as e:
            print(f"Error al leer los mensajes nuevos de {self.remote_outbox}: {e}")

        return mensajes_nuevos        

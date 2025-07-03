# -*- coding: utf-8 -*-
# p2p_miner_node.py
#
# P2P Miner GUI - Lógica del nodo minero P2P.
# Copyright (c) 2025 Marcelo Tonini - Mendoza, Argentina
# Licencia: MIT
#
# Descripción: Este script implementa la funcionalidad de un nodo P2P,
# maneja la comunicación con otros peers y controla el proceso de minería XMRig.
#

import socket
import threading
import json
import time
import sys
import subprocess
import os # <-- ¡Asegúrate de que 'os' esté importado! Ya lo tienes.
import queue

# --- Configuración del Nodo ---
PEER_NODES = [
    ('localhost', 8000),
    ('localhost', 8001),
    ('localhost', 8002)
]
MESSAGE_BUFFER_SIZE = 4096

# --- INICIO DEL CAMBIO PARA LA RUTA DE XMRIG ---
# Determinar el directorio base de la aplicación (donde se encuentra el script principal)
if getattr(sys, 'frozen', False):
    # Si la aplicación está empaquetada (ej. con PyInstaller)
    APPLICATION_BASE_DIR = os.path.dirname(sys.executable)
else:
    # Si se ejecuta desde el código fuente
    APPLICATION_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Construir la ruta al ejecutable de XMRig
# Se asume que xmrig.exe está en la subcarpeta 'xmrig' dentro del directorio base.
XMRIG_PATH = os.path.join(APPLICATION_BASE_DIR, "xmrig", "xmrig.exe")

# Opcional: Imprime la ruta para depuración (puedes borrar esta línea después)
print(f"DEBUG: XMRig path detected: {XMRIG_PATH}")
# --- FIN DEL CAMBIO PARA LA RUTA DE XMRIG ---


# La dirección de la billetera y el pool ahora se pasan por la GUI
MONERO_WALLET_ADDRESS_DEFAULT = "4931PMmb9FE2LapSempngoBNYoVP2ZdDt8C1bDScwhbNMcKzLw2guY5H1hxvNnRmfydJVKemEJQFdguxRK6J9hv5FHc8ABd" # <--- ¡CÁMBIAME SI AÚN NO LO HAS HECHO!
POOL_URL = "pool.supportxmr.com:443" # URL de tu pool, puedes fijarla aquí

# --- Tipos de Mensajes P2P ---
MSG_TYPE_HANDSHAKE = "handshake"
MSG_TYPE_TRANSACTION = "transaction"
MSG_TYPE_BLOCK = "block"
MSG_TYPE_PEER_LIST = "peer_list"
MSG_TYPE_REQUEST_PEERS = "request_peers"
MSG_TYPE_POOL_INFO_REQUEST = "pool_info_request" # Nuevo tipo de mensaje
MSG_TYPE_POOL_INFO_RESPONSE = "pool_info_response" # Nuevo tipo de mensaje
MSG_TYPE_INTERNAL_COMMAND = "internal_command" # Para comandos internos enviados desde stdin (ej. por GUI)

class P2PNode:
    def __init__(self, port, wallet_address):
        self.port = port
        self.host = '0.0.0.0'
        self.peers = set() # Usaremos un set para almacenar los peers conectados
        self.peers_lock = threading.Lock() # Bloqueo para proteger la lista de peers
        self.running = True
        self.xmrig_process = None
        self.wallet_address = wallet_address
        
        # Atributos para la información del pool del nodo
        self.current_pool_url = "" 
        self.current_hashrate = "N/A"
        self.last_xmrig_activity = "N/A"

        self.command_queue = queue.Queue() # Cola para comandos recibidos via stdin
        print(f"[{self.port}] Nodo inicializado en el puerto {self.port} con billetera: {self.wallet_address[:10]}...")

    def _create_message(self, msg_type, data):
        return json.dumps({"type": msg_type, "data": data}).encode('utf-8')

    def _send_message(self, client_socket, msg_type, data):
        try:
            message = self._create_message(msg_type, data)
            client_socket.sendall(message)
        except Exception as e:
            print(f"[{self.port}] Error al enviar mensaje a {client_socket.getpeername()}: {e}")
            # Ya no se llama remove_peer aquí, ya que el handler de conexión se encargará de esto
            # si la conexión realmente falló de forma irrecuperable.

    def _broadcast_message(self, msg_type, data, exclude_peer=None):
        message = self._create_message(msg_type, data)
        with self.peers_lock:
            peers_to_remove = []
            for peer_tuple in list(self.peers): # Iterar sobre una copia para permitir modificación
                try:
                    peer_host, peer_port = peer_tuple
                    # Reconectar o usar conexión existente
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(5) # Pequeño timeout para la conexión
                        s.connect(peer_tuple)
                        s.sendall(message)
                except Exception as e:
                    print(f"[{self.port}] Error al transmitir a {peer_tuple}: {e}")
                    peers_to_remove.append(peer_tuple)
            for p in peers_to_remove:
                self.peers.discard(p) # Usar discard para eliminar de un set

    def _handle_client_connection(self, client_socket, addr):
        print(f"[{self.port}] Conexión aceptada desde {addr}")
        try:
            # Enviar handshake al nuevo peer
            self._send_message(client_socket, MSG_TYPE_HANDSHAKE, {"port": self.port})

            while self.running:
                data = client_socket.recv(MESSAGE_BUFFER_SIZE)
                if not data:
                    break

                try:
                    message = json.loads(data.decode('utf-8'))
                    self._process_received_message(client_socket, message)
                except json.JSONDecodeError:
                    print(f"[{self.port}] Mensaje JSON inválido de {addr}: {data.decode('utf-8', errors='ignore')}")
                except Exception as e:
                    print(f"[{self.port}] Error al procesar mensaje de {addr}: {e}")

        except ConnectionResetError:
            print(f"[{self.port}] Conexión con {addr} reseteada por el peer.")
        except socket.timeout:
            print(f"[{self.port}] Timeout de conexión con {addr}.")
        except Exception as e:
            print(f"[{self.port}] Error en la conexión con el cliente {addr}: {e}")
        finally:
            self.remove_peer(client_socket)
            client_socket.close()
            print(f"[{self.port}] Conexión con {addr} cerrada.")

    def _process_received_message(self, client_socket, message):
        msg_type = message.get("type")
        msg_data = message.get("data")

        print(f"[{self.port}] Recibido '{msg_type}' de {client_socket.getpeername()}")

        if msg_type == MSG_TYPE_HANDSHAKE:
            peer_port = msg_data.get("port")
            peer_addr = client_socket.getpeername()[0] # Obtener el host real
            self.add_peer((peer_addr, peer_port))
            print(f"[{self.port}] Handshake con {peer_addr}:{peer_port}. Peers actuales: {len(self.peers)}")
            # Enviar lista de peers conocidos al nuevo peer
            self._send_message(client_socket, MSG_TYPE_PEER_LIST, list(self.peers))

        elif msg_type == MSG_TYPE_TRANSACTION:
            print(f"[{self.port}] Nueva transacción recibida: {msg_data}")
            self._broadcast_message(MSG_TYPE_TRANSACTION, msg_data, exclude_peer=client_socket)

        elif msg_type == MSG_TYPE_BLOCK:
            print(f"[{self.port}] Nuevo bloque recibido: {msg_data.get('index')}")
            self._broadcast_message(MSG_TYPE_BLOCK, msg_data, exclude_peer=client_socket)

        elif msg_type == MSG_TYPE_REQUEST_PEERS:
            # Un peer solicita nuestra lista de peers
            self._send_message(client_socket, MSG_TYPE_PEER_LIST, list(self.peers))
            print(f"[{self.port}] Enviando lista de {len(self.peers)} peers a {client_socket.getpeername()}")

        elif msg_type == MSG_TYPE_PEER_LIST:
            # Recibimos una lista de peers de otro nodo
            new_peers = msg_data
            added_count = 0
            for peer in new_peers:
                peer_tuple = tuple(peer) # Asegurarse de que sea una tupla
                if peer_tuple[1] != self.port and peer_tuple not in self.peers: # No añadirme a mí mismo
                    if self.add_peer(peer_tuple):
                        added_count += 1
            if added_count > 0:
                print(f"[{self.port}] Añadidos {added_count} nuevos peers. Total: {len(self.peers)}")

        elif msg_type == MSG_TYPE_POOL_INFO_REQUEST:
            # Nuevo: Manejar solicitud de información de pool
            print(f"[{self.port}] Recibida solicitud de información de pool de {client_socket.getpeername()}.")
            pool_data = {
                "wallet_address": self.wallet_address,
                "pool_url": self.current_pool_url,
                "hashrate": self.current_hashrate,
                "last_activity": self.last_xmrig_activity,
                "node_port": self.port # Para identificar qué nodo responde
            }
            self._send_message(client_socket, MSG_TYPE_POOL_INFO_RESPONSE, pool_data)

        elif msg_type == MSG_TYPE_POOL_INFO_RESPONSE:
            # Nuevo: Manejar respuesta de información de pool
            responding_node_port = msg_data.get("node_port", "Desconocido")
            print(f"\n--- Info de Pool del Nodo {responding_node_port} ({client_socket.getpeername()[0]}) ---")
            print(f"  Billetera: {msg_data.get('wallet_address', 'N/A')}")
            print(f"  Pool URL: {msg_data.get('pool_url', 'N/A')}")
            print(f"  Hashrate: {msg_data.get('hashrate', 'N/A')}")
            print(f"  Última Actividad: {msg_data.get('last_activity', 'N/A')}")
            print("---------------------------------------------------\n")

        elif msg_type == MSG_TYPE_INTERNAL_COMMAND:
            # Manejar comandos internos que no son P2P, pero vienen de un sistema de control (como la GUI)
            command = msg_data.get("command")
            self._execute_internal_command(command)

    def add_peer(self, peer_tuple):
        """Añade un peer si no es el propio nodo y no está ya en la lista."""
        with self.peers_lock:
            if peer_tuple[1] != self.port and peer_tuple not in self.peers:
                self.peers.add(peer_tuple)
                return True
            return False

    def remove_peer(self, client_socket):
        """Intenta remover un peer usando la información del socket."""
        peer_to_remove = None
        try:
            addr = client_socket.getpeername()
            with self.peers_lock:
                for peer_tuple in self.peers:
                    # Comparamos la dirección IP y el puerto de conexión real
                    if peer_tuple[0] == addr[0] and peer_tuple[1] == addr[1]:
                        peer_to_remove = peer_tuple
                        break
                if peer_to_remove:
                    self.peers.discard(peer_to_remove)
                    print(f"[{self.port}] Peer {peer_to_remove} desconectado. Peers restantes: {len(self.peers)}")
        except OSError: # Socket puede estar ya cerrado
            pass
        except Exception as e:
            print(f"[{self.port}] Error al remover peer: {e}")

    def connect_to_peer(self, peer_host, peer_port):
        if (peer_host, peer_port) == (self.host, self.port):
            return # No conectar a sí mismo

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((peer_host, peer_port))
                print(f"[{self.port}] Conectado a peer existente {peer_host}:{peer_port}")
                self._send_message(s, MSG_TYPE_HANDSHAKE, {"port": self.port})
                # Solicitar lista de peers del nuevo peer
                self._send_message(s, MSG_TYPE_REQUEST_PEERS, {})

                # Mantener la conexión abierta para intercambio de mensajes
                # Esto es una simplificación; en un sistema real, el _handle_client_connection
                # se encargaría de la lectura continua. Aquí es solo para handshake inicial.
                # Para un intercambio de mensajes bidireccional continuo, cada conexión requiere un hilo de lectura.
                # Para simplificar el ejemplo, las conexiones de "salida" se abren y cierran por cada mensaje.
                # El listener se encarga de las conexiones "entrantes" y su lectura continua.
        except Exception as e:
            print(f"[{self.port}] No se pudo conectar al peer {peer_host}:{peer_port}: {e}")

    def start_xmrig(self):
        if self.xmrig_process and self.xmrig_process.poll() is None:
            print(f"[{self.port}] XMRig ya está en ejecución.")
            return

        try:
            # Comando básico para XMRig. ¡Ajusta los parámetros según tu configuración deseada!
            # Asegúrate de usar un pool y una una dirección de billetera válidos.
            xmrig_command = [
                XMRIG_PATH, # <-- ¡Ahora usa la ruta dinámica!
                "-o", "pool.supportxmr.com:443", # Ejemplo de pool
                "-u", self.wallet_address,
                "-k", # Keepalive
                "--tls" # Usar TLS/SSL si el pool lo soporta
                # "--cpu", # ELIMINADO
                # "--nicehash" # ELIMINADO
                # "-p", "x" # Contraseña para el worker (opcional)
            ]
            print(f"[{self.port}] Iniciando XMRig con comando: {' '.join(xmrig_command)}")
            
            # stdout y stderr pipeados para leer la salida de XMRig
            self.xmrig_process = subprocess.Popen(
                xmrig_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True, # Para texto en lugar de bytes
                bufsize=1 # Línea por línea
            )
            threading.Thread(target=self._read_xmrig_output, daemon=True).start()
            print(f"[{self.port}] XMRig iniciado.")

        except FileNotFoundError:
            print(f"[{self.port}] Error: {XMRIG_PATH} no encontrado. Asegúrate de que esté en la ruta correcta.")
        except Exception as e:
            print(f"[{self.port}] Error al iniciar XMRig: {e}")

    def _read_xmrig_output(self):
        """Lee la salida de XMRig y actualiza el estado del nodo."""
        for line in iter(self.xmrig_process.stdout.readline, ''):
            sys.stdout.write(f"[{self.port} XMRig] {line}")
            # Aquí podrías parsear la línea para actualizar hashrate, shares, etc.
            if "speed" in line and "current" in line:
                try:
                    parts = line.split("speed")
                    if len(parts) > 1:
                        hashrate_str = parts[1].strip().split(';')[0].strip()
                        self.current_hashrate = hashrate_str
                        self.last_xmrig_activity = time.strftime('%H:%M:%S')
                except Exception as e:
                    print(f"[{self.port} XMRig Parser Error] {e}")

        for line in iter(self.xmrig_process.stderr.readline, ''):
            sys.stderr.write(f"[{self.port} XMRig ERROR] {line}")

        print(f"[{self.port}] Hilo de lectura de XMRig finalizado. Código de salida: {self.xmrig_process.returncode}")
        # self.xmrig_process = None # <--- ¡ELIMINA ESTA LÍNEA!
        self.current_hashrate = "N/A"
        self.last_xmrig_activity = "N/A"

    def stop_xmrig(self):
        # Asegúrate de que xmrig_process exista y sea un objeto Popen
        if self.xmrig_process is not None:
            if self.xmrig_process.poll() is None: # Si el proceso aún está en ejecución
                print(f"[{self.port}] Deteniendo XMRig (PID: {self.xmrig_process.pid})...")
                try:
                    # Intenta terminar amistosamente (SIGTERM)
                    self.xmrig_process.terminate()
                    self.xmrig_process.wait(timeout=5) # Espera un poco
                    if self.xmrig_process.poll() is None: # Si sigue vivo, forzar
                        self.xmrig_process.kill()
                    print(f"[{self.port}] XMRig detenido.")
                except Exception as e:
                    print(f"[{self.port}] Error al detener XMRig: {e}")
            else:
                print(f"[{self.port}] XMRig no estaba en ejecución activa (ya había terminado).")
            # Restablecer el proceso a None después de intentar detenerlo, UNA VEZ QUE stop_xmrig HA TERMINADO SUS COMPROBACIONES
            self.xmrig_process = None # <--- MANTENER ESTA LÍNEA AQUÍ
            self.current_hashrate = "N/A"
            self.last_xmrig_activity = "N/A"
        else:
            print(f"[{self.port}] XMRig no está en ejecución (objeto de proceso es None).")

    def _listen_for_connections(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(5)
            print(f"[{self.port}] Escuchando en {self.host}:{self.port}...")
            while self.running:
                try:
                    conn, addr = s.accept()
                    conn.settimeout(600) # Timeout para la conexión de cliente
                    threading.Thread(target=self._handle_client_connection, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except OSError as e:
                    if self.running:
                        print(f"[{self.port}] Error de OSError al aceptar conexión: {e}")
                except Exception as e:
                    if self.running:
                        print(f"[{self.port}] Error al aceptar conexión: {e}")
        print(f"[{self.port}] Listener de conexiones finalizado.")

    def _command_listener(self):
        """
        Lee comandos de sys.stdin en un hilo separado y los pone en una cola.
        Permite que la GUI envíe comandos al nodo.
        """
        print(f"[{self.port}] Hilo de escucha de comandos iniciado.")
        # Configurar sys.stdin para no ser bloqueante si es posible,
        # o manejar el bloqueo de forma segura en un hilo.
        # En Windows, msvcrt.kbhit() y msvcrt.getch() podrían usarse para entrada no bloqueante.
        # Para sys.stdin.readline() en un subprocess Popen con PIPE, es naturalmente bloqueante
        # hasta que se escribe una línea, lo cual es lo que queremos.
        while self.running:
            try:
                # sys.stdin.readline() es bloqueante, pero en un hilo separado no bloquea el main loop.
                # Cuando la GUI escribe al stdin del subprocess, esta línea lo captura.
                command_line = sys.stdin.readline().strip() 
                if command_line:
                    self.command_queue.put(command_line)
                # No se necesita sleep si readline es bloqueante y esperamos entrada.
                # Si se usara un método no bloqueante o un timeout, sí.
                # time.sleep(0.1) # Pequeña pausa para no saturar la CPU si readline no fuera bloqueante.
            except Exception as e:
                print(f"[{self.port}] Error en el hilo de comandos: {e}")
                break
        print(f"[{self.port}] Hilo de escucha de comandos finalizado.")

    def _execute_internal_command(self, command):
        """Ejecuta comandos internos recibidos a través de la cola de comandos."""
        print(f"[{self.port}] Ejecutando comando interno: '{command}'")
        if command == "stop":
            self.stop()
        elif command == "start_xmrig":
            self.start_xmrig()
        elif command == "stop_xmrig":
            self.stop_xmrig()
        elif command == "peers":
            print(f"[{self.port}] Peers conectados: {list(self.peers)}")
        elif command == "request_pool_info":
            self._request_pool_info_from_peers() # Nuevo: Comando para solicitar info de pool
        else:
            print(f"[{self.port}] Comando desconocido: {command}")

    def _request_pool_info_from_peers(self):
        """Envía un mensaje POOL_INFO_REQUEST a todos los peers conectados."""
        print(f"[{self.port}] Solicitando información de pool a los peers...")
        with self.peers_lock:
            for peer_tuple in list(self.peers):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(5)
                        s.connect(peer_tuple)
                        self._send_message(s, MSG_TYPE_POOL_INFO_REQUEST, {"requester_port": self.port})
                        print(f"[{self.port}] Solicitud de pool enviada a {peer_tuple}")
                except Exception as e:
                    print(f"[{self.port}] No se pudo enviar solicitud de pool a {peer_tuple}: {e}")

    def run(self):
        # Iniciar listener de conexiones entrantes
        threading.Thread(target=self._listen_for_connections, daemon=True).start()

        # Iniciar hilo para escuchar comandos desde stdin (ej. de la GUI)
        # Esto es crucial para que la GUI pueda enviar comandos al nodo
        threading.Thread(target=self._command_listener, daemon=True).start()

        # Conectar a peers predefinidos (si aún no estamos conectados)
        for peer_host, peer_port in PEER_NODES:
            if (peer_host, peer_port) != (self.host, self.port): # No intentar conectar a sí mismo
                threading.Thread(target=self.connect_to_peer, args=(peer_host, peer_port), daemon=True).start()

        # Iniciar XMRig automáticamente al arrancar el nodo
        self.start_xmrig()

        # Bucle principal del nodo
        while self.running:
            # Procesar comandos de la cola (desde stdin)
            while not self.command_queue.empty():
                command = self.command_queue.get_nowait()
                self._execute_internal_command(command)
            
            # Aquí podrías añadir lógica adicional que el nodo necesite hacer periódicamente
            # Ej: Descubrimiento de nuevos peers, re-broadcasting de transacciones, etc.
            time.sleep(1) # Pequeña pausa para no saturar la CPU

        print(f"[{self.port}] Nodo en puerto {self.port} detenido.")

    def stop(self):
        print(f"[{self.port}] Señal de detención recibida. Deteniendo nodo...")
        self.running = False
        self.stop_xmrig() # Asegurarse de detener XMRig al cerrar

# --- Punto de entrada del script ---
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python p2p_miner_node.py <puerto> <direccion_billetera_monero>")
        sys.exit(1)

    port = int(sys.argv[1])
    wallet_address = sys.argv[2] # La dirección de la billetera es el segundo argumento

    # Filtrar PEER_NODES para no incluir el propio puerto
    # Esto es importante para que cada nodo solo intente conectar a otros, no a sí mismo
    PEER_NODES = [peer for peer in PEER_NODES if peer[1] != port]

    node = P2PNode(port, wallet_address)
    try:
        node.run()
    except KeyboardInterrupt:
        print(f"[{node.port}] Ctrl+C detectado. Deteniendo nodo limpiamente.")
        node.stop()
    except Exception as e:
        print(f"[{node.port}] Error inesperado en el nodo: {e}")
        node.stop()
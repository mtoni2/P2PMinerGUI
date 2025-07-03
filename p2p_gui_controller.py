# -*- coding: utf-8 -*-
# p2p_gui_controller.py
#
# P2P Miner GUI - Controlador principal de la interfaz gráfica de usuario.
# Copyright (c) 2025 Marcelo Tonini - Mendoza, Argentina
# Licencia: MIT
#
# Descripción: Este script maneja la lógica de la GUI para controlar los nodos mineros P2P
# y provee una interfaz para monitorear su estado y actividad.
#

import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
import subprocess
import os
import threading
import time
import queue
import requests
import psutil
import json

# --- Configuración ---
NODE_PORTS = [8000, 8001, 8002] # Puertos de tus nodos P2P
NODE_SCRIPT_PATH = "p2p_miner_node.py" # Asegúrate de que este script esté en la misma carpeta o especifica la ruta completa

# --- Configuración de Minería Monero (XMRig) para la GUI ---
# ¡IMPORTANTE! Reemplaza con TU dirección real de Monero
# La dirección que me pasaste antes: 4931PMmb9FE2LapSempngoBNYoVPxZdDt8C1bDScwhbNMcKzLw2guY5H1hxvNnRmfydJVKemEJQFdguxRK6J9hv3FHc8ABk
MONERO_WALLET_ADDRESS = "4931PMmb9FE2LapSempngoBNYoVPxZdDt8C1bDScwhbNMcKzLw2guY5H1hxvNnRmfydJVKemEJQFdguxRK6J9hv3FHc8ABk"
XMRIG_POOL_API_URL = f"https://supportxmr.com/api/miner/{MONERO_WALLET_ADDRESS}/stats"


class P2PGUIController:
    def __init__(self, master):
        self.master = master
        self.master.title("P2P Miner Node Controller")
        # Configurar la ventana para que se inicie maximizada si es Windows
        if os.name == 'nt':
            self.master.state('zoomed')

        # Diccionarios para almacenar procesos de nodos, hilos, etc.
        self.processes = {port: None for port in NODE_PORTS}
        self.output_queues = {port: queue.Queue() for port in NODE_PORTS}
        self.output_threads = {port: None for port in NODE_PORTS}
        self.text_scroll_enabled = {port: tk.BooleanVar(value=True) for port in NODE_PORTS}
        self.node_status_labels = {} # Para etiquetas de estado de nodo

        # DICCIONARIOS CRÍTICOS INICIALIZADOS
        self.text_areas = {} # Inicializa el diccionario para las áreas de texto de los logs
        self.node_processes = {port: None for port in NODE_PORTS} # Para almacenar los procesos de los nodos

        # Variables para las estadísticas del minero
        self.current_hashrate = tk.StringVar(value="N/A")
        self.total_paid = tk.StringVar(value="N/A")
        self.pending_balance = tk.StringVar(value="N/A")
        self.last_activity = tk.StringVar(value="N/A")

        # Esto DEBE ir antes de cualquier llamada que use self.text_areas
        self._create_widgets() # Llamando a _create_widgets con el guion bajo

        # Iniciar el bucle de actualización de las áreas de salida de los nodos
        # Ahora es seguro llamarla porque self.text_areas ya existe
        self.update_output_areas()

        # Iniciar la actualización de estadísticas del minero
        self.master.after(1000, self.update_pool_stats_gui) # <--- ¡ESTA ES LA LÍNEA CORREGIDA!

        # Configurar el protocolo para cerrar la ventana
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _create_widgets(self): # <--- DEFINICIÓN ORIGINAL CON GUION BAJO
        # Frame principal para los controles globales
        global_controls_frame = tk.Frame(self.master, bd=2, relief="groove", padx=10, pady=10)
        global_controls_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        tk.Label(global_controls_frame, text="Dirección de Billetera Monero:").pack(side=tk.LEFT, padx=5)
        self.wallet_address_entry = tk.Entry(global_controls_frame, width=60)
        self.wallet_address_entry.insert(0, MONERO_WALLET_ADDRESS) # Valor por defecto
        self.wallet_address_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.apply_wallet_button = tk.Button(global_controls_frame, text="Aplicar", command=self._apply_wallet_address)
        self.apply_wallet_button.pack(side=tk.LEFT, padx=5)
        
        # Botones globales
        global_buttons_frame = tk.Frame(self.master, bd=2, relief="groove", padx=10, pady=10)
        global_buttons_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        tk.Button(global_buttons_frame, text="Iniciar Todos", command=self.start_all_nodes).pack(side=tk.LEFT, padx=5)
        tk.Button(global_buttons_frame, text="Detener Todos", command=self.stop_all_nodes).pack(side=tk.LEFT, padx=5)
        tk.Button(global_buttons_frame, text="Solicitar Info de Pool (Peers)", command=self.request_pool_info_all).pack(side=tk.LEFT, padx=5)
        tk.Button(global_buttons_frame, text="Actualizar Stats de Pool (Local)", command=self.update_pool_stats_gui).pack(side=tk.LEFT, padx=5)

        # Frame para los nodos individuales
        nodes_frame = tk.Frame(self.master)
        nodes_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        for port in NODE_PORTS:
            node_frame = tk.LabelFrame(nodes_frame, text=f"Nodo P2P - Puerto {port}", bd=2, relief="ridge", padx=10, pady=10)
            node_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Controles del nodo
            controls_subframe = tk.Frame(node_frame)
            controls_subframe.pack(side=tk.TOP, fill=tk.X, pady=5)
            
            start_button = tk.Button(controls_subframe, text="Iniciar Nodo", command=lambda p=port: self.start_node(p))
            start_button.pack(side=tk.LEFT, padx=2)
            
            stop_button = tk.Button(controls_subframe, text="Detener Nodo", command=lambda p=port: self.stop_node(p))
            stop_button.pack(side=tk.LEFT, padx=2)

            send_command_button = tk.Button(controls_subframe, text="Enviar Comando (GUI)", command=lambda p=port: self.send_command_dialog(p))
            send_command_button.pack(side=tk.LEFT, padx=2)

            # Área de texto para la salida
            output_text = scrolledtext.ScrolledText(node_frame, width=50, height=20, wrap=tk.WORD, state=tk.DISABLED, bg="black", fg="lime green")
            output_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
            self.text_areas[port] = output_text # <--- ¡CORREGIDO! Usando self.text_areas aquí

        # Área de texto para estadísticas globales del pool (solo lectura)
        self.pool_stats_frame = tk.LabelFrame(self.master, text="Estadísticas Globales de Minería (SupportXMR)", bd=2, relief="ridge", padx=10, pady=10)
        self.pool_stats_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.pool_stats_text = scrolledtext.ScrolledText(self.pool_stats_frame, width=80, height=10, wrap=tk.WORD, state=tk.DISABLED, bg="black", fg="cyan")
        self.pool_stats_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Configurar el cierre de la ventana (Esta línea ya la tienes en __init__, puede ser redundante aquí)
        # self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _apply_wallet_address(self):
        new_address = self.wallet_address_entry.get().strip()
        if new_address and len(new_address) > 90: # Validación básica de longitud
            global MONERO_WALLET_ADDRESS
            MONERO_WALLET_ADDRESS = new_address
            global XMRIG_POOL_API_URL
            XMRIG_POOL_API_URL = f"https://supportxmr.com/api/miner/{MONERO_WALLET_ADDRESS}/stats"
            messagebox.showinfo("Dirección de Billetera", "Dirección de billetera actualizada. Los nuevos nodos usarán esta dirección.")
            self.update_pool_stats_gui() # Actualizar stats con la nueva dirección
        else:
            messagebox.showerror("Error", "Por favor, introduce una dirección de billetera Monero válida.")


    def start_node(self, port):
        # Usamos self.node_processes aquí, por eso es importante inicializarlo en __init__
        if self.node_processes[port] is None or self.node_processes[port].poll() is not None:
            wallet_address = self.wallet_address_entry.get().strip()
            if not wallet_address:
                messagebox.showerror("Error", "La dirección de la billetera no puede estar vacía.")
                return

            try:
                command = ["python", "-u", NODE_SCRIPT_PATH, str(port), wallet_address] # <--- ¡AÑADIDO EL '-u'!
                
                self.node_processes[port] = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1
                )
                messagebox.showinfo("Nodo Iniciado", f"Nodo P2P en puerto {port} iniciado.")
                print(f"[{port}] Proceso del nodo lanzado. PID: {self.node_processes[port].pid}")

                # Iniciar un hilo para leer la salida del proceso
                threading.Thread(target=self._read_output, args=(self.node_processes[port], port), daemon=True).start()

            except FileNotFoundError:
                messagebox.showerror("Error", f"El script del nodo '{NODE_SCRIPT_PATH}' no fue encontrado. Asegúrate de que la ruta sea correcta.")
            except Exception as e:
                messagebox.showerror("Error al Iniciar Nodo", f"No se pudo iniciar el nodo en puerto {port}: {e}")
        else:
            messagebox.showinfo("Estado del Nodo", f"El nodo en puerto {port} ya está en ejecución.")

    def stop_node(self, port):
        # Usamos self.node_processes aquí
        if self.node_processes[port] and self.node_processes[port].poll() is None:
            try:
                # Intentar enviar comando de stop interno al nodo si tiene _command_listener
                # (Asumiendo que _command_listener lee de stdin)
                self.send_node_command(port, "stop")
                
                # Darle un momento para que se detenga limpiamente
                self.node_processes[port].wait(timeout=5)
                
                if self.node_processes[port].poll() is None: # Si sigue vivo, forzar terminación
                    self.node_processes[port].terminate()
                    self.node_processes[port].wait(timeout=5)
                    if self.node_processes[port].poll() is None:
                        self.node_processes[port].kill()
                
                self.node_processes[port] = None
                messagebox.showinfo("Nodo Detenido", f"Nodo P2P en puerto {port} detenido.")
                print(f"[{port}] Proceso del nodo detenido.")
            except Exception as e:
                messagebox.showerror("Error al Detener Nodo", f"No se pudo detener el nodo en puerto {port}: {e}")
        else:
            messagebox.showinfo("Estado del Nodo", f"El nodo en puerto {port} no está en ejecución.")

    def start_all_nodes(self):
        for port in NODE_PORTS:
            self.start_node(port)

    def stop_all_nodes(self):
        for port in NODE_PORTS:
            self.stop_node(port)
            
    def _read_output(self, process, port):
        """Reads stdout and stderr from the process and puts it into the queue."""
        print(f"[{port}] DEBUG: Hilo de lectura de salida iniciado para nodo {port}.")

        # Read stdout
        for line in iter(process.stdout.readline, ''):
            print(f"[{port} GUI - STDOUT] {line.strip()}")
            self.output_queues[port].put(line)
        print(f"[{port}] DEBUG: STDOUT pipe cerrado para nodo {port}.")

        # Read stderr
        for line in iter(process.stderr.readline, ''):
            print(f"[{port} GUI - STDERR] {line.strip()}")
            self.output_queues[port].put(f"ERROR: {line}")
        print(f"[{port}] DEBUG: STDERR pipe cerrado para nodo {port}.")

        self.output_queues[port].put(f"\n--- Nodo {port} ha terminado. ---\n")
        print(f"[{port}] Hilo de lectura de salida para Nodo {port} finalizado.")


    def update_output_areas(self):
        """Actualiza las áreas de texto de la GUI con la salida de las colas."""
        for port in NODE_PORTS:
            text_area = self.text_areas[port]
            inserted_new_content = False
            
            # <--- ¡CORRECCIÓN CLAVE! Habilitar el área de texto para escribir
            text_area.config(state=tk.NORMAL) 

            while not self.output_queues[port].empty():
                line = self.output_queues[port].get_nowait()
                text_area.insert(tk.END, line) # Aquí se inserta el texto
                inserted_new_content = True
                print(f"[{port}] DEBUG: Sacando de la cola y mostrando en GUI: {line.strip()}")

            # <--- ¡CORRECCIÓN CLAVE! Deshabilitar el área de texto nuevamente después de escribir
            text_area.config(state=tk.DISABLED) 

            # Si se insertó contenido nuevo en el área de texto
            if inserted_new_content:
                if self.text_scroll_enabled[port].get():
                    text_area.see(tk.END) # Asegura que la vista se desplace al final
                text_area.update_idletasks() # Fuerza un refresco de la GUI para este widget
        
        # Vuelve a programar esta función para que se ejecute después de 100ms
        self.master.after(100, self.update_output_areas)

    def send_command_dialog(self, port):
        command = simpledialog.askstring("Enviar Comando", f"Introduce el comando para el Nodo {port}:",
                                         parent=self.master)
        if command:
            self.send_node_command(port, command)

    def send_node_command(self, port, command):
        """Envía un comando interno al proceso del nodo via stdin."""
        process = self.node_processes.get(port)
        if not process or process.poll() is not None:
            messagebox.showerror("Error de Envío", f"El Nodo {port} no está en ejecución.")
            return

        if process.stdin:
            try:
                process.stdin.write(command + '\n')
                process.stdin.flush()
                print(f"[{port}] Comando '{command}' enviado al nodo.")
            except Exception as e:
                messagebox.showerror("Error de Envío", f"No se pudo enviar el comando al Nodo {port}: {e}")
        else:
            messagebox.showerror("Error de Configuración", f"El Nodo {port} no está configurado para recibir comandos interactivos (stdin no conectado).")


    def request_pool_info_all(self):
        """Envía el comando 'request_pool_info' a todos los nodos activos."""
        for port in NODE_PORTS:
            if self.node_processes[port] and self.node_processes[port].poll() is None:
                self.send_node_command(port, "request_pool_info")
            else:
                print(f"[{port}] Nodo no activo para solicitar información de pool.")

    def update_pool_stats_gui(self):
        """Actualiza el área de texto con las estadísticas de minería del pool."""
        def fetch_stats():
            try:
                # Asegúrate de que MONERO_WALLET_ADDRESS esté actualizado si se cambió via GUI
                current_api_url = f"https://supportxmr.com/api/miner/{MONERO_WALLET_ADDRESS}/stats"
                response = requests.get(current_api_url)
                response.raise_for_status()
                stats = response.json()

                output = f"Última Actualización: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                output += f"Dirección de Billetera: {MONERO_WALLET_ADDRESS}\n"
                output += f"Hashrate Actual: {stats.get('hashrate', 'N/A')} H/s\n"
                output += f"Hashrate Promedio (última hora): {stats.get('avgHashrate', 'N/A')} H/s\n"
                output += f"Pagado Total: {stats.get('amtPaid', 'N/A')} XMR\n"
                output += f"Balance Pendiente: {stats.get('due', 'N/A')} XMR\n"
                output += f"Pagos Confirmados: {stats.get('paymentsTotal', 'N/A')}\n"
                output += f"Último Pago: {stats.get('lastPayment', 'N/A')}\n"
                output += f"Shares Válidos: {stats.get('validShares', 'N/A')}\n"
                output += f"Shares Inválidos: {stats.get('invalidShares', 'N/A')}\n"
                output += f"Workers Activos: {stats.get('workersOnline', 'N/A')}\n"

                self.master.after(0, lambda: self._update_pool_stats_text(output))

            except requests.exceptions.RequestException as e:
                error_msg = f"Error al obtener estadísticas del pool: {e}"
                self.master.after(0, lambda: self._update_pool_stats_text(error_msg))
                print(error_msg)
            except json.JSONDecodeError:
                error_msg = "Error al decodificar la respuesta JSON del pool."
                self.master.after(0, lambda: self._update_pool_stats_text(error_msg))
                print(error_msg)
            except Exception as e:
                error_msg = f"Error inesperado al actualizar stats del pool: {e}"
                self.master.after(0, lambda: self._update_pool_stats_text(error_msg))
                print(error_msg)

        threading.Thread(target=fetch_stats, daemon=True).start()

    def _update_pool_stats_text(self, text):
        self.pool_stats_text.config(state=tk.NORMAL)
        self.pool_stats_text.delete(1.0, tk.END)
        self.pool_stats_text.insert(tk.END, text)
        self.pool_stats_text.config(state=tk.DISABLED)

    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Estás seguro de que quieres salir? Se detendrán todos los nodos activos."):
            for port in NODE_PORTS:
                if self.node_processes[port] is not None and self.node_processes[port].poll() is None:
                    print(f"Deteniendo Nodo {port} antes de salir...")
                    self.stop_node(port)
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = P2PGUIController(root)
    # Ya tienes root.protocol en __init__, esta línea puede ser redundante o generar un doble registro
    # root.protocol("WM_DELETE_WINDOW", app.on_closing) 
    root.mainloop()
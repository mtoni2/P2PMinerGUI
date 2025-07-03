# P2P Miner GUI

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green?style=flat-square)
![XMRig](https://img.shields.io/badge/Miner-XMRig-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---
## Descripción del Proyecto

Este proyecto es una implementación de prueba de concepto de un **sistema de minería P2P distribuido** que permite a múltiples nodos colaborar en una red para coordinar y ejecutar tareas de minería de criptomonedas (como Monero) utilizando el software **XMRig**. Incluye una **interfaz gráfica de usuario (GUI)** para una gestión sencilla de los nodos.

El objetivo principal es demostrar cómo se pueden interconectar nodos mineros, facilitando el monitoreo y control centralizado de los procesos de minería distribuidos en una red. Cada nodo actúa como un par en la red P2P, capaz de descubrir otros nodos, compartir información y, lo más importante, gestionar su propio proceso de minería de XMRig de forma autónoma, con la consola de XMRig oculta para una experiencia de usuario más limpia.

---
## ¿Por Qué Usar P2P Miner GUI?

En un mundo donde la minería de criptomonedas puede parecer compleja y desalentadora, P2P Miner GUI se destaca por su **simplicidad y eficacia**. A diferencia de otras soluciones que a menudo requieren configuraciones intrincadas o luchan con una implementación inestable, este proyecto ofrece:

* **Facilidad de Uso:** Olvídate de las consolas confusas y los comandos complicados. Con una **interfaz gráfica intuitiva**, podrás iniciar, detener y monitorear múltiples nodos de minería en cuestión de segundos, incluso si eres nuevo en el tema.
* **Fiabilidad Comprobada:** Desarrollado con un enfoque en la estabilidad, cada nodo se integra de manera robusta con XMRig, el minero líder, asegurando un rendimiento consistente y resultados predecibles. Hemos probado a fondo su funcionamiento para garantizar que cumpla con su propósito sin frustraciones.
* **Transparencia P2P y Descentralización del Control:** La elección de una arquitectura **P2P (Peer-to-Peer)** no es arbitraria. Permite que cada nodo funcione de forma autónoma y se comunique directamente con otros, **evitando un único punto de fallo** y distribuyendo el monitoreo y la gestión de la red. Esto significa que no dependes de un servidor central para la orquestación, ofreciendo una solución más **resiliente y adaptativa** en entornos de minería distribuidos. Observa cómo tus nodos se interconectan y colaboran, dándote control y visión total sobre tu operación distribuida.
* **Enfoque en Resultados:** Si bien es una prueba de concepto, su diseño eficiente permite una gestión efectiva de tus recursos mineros, algo que a menudo se pierde en proyectos más complicados que no logran arrancar o mantener la operación.

P2P Miner GUI no solo es una herramienta; es una demostración práctica de cómo la minería distribuida puede ser accesible y efectiva. Te invitamos a probarlo y experimentar la diferencia.

---
## Características

* **Red P2P Distribuida**: Nodos que se conectan entre sí para formar una red.
* **Control Centralizado vía GUI**: Inicia, detiene y monitorea múltiples nodos mineros desde una única interfaz gráfica.
* **Integración con XMRig**: Utiliza el popular software de minería XMRig para la minería de Monero.
* **Ventanas de Consola Ocultas**: Los procesos de los nodos y de XMRig se ejecutan en segundo plano sin mostrar ventanas de consola.
* **Monitoreo Básico**: Rastrea el estado y la actividad de XMRig (hashrate, última actividad) reportada por los nodos.
* **Fácil de Usar**: Diseñado para una configuración y operación sencillas.

---
## Requisitos Previos

Antes de ejecutar el proyecto, asegurate de tener instalado:

* **Python 3.8+**: Podés descargarlo desde [python.org](https://www.python.org/downloads/).
* **pip**: El gestor de paquetes de Python (normalmente viene con Python).

---
## Instalación y Ejecución

Seguí estos pasos para poner en marcha el proyecto:

1.  **Clonar el Repositorio**:
    Abrí tu terminal o línea de comandos y ejecutá:
    ```bash
    git clone [https://github.com/mtoni2/P2PMinerGUI.git](https://github.com/mtoni2/P2PMinerGUI.git)
    cd P2PMinerGUI
    ```

2.  **Instalar Dependencias de Python**:
    Instalá las bibliotecas necesarias. Si no tenés `tkinter` preinstalado con tu Python, es posible que necesites instalarlo por separado o asegurarte de que tu instalación de Python lo incluya.
    ```bash
    pip install pyinstaller # Necesario si querés generar el ejecutable
    # Si tkinter no está incluido con tu Python, puede que necesites:
    # sudo apt-get install python3-tk # En sistemas basados en Debian/Ubuntu
    # brew install python-tk # En macOS con Homebrew
    ```
    *Nota: Este proyecto está diseñado para funcionar con el `xmrig.exe` incluido en la carpeta `xmrig/`.*

3.  **Ejecutar la GUI (Desde el Código Fuente)**:
    Para iniciar la interfaz gráfica de usuario:
    ```bash
    python p2p_gui_controller.py
    ```

---
## Uso de la GUI

1.  **Iniciar Nodos**:
    * En la GUI, introducí un número de puerto único para cada nodo (ej. 8000, 8001, 8002).
    * Introducí tu dirección de billetera de Monero.
    * Hacé clic en "Iniciar Nodo". El nodo se iniciará en segundo plano, y su salida se redirigirá a la ventana de log de la GUI.
2.  **Detener Nodos**:
    * Seleccioná el nodo deseado en la lista y hacé clic en "Detener Nodo".
3.  **Monitorear**:
    * El área de log mostrará la actividad de los nodos, incluyendo mensajes P2P y la salida parseada de XMRig (hashrate, etc.).
    * Podés solicitar información del pool a los peers para ver sus estados de minería.

---
## Estructura del Proyecto

P2PMinerGUI/
├── p2p_gui_controller.py   # Script principal de la interfaz gráfica de usuario.
├── p2p_miner_node.py       # Script que implementa la lógica de cada nodo P2P y controla XMRig.
├── xmrig/                  # Directorio que contiene el ejecutable de XMRig.
│   └── xmrig.exe           # Ejecutable de XMRig para Windows (versión compatible).
├── .gitignore              # Archivo para ignorar directorios y archivos generados por Git.
└── README.md               # Este archivo de documentación.

---
## Generar el Ejecutable (Opcional)

Si deseás crear un ejecutable autónomo de la aplicación (para Windows):

1.  Asegurate de tener `pyinstaller` instalado (`pip install pyinstaller`).
2.  Navegá a la raíz del proyecto en tu terminal.
3.  Ejecutá el siguiente comando para generar el ejecutable:
    ```bash
    pyinstaller --noconfirm --onedir --windowed ^
    --add-data "p2p_miner_node.py;." ^
    --add-data "xmrig;xmrig" ^
    p2p_gui_controller.py
    ```
4.  El ejecutable se encontrará en la carpeta `dist/P2PMinerGUI/`. Ejecutá `P2PMinerGUI.exe`.

---
## Notas Importantes y Advertencias

* Este proyecto es una **prueba de concepto** y no está diseñado para uso en producción. Puede tener limitaciones de rendimiento, seguridad y robustez.
* La configuración de `PEER_NODES` en `p2p_miner_node.py` está predefinida para `localhost` para facilitar las pruebas locales con múltiples nodos. Para una red real, deberías modificar esta lista con las direcciones IP y puertos de los nodos esperados.
* La minería de criptomonedas consume recursos significativos del sistema (CPU/GPU y energía). Asegurate de entender los riesgos y costos asociados.

---
## Contribuciones

¡Las contribuciones son bienvenidas! Si encontrás un error o tenés una mejora, no dudes en abrir un *issue* o enviar un *pull request*.

---
## Apoya el Proyecto

Si encontrás útil este proyecto y te gustaría apoyar su desarrollo continuo, ¡cualquier donación es bienvenida y muy apreciada!

Podés enviar Monero (XMR) a la siguiente dirección de billetera:

**Dirección XMR:** `4931PMmb9FE2LapSempngoBNYoVPxZdDt8C1bDScwhbNMcKzLw2guY5H1hxvNnRmfydJVKemEJQFdguxRK6J9hv3FHc8ABk`

¡Gracias por tu apoyo!

---
## Licencia

Este proyecto está bajo la Licencia MIT.

Copyright (c) 2025 Marcelo Tonini - Mendoza, Argentina (mtoni2)

Consultá el archivo `LICENSE` para más detalles.
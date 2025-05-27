import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext
import requests
import json
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from datetime import datetime
import shutil
from config import FLASK_SERVER_URL  # Importa do novo arquivo config.py
import mimetypes


# --- Variáveis Globais de Estado ---
LOGGED_IN_USER_ID = None
LOGGED_IN_USERNAME = None
LOGGED_IN_USER_EMAIL = None

# Variáveis globais para o monitoramento e destino local
observer = None
monitoring_path = None
local_archive_folder = None
# Conjunto para controlar arquivos em upload para evitar duplicidade
uploading_files = set()
stop_event = threading.Event()  # Evento para sinalizar a parada do observador

# --- Variáveis globais para os widgets Tkinter ---
# Serão inicializadas dentro de show_main_app_window()
root = None  # A janela principal do Tkinter
log_text = None
monitor_status_label = None
monitoring_path_label = None
archive_folder_label = None
start_monitor_button = None
stop_monitor_button = None
main_app_window = None  # Referência à janela principal do app
login_window = None  # Referência à janela de login


# --- Configurações Importantes ---
# Arquivo para armazenar configurações do desktop app (caminhos e último email)
CONFIG_FILE = "desktop_config.json"

# --- Funções de Configuração ---


def load_config():
    """Carrega as configurações do arquivo JSON."""
    global monitoring_path, local_archive_folder, LOGGED_IN_USER_EMAIL
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
                monitoring_path = config_data.get("monitoring_path")
                local_archive_folder = config_data.get("local_archive_folder")
                LOGGED_IN_USER_EMAIL = config_data.get("last_logged_in_email")
                return True
        except json.JSONDecodeError as e:
            add_log(
                f"Erro ao carregar configurações (JSON inválido): {e}", "error")
            return False
        except Exception as e:
            add_log(f"Erro inesperado ao carregar configurações: {e}", "error")
            return False
    return False


def save_config(monitoring_path_val=None, archive_folder_val=None, email=None):
    """Salva as configurações no arquivo JSON."""
    config_data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
        except json.JSONDecodeError:
            pass  # Ignora se o arquivo estiver corrompido, começará com um novo
        except Exception as e:
            add_log(f"Erro ao ler config existente para salvar: {e}", "error")

    # Atualiza apenas os valores passados
    if monitoring_path_val is not None:
        config_data["monitoring_path"] = monitoring_path_val
    if archive_folder_val is not None:
        config_data["local_archive_folder"] = archive_folder_val
    if email is not None:
        config_data["last_logged_in_email"] = email
    elif "last_logged_in_email" in config_data and email is None:  # Se email for explicitamente None, remove
        del config_data["last_logged_in_email"]

    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        add_log("Configurações salvas com sucesso.")
    except Exception as e:
        add_log(f"Erro ao salvar configurações: {e}", "error")


# --- Funções de Log e UI ---

def add_log(message, message_type="info"):
    """Adiciona uma mensagem ao log na UI com timestamp e cor."""
    if log_text:  # Garante que o widget log_text existe
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        log_text.config(state=tk.NORMAL)  # Habilita edição
        log_text.insert(tk.END, formatted_message,
                        message_type)  # Insere com tag
        log_text.see(tk.END)  # Rola para o final
        log_text.config(state=tk.DISABLED)  # Desabilita edição

        # Configura as tags de cor (precisa ser feito uma vez)
        log_text.tag_config("error", foreground="red")
        log_text.tag_config("success", foreground="green")
        log_text.tag_config("warning", foreground="orange")
        log_text.tag_config("info", foreground="black")  # Default
    else:
        # Fallback para console se log_text ainda não foi inicializado
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message_type.upper()}: {message}")


def update_monitor_status_ui():
    """Atualiza o texto e a cor do status do monitor na UI."""
    if monitor_status_label:  # Garante que o widget existe
        if observer and observer.is_alive():
            monitor_status_label.config(
                text="Status do Monitor: Ativo", fg="green")
            start_monitor_button.config(state=tk.DISABLED)
            stop_monitor_button.config(state=tk.NORMAL)
        else:
            monitor_status_label.config(
                text="Status do Monitor: Inativo", fg="red")
            start_monitor_button.config(state=tk.NORMAL)
            stop_monitor_button.config(state=tk.DISABLED)

    if monitoring_path_label:  # Garante que o widget existe
        path_text = monitoring_path if monitoring_path else "Não selecionada"
        monitoring_path_label.config(
            text=f"Pasta de Monitoramento: {path_text}")

    if archive_folder_label:  # Garante que o widget existe
        path_text = local_archive_folder if local_archive_folder else "Não selecionada"
        archive_folder_label.config(
            text=f"Pasta de Arquivamento Local: {path_text}")

    # Habilita o botão iniciar se os caminhos já estiverem configurados
    if start_monitor_button:  # Precisa verificar se o botão existe antes de configurar
        if monitoring_path and local_archive_folder and LOGGED_IN_USER_ID and LOGGED_IN_USER_EMAIL:
            start_monitor_button.config(state=tk.NORMAL)
        else:
            start_monitor_button.config(state=tk.DISABLED)


# --- Funções de Monitoramento de Arquivos ---

class FileEventHandler(FileSystemEventHandler):
    """Manipulador de eventos do sistema de arquivos para o Watchdog."""

    def on_created(self, event):
        if event.is_directory:
            return
        # Ignora arquivos temporários comuns do Windows e desktop.ini
        if "~$" in event.src_path or event.src_path.endswith(".tmp") or os.path.basename(event.src_path).lower() == "desktop.ini":
            return
        add_log(f"Detectado novo arquivo: {event.src_path}")
        self.process_file(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        # Ignora arquivos temporários comuns do Windows e desktop.ini
        if "~$" in event.dest_path or event.dest_path.endswith(".tmp") or os.path.basename(event.dest_path).lower() == "desktop.ini":
            return
        add_log(f"Detectado arquivo movido (renomeado): {event.dest_path}")
        self.process_file(event.dest_path)

    def process_file(self, file_path):
        """Processa um arquivo novo ou movido (renomeado) para upload."""
        if file_path in uploading_files:
            add_log(
                f"Arquivo {os.path.basename(file_path)} já está em processo de upload, ignorando.", "warning")
            return

        # Adiciona o arquivo ao conjunto de controle
        uploading_files.add(file_path)
        add_log(f"Iniciando processamento para {os.path.basename(file_path)}")

        # Inicia o upload em uma nova thread para não travar a UI
        threading.Thread(target=self._upload_and_archive_thread,
                         args=(file_path,)).start()

    def _upload_and_archive_thread(self, file_path):
        """Thread para upload de arquivo e arquivamento local."""
        try:
            # Espera um pouco para garantir que o arquivo foi totalmente escrito
            time.sleep(0.5)
            if not os.path.exists(file_path):
                add_log(
                    f"Erro: Arquivo não encontrado após espera: {file_path}", "error")
                return

            if not LOGGED_IN_USER_ID or not LOGGED_IN_USER_EMAIL:
                add_log(
                    "Erro: Nenhum usuário logado. Não é possível fazer upload.", "error")
                return

            add_log(
                f"Tentando upload de {os.path.basename(file_path)} para o servidor OpenPDF...")
            success = upload_file_to_server(
                file_path, LOGGED_IN_USER_ID, LOGGED_IN_USER_EMAIL)

            if success:
                add_log(
                    f"Upload de {os.path.basename(file_path)} concluído com sucesso!", "success")
                # Move para a pasta de arquivamento local
                archive_file_locally(file_path)
            else:
                add_log(
                    f"Falha no upload de {os.path.basename(file_path)}.", "error")
        except Exception as e:
            add_log(
                f"Erro inesperado ao processar arquivo {os.path.basename(file_path)}: {e}", "error")
        finally:
            # Remove o arquivo do conjunto de controle, independentemente do sucesso
            if file_path in uploading_files:
                uploading_files.remove(file_path)


def start_monitoring():
    """Inicia o monitoramento da pasta selecionada."""
    global observer, monitoring_path

    if not monitoring_path or not os.path.isdir(monitoring_path):
        add_log(
            "Por favor, selecione uma pasta de monitoramento válida primeiro.", "warning")
        messagebox.showwarning(
            "Configuração Necessária", "Por favor, selecione uma pasta de monitoramento válida antes de iniciar.")
        return

    if not local_archive_folder or not os.path.isdir(local_archive_folder):
        add_log(
            "Por favor, selecione uma pasta de arquivamento local válida primeiro.", "warning")
        messagebox.showwarning(
            "Configuração Necessária", "Por favor, selecione uma pasta de arquivamento local válida antes de iniciar.")
        return

    if observer and observer.is_alive():
        add_log("O monitor já está ativo.", "info")
        return

    if not LOGGED_IN_USER_ID or not LOGGED_IN_USER_EMAIL:
        add_log(
            "Nenhum usuário logado. Não é possível iniciar o monitoramento.", "error")
        messagebox.showerror(
            "Erro de Login", "É necessário fazer login antes de iniciar o monitoramento.")
        return

    add_log(f"Iniciando monitoramento da pasta: {monitoring_path}")
    event_handler = FileEventHandler()
    observer = Observer()
    observer.schedule(event_handler, monitoring_path, recursive=True)
    stop_event.clear()  # Garante que o evento está limpo
    observer.start()
    add_log("Monitoramento iniciado.", "success")
    update_monitor_status_ui()


def stop_monitoring():
    """Para o monitoramento da pasta."""
    global observer
    if observer:
        if observer.is_alive():
            add_log("Parando monitoramento...")
            observer.stop()
            observer.join(timeout=5)  # Espera a thread do observador terminar
            if observer.is_alive():
                add_log(
                    "A thread do monitoramento não terminou após 5 segundos. Pode haver um problema.", "error")
            else:
                add_log("Monitoramento parado com sucesso.", "success")
        observer = None  # Limpa a referência do observador
    else:
        add_log("Nenhum monitor ativo para parar.", "info")
    update_monitor_status_ui()

# --- Funções de Sincronização com o Servidor Flask ---


def upload_file_to_server(file_path, user_id, user_email):
    """Envia um arquivo para o servidor Flask."""
    if not os.path.exists(file_path):
        add_log(
            f"Erro de upload: Arquivo não existe no caminho: {file_path}", "error")
        return False

    file_name = os.path.basename(file_path)
    # Tenta determinar o caminho relativo se a pasta monitorada for um pai
    relative_path = os.path.relpath(
        os.path.dirname(file_path), monitoring_path)
    if relative_path == ".":  # Se o arquivo estiver na raiz da pasta monitorada
        relative_path = ""  # Envia como vazio para a rota Flask
    else:
        relative_path = relative_path.replace(
            "\\", "/")  # Garante barras corretas para URL

    try:
        with open(file_path, 'rb') as f:  # Abrir o arquivo no try-except para garantir que seja fechado
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_name)
            if not mime_type:
                mime_type = 'application/octet-stream'  # fallback genérico

            files = {'file': (file_name, open(file_path, 'rb'), mime_type)}
            data = {'email': user_email}
            response = requests.post(
                f"{FLASK_SERVER_URL}/upload_desktop",
                files={"file": (file_name, open(file_path, "rb"), mime_type)},
                data={"email": user_email}
            )
            response.raise_for_status()  # Lança HTTPError para status de erro (4xx ou 5xx)

            try:
                response_data = response.json()
            except Exception:
                add_log(
                    f"Erro ao enviar arquivo para o servidor: {response.text}", "error")
                return False

            if response_data.get('success'):
                add_log(
                    f"Servidor retornou: {response_data.get('message', 'Upload bem-sucedido.')}", "success")
                return True
            else:
                add_log(
                    f"Erro no servidor: {response_data.get('message', 'Upload falhou.')}", "error")
                return False
    except FileNotFoundError:
        add_log(
            f"Erro de upload: Arquivo não encontrado ao tentar abrir: {file_path}", "error")
        return False
    except requests.exceptions.ConnectionError:
        add_log(
            f"Erro de conexão: Não foi possível conectar ao servidor Flask em {FLASK_SERVER_URL}. Verifique se o servidor está rodando.", "error")
        messagebox.showerror(
            "Erro de Conexão", f"Não foi possível conectar ao servidor Flask em {FLASK_SERVER_URL}. Verifique se ele está rodando.")
        return False
    except requests.exceptions.Timeout:
        add_log(
            "Erro de timeout: O servidor Flask demorou muito para responder.", "error")
        messagebox.showerror(
            "Erro de Timeout", "O servidor Flask demorou muito para responder.")
        return False
    except requests.exceptions.RequestException as e:
        add_log(f"Erro ao enviar arquivo para o servidor: {e}", "error")
        messagebox.showerror(
            "Erro de Upload", f"Ocorreu um erro ao enviar o arquivo: {e}")
        return False
    except json.JSONDecodeError:
        add_log(
            f"Erro de JSON: Resposta inválida do servidor. Status: {response.status_code if 'response' in locals() else 'N/A'}, Conteúdo: {response.text if 'response' in locals() else 'N/A'}", "error")
        messagebox.showerror("Erro do Servidor",
                             "O servidor enviou uma resposta inválida.")
        return False
    except Exception as e:  # Captura qualquer outra exceção inesperada
        add_log(f"Erro inesperado no upload: {e}", "error")
        messagebox.showerror(
            "Erro Inesperado", f"Ocorreu um erro inesperado durante o upload: {e}")
        return False


def archive_file_locally(file_path):
    """Move o arquivo para a pasta de arquivamento local."""
    if not local_archive_folder:
        add_log("Erro: Pasta de arquivamento local não selecionada.", "error")
        return False

    try:
        os.makedirs(local_archive_folder, exist_ok=True)
        dest_path = os.path.join(local_archive_folder,
                                 os.path.basename(file_path))

        # Evita sobrescrever se o arquivo já existir no destino
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(dest_path)
            counter = 1
            while os.path.exists(f"{base}_{counter}{ext}"):
                counter += 1
            dest_path = f"{base}_{counter}{ext}"

        shutil.move(file_path, dest_path)
        add_log(
            f"Arquivo '{os.path.basename(file_path)}' movido para a pasta de arquivamento local: {dest_path}", "info")
        return True
    except Exception as e:
        add_log(f"Erro ao mover arquivo para arquivamento local: {e}", "error")
        messagebox.showerror(
            "Erro de Arquivamento", f"Não foi possível arquivar o arquivo localmente: {e}")
        return False

# --- Funções da Interface de Login ---


def show_login_window():
    """Exibe a janela de login."""
    global login_window, LOGGED_IN_USER_EMAIL

    if main_app_window and main_app_window.winfo_exists():
        main_app_window.withdraw()  # Esconde a janela principal se estiver visível

    if login_window and login_window.winfo_exists():
        login_window.deiconify()  # Revela se já existe
        return

    login_window = tk.Toplevel(root)
    login_window.title("Login OpenPDF Desktop")
    login_window.geometry("400x300")
    login_window.resizable(False, False)
    # Garante que fechar a janela de login fecha todo o aplicativo
    login_window.protocol("WM_DELETE_WINDOW", root.quit)

    tk.Label(login_window, text="Login de Usuário",
             font=("Arial", 16)).pack(pady=10)

    tk.Label(login_window, text="Email:").pack()
    email_entry = tk.Entry(login_window, width=40)
    email_entry.pack(pady=5)
    if LOGGED_IN_USER_EMAIL:  # Preenche com o último email logado
        email_entry.insert(0, LOGGED_IN_USER_EMAIL)

    tk.Label(login_window, text="Senha:").pack()
    password_entry = tk.Entry(login_window, show="*", width=40)
    password_entry.pack(pady=5)

    def attempt_login():
        email = email_entry.get()
        password = password_entry.get()
        if not email or not password:
            messagebox.showerror(
                "Erro de Login", "Por favor, preencha todos os campos.")
            return

        response = send_login_request(email, password)
        if response and response.get('success'):
            global LOGGED_IN_USER_ID, LOGGED_IN_USERNAME, LOGGED_IN_USER_EMAIL
            # Ajuste conforme o que seu backend retorna!
            user = response.get('user')
            if user:
                LOGGED_IN_USER_ID = user.get('id')
                LOGGED_IN_USERNAME = user.get('username')
            else:
                LOGGED_IN_USER_ID = response.get('user_id')
                LOGGED_IN_USERNAME = response.get('username')
            LOGGED_IN_USER_EMAIL = email  # Salva o email que foi usado para login
            add_log(f"Login bem-sucedido como {LOGGED_IN_USERNAME}", "success")
            save_config(email=email)  # Salva o email do último login
            login_window.destroy()  # Fecha a janela de login
            show_main_app_window()  # Abre a janela principal
        else:
            add_log(
                f"Falha no login: {response.get('message', 'Erro desconhecido.')}", "error")
            messagebox.showerror("Erro de Login", response.get(
                'message', 'Falha ao conectar ou erro no servidor.'))

    tk.Button(login_window, text="Login", command=attempt_login).pack(pady=10)


def send_login_request(email, password):
    """Envia requisição de login para o servidor Flask."""
    try:
        response = requests.post(
            FLASK_SERVER_URL + "/login_desktop",
            json={"email": email, "password": password}
        )
        response.raise_for_status()  # Lança HTTPError para status de erro (4xx ou 5xx)
        return response.json()
    except requests.exceptions.ConnectionError:
        add_log(
            f"Erro de conexão: Não foi possível conectar ao servidor Flask em {FLASK_SERVER_URL}. Verifique se o servidor está rodando.", "error")
        return {"success": False, "message": "Não foi possível conectar ao servidor."}
    except requests.exceptions.Timeout:
        add_log(
            "Erro de timeout: O servidor Flask demorou muito para responder.", "error")
        return {"success": False, "message": "O servidor demorou muito para responder."}
    except requests.exceptions.RequestException as e:
        add_log(f"Erro durante a requisição de login: {e}", "error")
        return {"success": False, "message": f"Erro na requisição: {e}"}
    except json.JSONDecodeError:
        add_log(
            f"Erro de JSON: Resposta inválida do servidor para login. Status: {response.status_code if 'response' in locals() else 'N/A'}, Conteúdo: {response.text if 'response' in locals() else 'N/A'}", "error")
        return {"success": False, "message": "Resposta inválida do servidor."}
    except Exception as e:  # Captura qualquer outra exceção inesperada
        add_log(f"Erro inesperado no login: {e}", "error")
        return {"success": False, "message": f"Ocorreu um erro inesperado: {e}"}

# --- Funções da Interface Principal (App) ---


def choose_monitoring_path():
    """Abre um diálogo para selecionar a pasta de monitoramento."""
    global monitoring_path
    selected_path = filedialog.askdirectory()
    if selected_path:
        monitoring_path = selected_path
        save_config(monitoring_path_val=monitoring_path)
        update_monitor_status_ui()
        add_log(f"Pasta de monitoramento selecionada: {monitoring_path}")
    else:
        add_log("Seleção de pasta de monitoramento cancelada.", "info")


def choose_archive_folder():
    """Abre um diálogo para selecionar a pasta de arquivamento local."""
    global local_archive_folder
    selected_path = filedialog.askdirectory()
    if selected_path:
        local_archive_folder = selected_path
        save_config(archive_folder_val=local_archive_folder)
        update_monitor_status_ui()
        add_log(
            f"Pasta de arquivamento local selecionada: {local_archive_folder}")
    else:
        add_log("Seleção de pasta de arquivamento local cancelada.", "info")


def show_main_app_window():
    """Exibe a janela principal da aplicação."""
    global main_app_window, log_text, monitor_status_label, \
        monitoring_path_label, archive_folder_label, \
        start_monitor_button, stop_monitor_button

    if login_window and login_window.winfo_exists():
        login_window.withdraw()  # Esconde a janela de login se estiver visível

    if main_app_window and main_app_window.winfo_exists():
        main_app_window.deiconify()  # Revela se já existia
        update_monitor_status_ui()  # Atualiza o estado
        return  # Já está mostrando

    main_app_window = tk.Toplevel(root)
    main_app_window.title("OpenPDF Desktop Monitor")
    main_app_window.geometry("700x550")
    main_app_window.resizable(False, False)
    main_app_window.protocol(
        "WM_DELETE_WINDOW", lambda: on_closing_main_app(main_app_window))

    # Frame principal
    main_frame = tk.Frame(main_app_window, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Título
    # AQUI AGORA LOGGED_IN_USERNAME TERÁ UM VALOR VÁLIDO
    tk.Label(main_frame, text=f"Bem-vindo(a), {LOGGED_IN_USERNAME}!", font=(
        "Arial", 14, "bold")).pack(pady=5)
    tk.Label(main_frame, text="Monitor de Upload de Documentos",
             font=("Arial", 12)).pack(pady=5)

    # Status do Monitor
    monitor_status_label = tk.Label(
        main_frame, text="Status do Monitor: N/A", font=("Arial", 10, "bold"))
    monitor_status_label.pack(pady=5)

    # Caminhos selecionados
    monitoring_path_label = tk.Label(
        main_frame, text="Pasta de Monitoramento: N/A", wraplength=600)
    monitoring_path_label.pack(pady=2)
    archive_folder_label = tk.Label(
        main_frame, text="Pasta de Arquivamento Local: N/A", wraplength=600)
    archive_folder_label.pack(pady=2)

    # Botões de Seleção de Pasta
    path_buttons_frame = tk.Frame(main_frame)
    path_buttons_frame.pack(pady=10)
    tk.Button(path_buttons_frame, text="Selecionar Pasta de Monitoramento",
              command=choose_monitoring_path).pack(side=tk.LEFT, padx=5)
    tk.Button(path_buttons_frame, text="Selecionar Pasta de Arquivamento",
              command=choose_archive_folder).pack(side=tk.LEFT, padx=5)

    # Botões de Controle do Monitor
    monitor_buttons_frame = tk.Frame(main_frame)
    monitor_buttons_frame.pack(pady=10)
    start_monitor_button = tk.Button(
        monitor_buttons_frame, text="Iniciar Monitoramento", command=start_monitoring, state=tk.DISABLED)
    start_monitor_button.pack(side=tk.LEFT, padx=5)
    stop_monitor_button = tk.Button(
        monitor_buttons_frame, text="Parar Monitoramento", command=stop_monitoring, state=tk.DISABLED)
    stop_monitor_button.pack(side=tk.LEFT, padx=5)

    # Log de Atividade
    tk.Label(main_frame, text="Log de Atividade:", font=(
        "Arial", 10, "bold")).pack(pady=5, anchor=tk.W)
    log_text = scrolledtext.ScrolledText(
        main_frame, width=80, height=15, state=tk.DISABLED, wrap=tk.WORD)
    log_text.pack(pady=5, fill=tk.BOTH, expand=True)

    # Botões de Ação
    action_buttons_frame = tk.Frame(main_frame)
    action_buttons_frame.pack(pady=10)
    tk.Button(action_buttons_frame, text="Logout", command=lambda: logout_and_close(
        main_app_window)).pack(side=tk.LEFT, padx=5)
    tk.Button(action_buttons_frame, text="Sair do Aplicativo",
              command=lambda: on_closing_main_app(main_app_window)).pack(side=tk.LEFT, padx=5)

    # Atualiza o status inicial da UI
    update_monitor_status_ui()
    # Se os caminhos já estiverem configurados e o usuário logado, habilita o botão Iniciar
    if monitoring_path and local_archive_folder and LOGGED_IN_USER_ID and LOGGED_IN_USER_EMAIL:
        start_monitor_button.config(state=tk.NORMAL)
    else:
        add_log(
            "Selecione as pastas de monitoramento e arquivamento para iniciar o monitor.", "info")


def logout_and_close(window):
    """Faz logout, para o monitoramento e volta para a tela de login."""
    global LOGGED_IN_USER_ID, LOGGED_IN_USERNAME, LOGGED_IN_USER_EMAIL
    LOGGED_IN_USER_ID = None
    LOGGED_IN_USERNAME = None
    LOGGED_IN_USER_EMAIL = None
    save_config(email=None)  # Limpa o último email logado
    stop_monitoring()  # Para o monitoramento
    window.destroy()
    show_login_window()  # Volta para a tela de login


def on_closing_main_app(window):
    """Função chamada ao tentar fechar a janela principal."""
    if messagebox.askokcancel("Sair", "Tem certeza que deseja sair do aplicativo? O monitoramento será parado."):
        stop_monitoring()
        window.destroy()
        root.quit()  # Garante que o aplicativo Tkinter principal seja encerrado


# --- Início do Aplicativo ---
root = tk.Tk()
root.withdraw()  # Esconde a janela raiz (principal) para mostrar apenas as de login/main app

# Carrega as configurações ao iniciar (inclui o último email logado)
load_config()

# Sempre inicia na janela de login.
# A janela principal só será exibida após um login bem-sucedido.
add_log("Iniciando o aplicativo OpenPDF Desktop. Por favor, faça login.", "info")
show_login_window()


def login_user(email, password):
    # Mude para a nova rota
    login_url = f"{FLASK_SERVER_URL}/login_desktop"


# Inicia o loop principal do Tkinter
root.mainloop()

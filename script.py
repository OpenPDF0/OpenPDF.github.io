# script.py
import threading
import time
import os
import shutil
import json
from flask import Flask, render_template, send_from_directory, request, redirect, session, url_for, flash, Blueprint, jsonify
import auth  # Importa o módulo auth.py
from flask_dance.contrib.google import make_google_blueprint, google
# Importar mover_para_lixeira e outras funções/variáveis do seu módulo lixeira.py
# Importar funções necessárias da lixeira
from lixeira import lixeira_bp, mover_para_lixeira, limpar_lixeira_automaticamente, PASTA_LIXEIRA_BASE
import requests
from werkzeug.utils import secure_filename
from datetime import datetime
import bcrypt  # Adicionar esta importação se você for verificar senhas aqui, mas o auth.py já faz isso
# Importa do config.py
from config import SECRET_KEY, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, FLASK_SERVER_URL

# Caminhos base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Pasta base para todos os usuários
PASTA_ARQUIVOS_BASE = os.path.join(BASE_DIR, 'arquivos_usuarios')

# Cria a pasta base para arquivos de usuários se não existir
os.makedirs(PASTA_ARQUIVOS_BASE, exist_ok=True)

# Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = SECRET_KEY  # Usando a chave do config.py

# Configuração do Google OAuth
google_bp = make_google_blueprint(
    client_id=GOOGLE_OAUTH_CLIENT_ID,  # Usando do config.py
    client_secret=GOOGLE_OAUTH_CLIENT_SECRET,  # Usando do config.py
    scope=["profile", "email"],
)
# Ajustado o url_prefix se necessário
app.register_blueprint(google_bp, url_prefix="/login")

# Blueprint da lixeira
# Registro do blueprint da lixeira
app.register_blueprint(lixeira_bp, url_prefix='/lixeira')


# Variável para o thread de limpeza da lixeira
lixeira_cleaner_thread = None

# Rotas da aplicação


@app.route('/')
def index():
    if 'usuario' not in session:
        flash('Por favor, faça login para acessar seus arquivos.', 'danger')
        return redirect(url_for('login'))

    user_email = session['email']
    user_folder_name = secure_filename(user_email.split('@')[0])
    # Pega o caminho da subpasta, se houver
    current_folder_path = request.args.get('path', '')

    user_full_path = os.path.join(PASTA_ARQUIVOS_BASE, user_folder_name)
    current_display_path = os.path.join(user_full_path, current_folder_path)

    # Garante que a pasta do usuário exista
    os.makedirs(current_display_path, exist_ok=True)

    files = []
    folders = []
    try:
        for item in os.listdir(current_display_path):
            item_path = os.path.join(current_display_path, item)
            if os.path.isfile(item_path):
                # Gera o full_relative_file_path para o HTML
                # Remove o PASTA_ARQUIVOS_BASE para obter o caminho relativo ao usuário
                full_relative_file_path = os.path.relpath(
                    item_path, user_full_path).replace('\\', '/')
                files.append({
                    'filename': item,
                    'full_path': full_relative_file_path  # Caminho relativo ao usuário
                })
            elif os.path.isdir(item_path):
                # Para pastas, queremos o nome da pasta relativa à pasta atual
                relative_folder_name = os.path.relpath(
                    item_path, current_display_path)
                folders.append(relative_folder_name)
    except Exception as e:
        flash(f"Erro ao listar arquivos: {e}", 'danger')
        print(
            f"[ERRO] Erro ao listar arquivos para {user_email} em {current_display_path}: {e}")
        files = []
        folders = []

    # O 'current_folder_path' aqui é o caminho da pasta atual que está sendo exibida.
    # O 'query_busca' é usado para preencher o campo de busca se a página foi resultado de uma busca.
    # O 'search_active' indica se a página está exibindo resultados de busca.
    # Esses parâmetros são importantes para o template index.html.
    return render_template('index.html', arquivos=files, pastas=folders,
                           current_folder_path=current_folder_path,
                           search_active=False,  # Não é uma busca ativa ao carregar a index normalmente
                           query_busca='')  # Limpa o campo de busca ao carregar a index normalmente


ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'usuario' not in session:
        flash('Por favor, faça login para fazer upload.', 'danger')
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('Nenhum arquivo enviado.', 'danger')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('index'))

    # Verifica se o arquivo é permitido
    if not allowed_file(file.filename):
        flash('Tipo de arquivo não permitido.', 'danger')
        return redirect(url_for('index'))

    # current_folder_path é o caminho relativo onde o usuário está no frontend
    current_folder_path = request.form.get('current_folder_path', '')
    user_email = session['email']
    user_folder_name = secure_filename(user_email.split('@')[0])

    # Cria o caminho completo para a pasta de destino do usuário no servidor
    target_folder = os.path.join(PASTA_ARQUIVOS_BASE, user_folder_name)
    if current_folder_path:  # Se houver uma subpasta, adiciona
        target_folder = os.path.join(target_folder, current_folder_path)

    os.makedirs(target_folder, exist_ok=True)  # Garante que a pasta exista

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(target_folder, filename)

        # Previne sobrescrita: se o arquivo já existe, adiciona um contador
        base, extension = os.path.splitext(filename)
        counter = 1
        original_file_path = file_path  # Guarda o path original para referência
        while os.path.exists(file_path):
            file_path = os.path.join(
                target_folder, f"{base}_{counter}{extension}")
            counter += 1

        try:
            file.save(file_path)
            flash(
                f'Arquivo "{os.path.basename(file_path)}" enviado com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao salvar arquivo: {e}', 'danger')
            print(
                f"[ERRO] Erro ao salvar arquivo {filename} para {user_email}: {e}")
        return redirect(url_for('index', path=current_folder_path))
    return redirect(url_for('index', path=current_folder_path))





@app.route('/download/<path:filename>')
def download_file(filename):
    if 'usuario' not in session:
        flash('Por favor, faça login para baixar arquivos.', 'danger')
        return redirect(url_for('login'))

    user_email = session['email']
    user_folder_name = secure_filename(user_email.split('@')[0])

    # Construindo o caminho completo do arquivo a partir da pasta base do usuário
    # filename aqui é o 'full_path' que enviamos do HTML (e.g., 'subpasta/arquivo.pdf')
    file_full_path = os.path.join(
        PASTA_ARQUIVOS_BASE, user_folder_name, filename)

    # Garante que o arquivo está dentro da pasta do usuário e não tenta sair
    # Isso é uma medida de segurança importante
    absolute_user_path = os.path.abspath(
        os.path.join(PASTA_ARQUIVOS_BASE, user_folder_name))
    absolute_file_path = os.path.abspath(file_full_path)

    if not absolute_file_path.startswith(absolute_user_path):
        flash('Acesso negado: Tentativa de acessar arquivo fora da sua pasta.', 'danger')
        return redirect(url_for('index'))

    if os.path.exists(file_full_path) and os.path.isfile(file_full_path):
        # O dirname(file_full_path) será o diretório de onde o arquivo será enviado
        # O basename(file_full_path) será o nome do arquivo para download
        return send_from_directory(os.path.dirname(file_full_path), os.path.basename(file_full_path), as_attachment=True)
    else:
        flash('Arquivo não encontrado.', 'danger')
        return redirect(url_for('index'))


@app.route('/renomear_arquivo/<path:filename>', methods=['POST'])
def renomear_arquivo(filename):
    if 'usuario' not in session:
        flash('Por favor, faça login para renomear.', 'danger')
        return redirect(url_for('login'))

    novo_nome = request.form.get('novo_nome')
    if not novo_nome:
        flash('O novo nome não pode estar vazio.', 'danger')
        return redirect(url_for('index'))

    user_email = session['email']
    user_folder_name = secure_filename(user_email.split('@')[0])

    # Caminho completo para o arquivo antigo
    old_file_full_path = os.path.join(
        PASTA_ARQUIVOS_BASE, user_folder_name, filename)

    # Extrai a extensão original
    _, ext = os.path.splitext(old_file_full_path)

    # Garante que o novo nome não contém caracteres inválidos e adiciona a extensão original se não houver
    new_filename_secure = secure_filename(novo_nome)
    if not new_filename_secure.lower().endswith(ext.lower()):
        new_filename_secure += ext

    # Determina a pasta atual para o redirect
    current_folder_path = os.path.dirname(filename)

    # Caminho completo para o novo arquivo (na mesma pasta do antigo)
    new_file_full_path = os.path.join(os.path.dirname(
        old_file_full_path), new_filename_secure)

    # Verifica se o arquivo existe
    if not os.path.exists(old_file_full_path):
        flash('Arquivo original não encontrado para renomear.', 'danger')
        return redirect(url_for('index', path=current_folder_path))

    try:
        os.rename(old_file_full_path, new_file_full_path)
        flash(
            f'Arquivo renomeado para "{new_filename_secure}" com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao renomear arquivo: {e}', 'danger')
        print(
            f"[ERRO] Erro ao renomear {filename} para {new_filename_secure}: {e}")
    return redirect(url_for('index', path=current_folder_path))


@app.route('/mover_para_lixeira/<path:filename>')
def mover_para_lixeira_route(filename):
    if 'usuario' not in session:
        flash('Por favor, faça login para mover arquivos para a lixeira.', 'danger')
        return redirect(url_for('login'))

    user_email = session['email']
    user_folder_name = secure_filename(user_email.split('@')[0])

    # Caminho completo do arquivo original no sistema
    original_filepath_full = os.path.join(
        PASTA_ARQUIVOS_BASE, user_folder_name, filename)

    # Extrai a pasta relativa do arquivo (ex: 'docs/financeiro' se filename for 'docs/financeiro/relatorio.pdf')
    original_relative_folder = os.path.dirname(filename).replace('\\', '/')

    if mover_para_lixeira(user_email, original_filepath_full, original_relative_folder):
        flash(
            f'Arquivo "{os.path.basename(filename)}" movido para a lixeira!', 'success')
    else:
        flash('Erro ao mover arquivo para a lixeira.', 'danger')

    # Redireciona para a pasta atual após a operação
    current_folder_path_for_redirect = os.path.dirname(filename)
    return redirect(url_for('index', path=current_folder_path_for_redirect))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['password']

        user_info_or_error = auth.verificar_usuario(email, senha)

        if isinstance(user_info_or_error, dict):  # Login bem-sucedido
            session['usuario'] = user_info_or_error['username']
            session['email'] = email
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:  # Falha no login (mensagem de erro)
            flash(user_info_or_error, 'danger')  # Exibe o mensagem de erro
    return render_template('login.html')


@app.route('/login_desktop', methods=['POST'])
def login_desktop():
    """
    Rota para o aplicativo desktop fazer login.
    Não usa sessão Flask, apenas autentica e retorna os dados do usuário.
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "Email e senha são obrigatórios."}), 400

    user_info_or_error = auth.verificar_usuario(email, password)

    if isinstance(user_info_or_error, dict):  # Login bem-sucedido
        return jsonify({
            "success": True,
            "message": "Login bem-sucedido!",
            "user": {
                "id": user_info_or_error['id'],
                "username": user_info_or_error['username'],
                "email": email
            }
        }), 200
    else:  # Falha no login (mensagem de erro)
        return jsonify({"success": False, "message": user_info_or_error}), 401


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('As senhas não coincidem.', 'danger')
            return redirect(url_for('cadastro'))

        response = auth.cadastrar_usuario(username, email, password)

        if isinstance(response, dict) and response.get('success'):
            flash(response['message'], 'success')
            return redirect(url_for('login'))
        else:
            # Exibe a mensagem de erro retornada por cadastrar_usuario
            flash(response, 'danger')
    return render_template('cadastro.html')


@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('email', None)
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))


@app.route("/google_login_callback")
def google_login_callback():
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    assert resp.ok, resp.text
    user_info = resp.json()
    # ... faça login/cadastro do usuário ...
    return redirect(url_for("index"))






# <-- Adicionado endpoint='buscar' aqui
@app.route('/search', methods=['GET'], endpoint='buscar')
def search_files():
    if 'usuario' not in session:
        flash('Por favor, faça login para pesquisar.', 'danger')
        return redirect(url_for('login'))

    search_query = request.args.get('query', '').strip()

    if not search_query:
        flash('Por favor, insira um termo de busca.', 'warning')
        return redirect(url_for('index'))

    user_email = session['email']
    user_folder_name = secure_filename(user_email.split('@')[0])
    user_full_path = os.path.join(PASTA_ARQUIVOS_BASE, user_folder_name)

    found_files = []
    found_folders = []

    for root_dir, dirnames, filenames in os.walk(user_full_path):
        # Garante que os caminhos são relativos à pasta do usuário para exibição
        relative_to_user_base = os.path.relpath(root_dir, user_full_path)
        if relative_to_user_base == '.':
            relative_to_user_base = ''  # Para a raiz da pasta do usuário

        # Busca por pastas
        for folder_name in dirnames:
            if search_query.lower() in folder_name.lower():
                # Adiciona o caminho completo da pasta relativa ao usuário
                full_relative_folder_path = os.path.join(
                    relative_to_user_base, folder_name).replace('\\', '/')
                found_folders.append(full_relative_folder_path)

        # Busca por arquivos
        for file_name in filenames:
            if search_query.lower() in file_name.lower():
                # Adiciona o caminho completo do arquivo relativo ao usuário
                full_relative_file_path = os.path.join(
                    relative_to_user_base, file_name).replace('\\', '/')
                found_files.append({
                    'filename': file_name,
                    'full_path': full_relative_file_path
                })

    # Renderiza o template index.html com os resultados da busca
    # Passamos 'search_active' para o template saber que está mostrando resultados de busca
    # e 'search_query' para exibir o termo buscado.
    # current_folder_path é vazio porque a busca é global, não em uma pasta específica.
    return render_template('index.html', arquivos=found_files, pastas=found_folders,
                           current_folder_path='',
                           search_active=True, search_query=search_query)


# Função para iniciar a limpeza automática da lixeira em um thread separado
# Limpa a cada 24 horas por padrão
def start_lixeira_cleaner(interval_seconds=24 * 60 * 60):
    print("Iniciando limpeza da lixeira em segundo plano...")
    # Você pode passar o intervalo diretamente para a função limpar_lixeira_automaticamente
    # Ou passar uma flag para ela parar de rodar, se for o caso de desligar o servidor
    limpar_lixeira_automaticamente(interval_seconds)


@app.route('/upload_desktop', methods=['POST'])
def upload_desktop():
    email = request.form.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Email não informado.'}), 400

    user_folder_name = secure_filename(email.split('@')[0])
    target_folder = os.path.join(PASTA_ARQUIVOS_BASE, user_folder_name)
    os.makedirs(target_folder, exist_ok=True)

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Tipo de arquivo não permitido.'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(target_folder, filename)
    base, extension = os.path.splitext(filename)
    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(target_folder, f"{base}_{counter}{extension}")
        counter += 1

    try:
        file.save(file_path)
        return jsonify({'success': True, 'message': 'Arquivo enviado com sucesso!'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao salvar arquivo: {e}'}), 500


@app.route('/deletar_arquivo/<path:filename>')
def deletar_arquivo(filename):
    if 'usuario' not in session:
        flash('Por favor, faça login para deletar arquivos.', 'danger')
        return redirect(url_for('login'))

    user_email = session['email']
    user_folder_name = secure_filename(user_email.split('@')[0])
    file_full_path = os.path.join(
        PASTA_ARQUIVOS_BASE, user_folder_name, filename)

    # Segurança: impede acesso fora da pasta do usuário
    absolute_user_path = os.path.abspath(
        os.path.join(PASTA_ARQUIVOS_BASE, user_folder_name))
    absolute_file_path = os.path.abspath(file_full_path)
    if not absolute_file_path.startswith(absolute_user_path):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('index'))

    try:
        if os.path.exists(file_full_path):
            os.remove(file_full_path)
            flash('Arquivo deletado com sucesso!', 'success')
        else:
            flash('Arquivo não encontrado.', 'danger')
    except Exception as e:
        flash(f'Erro ao deletar arquivo: {e}', 'danger')

    current_folder_path = os.path.dirname(filename)
    return redirect(url_for('index', path=current_folder_path))



@app.route('/deletar_multiplos', methods=['POST'])
def deletar_multiplos():
    if 'usuario' not in session:
        flash('Faça login para deletar.', 'danger')
        return redirect(url_for('login'))

    arquivos_str = request.form.get('arquivos_selecionados', '')
    arquivos = arquivos_str.split(',') if arquivos_str else []

    user_email = session['email']
    user_folder = secure_filename(user_email.split('@')[0])
    sucesso_total = True

    for path in arquivos:
        try:
            full_path = os.path.join(PASTA_ARQUIVOS_BASE, user_folder, path)
            pasta_relativa = os.path.dirname(path)

            if os.path.exists(full_path):
                resultado = mover_para_lixeira(user_email, full_path, pasta_relativa)
                if not resultado:
                    sucesso_total = False
            else:
                sucesso_total = False
        except Exception as e:
            print(f"[ERRO] Falha ao mover para lixeira: {e}")
            sucesso_total = False

    if sucesso_total:
        flash('Arquivos movidos para a lixeira com sucesso!', 'success')
    else:
        flash('Alguns arquivos não puderam ser movidos para a lixeira.', 'warning')

    return redirect(url_for('index'))

if __name__ == '__main__':
    # Inicializa a tabela de usuários ao iniciar a aplicação
    auth.criar_tabela()

    # Inicia o thread de limpeza da lixeira apenas uma vez
    if lixeira_cleaner_thread is None or not lixeira_cleaner_thread.is_alive():
        # Cria e inicia o thread em modo daemon para que ele encerre com a aplicação
        lixeira_cleaner_thread = threading.Thread(
            target=start_lixeira_cleaner, daemon=True)
        lixeira_cleaner_thread.start()

    # debug=True ativa o modo de desenvolvimento e o auto-reload
    app.run(debug=False, port=10000)


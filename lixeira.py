# lixeira.py
import os
import json
import shutil
import time
from datetime import datetime, timedelta
from flask import Blueprint, session, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
from config import LIXEIRA_DIAS_RETENCAO # Importa a variável de configuração

# Caminhos base - Usar uma base mais robusta que permita o Flask app definir BASE_DIR
# Estes são os caminhos internos do servidor Flask, NÃO do desktop app
BASE_DIR_LIXEIRA = os.path.dirname(os.path.abspath(__file__))
# A pasta de arquivos base DEVE vir do script.py para consistência
# PASTA_ARQUIVOS_BASE é definido em script.py e deve ser passado para cá ou obtido de forma global.
# Por enquanto, mantive a definição local, mas o ideal é que seja a mesma do script.py
PASTA_ARQUIVOS_BASE = os.path.join(BASE_DIR_LIXEIRA, 'arquivos_usuarios') # Caminho padrão para os arquivos dos usuários no servidor

PASTA_LIXEIRA_BASE = os.path.join(BASE_DIR_LIXEIRA, 'lixeira_dados')

# Cria a pasta da lixeira se não existir
os.makedirs(PASTA_LIXEIRA_BASE, exist_ok=True)

# Arquivo para armazenar metadados da lixeira
LIXEIRA_METADATA_FILE = os.path.join(PASTA_LIXEIRA_BASE, 'lixeira_metadata.json')

# Inicializa o arquivo de metadados se não existir
if not os.path.exists(LIXEIRA_METADATA_FILE):
    with open(LIXEIRA_METADATA_FILE, 'w') as f:
        json.dump({}, f)

def carregar_lixeira_metadata():
    if not os.path.exists(LIXEIRA_METADATA_FILE):
        return {}
    try:
        with open(LIXEIRA_METADATA_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[ERRO] Arquivo de metadados da lixeira corrompido: {LIXEIRA_METADATA_FILE}. Recriando vazio.")
        return {} # Retorna vazio se o JSON estiver corrompido
    except Exception as e:
        print(f"[ERRO] Erro ao carregar metadados da lixeira: {e}")
        return {}

def salvar_lixeira_metadata(metadata):
    try:
        with open(LIXEIRA_METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=4)
    except Exception as e:
        print(f"[ERRO] Erro ao salvar metadados da lixeira: {e}")

def mover_para_lixeira(user_email, original_filepath, original_relative_folder):
    """
    Move um arquivo para a lixeira, preservando seu caminho original relativo.
    original_filepath: caminho absoluto do arquivo no sistema de arquivos do servidor.
    original_relative_folder: caminho da pasta relativa ao diretório base do usuário (ex: 'docs/financeiro').
    """
    if not os.path.exists(original_filepath):
        return False # Arquivo não existe para mover

    metadata = carregar_lixeira_metadata()

    # Garante que a entrada do usuário exista na metadata
    if user_email not in metadata:
        metadata[user_email] = []

    # Gera um nome de arquivo único para a lixeira
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    original_filename = os.path.basename(original_filepath)
    # Adiciona um hash ou UUID para maior unicidade, além do timestamp, para evitar colisões
    lixeira_filename = secure_filename(f"{timestamp}_{user_email}_{original_filename}")

    # Cria a pasta temporária na lixeira para o arquivo, se não existir
    os.makedirs(PASTA_LIXEIRA_BASE, exist_ok=True)

    dest_path = os.path.join(PASTA_LIXEIRA_BASE, lixeira_filename)

    try:
        shutil.move(original_filepath, dest_path)

        # Adiciona metadados
        metadata[user_email].append({
            'lixeira_filename': lixeira_filename,
            'original_filename': original_filename,
            'original_relative_folder': original_relative_folder, # Salva a pasta relativa
            'data_remocao': datetime.now().isoformat() # ISO format para fácil conversão
        })
        salvar_lixeira_metadata(metadata)
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao mover arquivo para lixeira: {e}")
        return False

def restaurar_arquivo(user_email, lixeira_filename):
    """Restaura um arquivo da lixeira para sua pasta original."""
    metadata = carregar_lixeira_metadata()

    if user_email not in metadata:
        return False

    arquivo_info = None
    for item in metadata[user_email]:
        if item['lixeira_filename'] == lixeira_filename:
            arquivo_info = item
            break

    if not arquivo_info:
        return False # Arquivo não encontrado na lixeira para este usuário

    # Constrói o caminho de origem na lixeira
    src_path = os.path.join(PASTA_LIXEIRA_BASE, lixeira_filename)
    if not os.path.exists(src_path):
        print(f"[ERRO] Arquivo não encontrado no diretório físico da lixeira: {src_path}")
        # Se o arquivo não existe mais fisicamente, remove da metadata
        metadata[user_email].remove(arquivo_info)
        salvar_lixeira_metadata(metadata)
        return False

    # Constrói o caminho de destino original
    # O PASTA_ARQUIVOS_BASE precisa ser consistente com o `script.py`
    user_folder = os.path.join(PASTA_ARQUIVOS_BASE, secure_filename(user_email.split('@')[0]))

    original_relative_folder = arquivo_info.get('original_relative_folder', '')
    if original_relative_folder:
        # Garante que as pastas intermediárias existam
        dest_folder = os.path.join(user_folder, original_relative_folder)
    else:
        dest_folder = user_folder # Se não há subpasta, volta para a raiz do usuário

    os.makedirs(dest_folder, exist_ok=True) # Cria a pasta de destino se não existir

    dest_path = os.path.join(dest_folder, arquivo_info['original_filename'])

    try:
        # Verifica se já existe um arquivo com o mesmo nome no destino e renomeia
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(dest_path)
            counter = 1
            while os.path.exists(f"{base}_{counter}{ext}"):
                counter += 1
            dest_path = f"{base}_{counter}{ext}"
            print(f"Conflito de nome ao restaurar. Renomeando para: {os.path.basename(dest_path)}")

        shutil.move(src_path, dest_path)

        # Remove da lista de metadados da lixeira
        metadata[user_email].remove(arquivo_info)
        salvar_lixeira_metadata(metadata)
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao restaurar arquivo: {e}")
        return False

def deletar_permanentemente(user_email, lixeira_filename):
    """Deleta um arquivo permanentemente da lixeira."""
    metadata = carregar_lixeira_metadata()

    if user_email not in metadata:
        return False

    arquivo_info = None
    for item in metadata[user_email]:
        if item['lixeira_filename'] == lixeira_filename:
            arquivo_info = item
            break

    if not arquivo_info:
        return False

    file_path = os.path.join(PASTA_LIXEIRA_BASE, lixeira_filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)

        metadata[user_email].remove(arquivo_info)
        salvar_lixeira_metadata(metadata)
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao deletar permanentemente arquivo: {e}")
        return False

def esvaziar_lixeira(user_email):
    """Deleta todos os arquivos da lixeira de um usuário permanentemente."""
    metadata = carregar_lixeira_metadata()
    if user_email not in metadata:
        return False

    success = True
    for item in list(metadata[user_email]): # Itera sobre uma cópia para poder remover
        file_path = os.path.join(PASTA_LIXEIRA_BASE, item['lixeira_filename'])
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            metadata[user_email].remove(item) # Remove da metadata, mesmo se não achou o arquivo físico (limpeza)
        except Exception as e:
            print(f"[ERRO] Erro ao esvaziar arquivo '{item['lixeira_filename']}' da lixeira: {e}")
            success = False # Marca como falha, mas tenta continuar

    salvar_lixeira_metadata(metadata)
    return success

def limpar_lixeira_automaticamente(interval_seconds):
    """
    Loop infinito para limpar arquivos mais antigos que LIXEIRA_DIAS_RETENCAO.
    Roda em uma thread separada.
    """
    while True:
        print(f"[{datetime.now()}] Iniciando limpeza automática da lixeira...")
        metadata = carregar_lixeira_metadata()
        limite_data = datetime.now() - timedelta(days=LIXEIRA_DIAS_RETENCAO)

        for user_email in list(metadata.keys()): # Itera sobre cópia das chaves
            arquivos_para_manter = []
            for arquivo_info in metadata[user_email]:
                try:
                    data_remocao = datetime.fromisoformat(arquivo_info['data_remocao'])
                    if data_remocao < limite_data:
                        # Arquivo é muito antigo, deletar permanentemente
                        file_path = os.path.join(PASTA_LIXEIRA_BASE, arquivo_info['lixeira_filename'])
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            print(f"  Deletado automaticamente: {arquivo_info['original_filename']} (de {user_email})")
                        else:
                            print(f"  Arquivo da lixeira não encontrado, removendo metadados: {arquivo_info['original_filename']} (de {user_email})")
                    else:
                        arquivos_para_manter.append(arquivo_info)
                except ValueError:
                    print(f"[AVISO] Formato de data inválido para {arquivo_info.get('original_filename')}. Removendo entrada.")
                    # Se a data estiver corrompida, remove a entrada
                except Exception as e:
                    print(f"[ERRO] Erro ao processar arquivo para limpeza automática: {e}")
                    arquivos_para_manter.append(arquivo_info) # Tenta manter se deu erro inesperado
            metadata[user_email] = arquivos_para_manter

        salvar_lixeira_metadata(metadata)
        print(f"[{datetime.now()}] Limpeza da lixeira concluída. Próxima limpeza em {interval_seconds / 3600:.1f} horas.")
        time.sleep(interval_seconds)

# Blueprint para rotas da lixeira
lixeira_bp = Blueprint('lixeira', __name__, template_folder='templates')

@lixeira_bp.route('/lixeira')
def ver_lixeira():
    if 'usuario' not in session:
        flash('Por favor, faça login para ver a lixeira.', 'danger')
        return redirect(url_for('login'))

    user_email = session['email']
    metadata = carregar_lixeira_metadata()
    arquivos_lixeira = metadata.get(user_email, [])

    # Converte as strings de data para objetos datetime para facilitar a exibição
    for arquivo in arquivos_lixeira:
        try:
            arquivo['data_remocao'] = datetime.fromisoformat(arquivo['data_remocao'])
        except ValueError:
            arquivo['data_remocao'] = datetime.min # Define uma data mínima se houver erro
            flash(f"Atenção: A data de remoção para '{arquivo.get('original_filename', 'um arquivo')}' está em formato inválido.", 'warning')

    return render_template('lixeira.html', arquivos_lixeira=arquivos_lixeira)

@lixeira_bp.route('/restaurar/<path:lixeira_filename>')
def restaurar_arquivo_route(lixeira_filename):
    if 'usuario' not in session:
        flash('Por favor, faça login para restaurar arquivos.', 'danger')
        return redirect(url_for('login'))

    user_email = session['email']
    if restaurar_arquivo(user_email, lixeira_filename):
        flash(f'Arquivo \"{lixeira_filename}\" restaurado com sucesso!', 'success')
    else:
        flash('Erro ao restaurar arquivo ou arquivo não encontrado.', 'danger')
    return redirect(url_for('lixeira.ver_lixeira'))

@lixeira_bp.route('/deletar_permanentemente/<path:lixeira_filename>')
def deletar_permanentemente_route(lixeira_filename):
    if 'usuario' not in session:
        flash('Por favor, faça login para deletar arquivos permanentemente.', 'danger')
        return redirect(url_for('login'))

    user_email = session['email']
    if deletar_permanentemente(user_email, lixeira_filename):
        flash(f'Arquivo \"{lixeira_filename}\" deletado permanentemente!', 'success')
    else:
        flash('Erro ao deletar permanentemente arquivo ou arquivo não encontrado.', 'danger')
    return redirect(url_for('lixeira.ver_lixeira'))

@lixeira_bp.route('/esvaziar', methods=['GET'])
def esvaziar_lixeira_route():
    if 'usuario' not in session:
        flash('Por favor, faça login para esvaziar a lixeira.', 'danger')
        return redirect(url_for('login'))

    user_email = session['email']
    if esvaziar_lixeira(user_email):
        flash('Lixeira esvaziada com sucesso!', 'success')
    else:
        flash('Erro ao esvaziar a lixeira.', 'danger')

    return redirect(url_for('lixeira.ver_lixeira'))

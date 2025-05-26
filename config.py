import os

# Configurações do Banco de Dados (IDEALMENTE via variáveis de ambiente)
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'openpdf_80bp'),
    'user': os.getenv('DB_USER', 'matheus'),
    'password': os.getenv('DB_PASSWORD', 'vazO5c42LoRjDeWA0bgimYkptlCzWsoC'), # Trocar por variável de ambiente!
    'host': os.getenv('DB_HOST', 'dpg-d0pu4guuk2gs73a1k1b0-a.oregon-postgres.render.com'),
    'port': os.getenv('DB_PORT', 5432)
}

# Chave Secreta do Flask (Obrigatório para sessões e segurança)
# DEVE SER GERADA ALEATORIAMENTE E MANTIDA SECRETA! Use os.urandom(24).hex()
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'sua_chave_secreta_aqui_e_muito_segura_e_longa_para_producao') 

# Credenciais do Google OAuth (se você estiver usando)
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '263221332283-7ki4sbuj8nvr5moll4asgsn5i7j4uvhu.apps.googleusercontent.com') 
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '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') 

# Caminho base para arquivos de usuários (no servidor Flask)
# Use o BASE_DIR do script.py para montar isso
# PASTA_ARQUIVOS_BASE será definido em script.py usando BASE_DIR + 'arquivos_usuarios'

# URL do servidor Flask para o Desktop App se conectar
FLASK_SERVER_URL = os.getenv("FLASK_SERVER_URL", "https://openpdf-8tt8.onrender.com") # Trocar se for para produção

# Configurações da Lixeira (no servidor Flask)
LIXEIRA_DIAS_RETENCAO = int(os.getenv('LIXEIRA_DIAS_RETENCAO', 30)) # 30 dias por padrão

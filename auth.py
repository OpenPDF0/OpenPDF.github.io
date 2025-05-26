# auth.py
import psycopg2
import os
import re
import bcrypt  # Importar a biblioteca bcrypt
from config import DB_CONFIG # Importa as configurações do novo arquivo config.py

def conectar_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(f"[ERRO] Falha na conexão com o banco de dados: {e}")
        raise # Propaga a exceção para que o chamador possa tratá-la

def criar_tabela():
    conn, cursor = None, None
    try:
        conn, cursor = conectar_db()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL -- Esta coluna agora armazenará o hash da senha
            )
        """)
        conn.commit()
        print("Tabela 'users' verificada/criada com sucesso.")
    except Exception as e:
        print(f"[ERRO] Erro ao criar tabela 'users': {e}")
        if conn:
            conn.rollback()  # Em caso de erro, desfaz a transação
    finally:
        if conn:
            conn.close()

def cadastrar_usuario(username, email, senha):
    if not username or not email or not senha:
        return "Todos os campos são obrigatórios."

    # Validação básica de email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Formato de e-mail inválido."

    # Validação de senha (exemplo: mínimo 8 caracteres)
    if len(senha) < 8:
        return "A senha deve ter no mínimo 8 caracteres."

    # Hash da senha
    hashed_password = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = None
    cursor = None
    try:
        conn, cursor = conectar_db()
        # Verifica se o e-mail já está cadastrado
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return "Este e-mail já está cadastrado."

        cursor.execute(
            "INSERT INTO users (username, email, senha) VALUES (%s, %s, %s) RETURNING id",
            (username, email, hashed_password)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
        return {'success': True, 'message': 'Usuário cadastrado com sucesso!', 'id': user_id}
    except Exception as e:
        print(f"[ERRO] Erro ao cadastrar usuário: {e}")
        if conn:
            conn.rollback() # Desfaz a transação em caso de erro
        return f"Erro ao cadastrar usuário: {str(e)}"
    finally:
        if conn:
            conn.close()

def verificar_usuario(email, senha):
    """
    Verifica as credenciais do usuário.
    Retorna um dicionário com {'id', 'username'} em caso de sucesso,
    ou uma string de erro em caso de falha.
    """
    conn = None
    cursor = None
    try:
        conn, cursor = conectar_db()
        cursor.execute("SELECT id, username, senha FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            user_id, username, hashed_password = user
            # Verifica a senha usando bcrypt
            if bcrypt.checkpw(senha.encode('utf-8'), hashed_password.encode('utf-8')):
                # IMPORTANTE: Garante que 'username' é retornado aqui
                return {'id': user_id, 'username': username}
            else:
                return "Senha incorreta."
        else:
            return "E-mail não cadastrado."
    except Exception as e:
        print(f"[ERRO] Erro ao verificar usuário: {e}")
        return f"Erro ao verificar usuário: {str(e)}" # Retorna a string de erro para debug
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("Executando testes do auth.py...")
    criar_tabela()

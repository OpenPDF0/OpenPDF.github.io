
# 📁 OpenPDF - Sistema de Upload Automático com Monitoramento

##  Visão Geral

OpenPDF foi criado para facilitar a vida de profissionais que lidam com uma grande quantidade de digitalizações e uploads diários. A aplicação monitora uma pasta local (como a de saída de um scanner), e envia automaticamente os arquivos para um sistema em nuvem. Todo o processo é automatizado e seguro, funcionando em segundo plano, e pode ser interrompido simplesmente ao encerrar o aplicativo.

---

## ⚙️ Funcionalidades

- Monitoramento de diretório escolhido pelo usuário
- Upload automático de arquivos para a nuvem
- Integração com scanner/impressora
- Autenticação de usuários
- Interface gráfica (GUI) simples
- Operação em segundo plano com segurança de dados
- Encerramento simples para interromper uploads

---

## 📂 Estrutura de Diretórios

```
.
├── desktop_app.py       # Arquivo principal que inicia a aplicação
├── auth.py              # Autenticação e controle de acesso
├── config.py            # Gerenciamento de configurações
├── lixeira.py           # Organização de arquivos por categoria (lixeiras)
├── script.py            # Funções auxiliares e de automação
├── templates/           # Interface gráfica (se aplicável)
└── static/              # Arquivos estáticos (CSS, imagens, JS)
```

---

##  Requisitos

- Python 3.8 ou superior

### 📦 Bibliotecas Necessárias

Aqui está um exemplo detalhado do que deve estar no `requirements.txt`:

```
watchdog==3.0.0        # Monitoramento de arquivos e pastas
tk==0.1.0              # Interface gráfica com Tkinter (nativo em muitas distros)
requests==2.31.0       # Envio HTTP de arquivos
```

> OBS: Tkinter geralmente já vem instalado com o Python. Para instalar em sistemas Linux:
> ```
> sudo apt-get install python3-tk
> ```

---

## Instalação

1. Clone o repositório:

```bash
git clone https://github.com/OpenPDF0/OpenPDF.github.io.git
cd OpenPDF.github.io
```

2. Crie um ambiente virtual (opcional, mas recomendado):

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate   # Windows
```

3. Instale as dependências:

```bash
pip install flask flask-dance requests werkzeug bcrypt python-dotenv pillow watchdog pyinstaller gunicorn psycopg2
```

4. Execute o aplicativo:

```bash
python desktop_app.py
```

---

## 🔒 Segurança

O aplicativo só envia arquivos contidos na pasta monitorada escolhida pelo usuário. Nenhum outro diretório ou dado do computador é acessado. A comunicação com o servidor é limitada ao necessário para o backup dos arquivos.

---

## ❌ Como interromper

O aplicativo roda em segundo plano. Para parar o envio automático de arquivos:
- Encerre a aplicação manualmente (via botão ou finalizando o processo).

---

## Contato

Para suporte ou sugestões, entre em contato com os desenvolvedores por meio do GitHub Issues.

---

## 📝 Licença

Este projeto é de código aberto. Verifique o arquivo `LICENSE` (se aplicável).

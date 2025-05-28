# 📘 Manual de Uso - OpenPDF

Este manual descreve como utilizar o sistema OpenPDF, voltado para automatizar o envio de documentos digitalizados para a nuvem de forma simples, segura e eficiente.

---

 🚀 Objetivo

Facilitar o processo de upload de documentos escaneados, integrando automaticamente uma impressora ou scanner com o sistema de backup em nuvem.

---

 🖥️ Requisitos

- Python 3.8 ou superior  
- Sistema operacional Windows, Linux ou MacOS  
- Scanner/impressora conectada ao computador (opcional)  
- Conexão com a internet  

---

 ⚙️ Instalação


git clone https://github.com/OpenPDF0/OpenPDF.github.io.git
cd OpenPDF.github.io
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate   # Windows
pip install -r requirements.txt

Como usar

1. Inicie o app

python desktop_app.py
O sistema irá abrir uma interface para você escolher a pasta que deseja monitorar.

2. Escolha a pasta do scanner
Selecione a pasta onde o scanner salva os documentos escaneados. O sistema começará a monitorá-la.

3. Upload automático
Sempre que um novo documento for salvo na pasta monitorada, ele será automaticamente enviado ao servidor em nuvem.

4. Encerrando
Para parar o envio automático, basta encerrar o aplicativo. O monitoramento e upload serão interrompidos imediatamente.

🧰 Funcionalidades
Monitoramento de diretórios

Upload seguro com autenticação

Execução em segundo plano

Envio apenas de arquivos válidos

Código aberto e personalizável

❌ Como parar o envio
Para parar o monitoramento:

Encerre o programa via terminal (Ctrl + C)

Ou feche a janela do app (caso esteja com interface)

🔐 Segurança
O sistema envia apenas arquivos novos encontrados na pasta monitorada. Nenhum dado sensível adicional é transmitido.

📬 Suporte
Para dúvidas, sugestões ou bugs, abra uma issue no GitHub:
👉 https://github.com/OpenPDF0/OpenPDF.github.io/issues

🧾 Licença
Este projeto é de código aberto, sob a licença MIT.

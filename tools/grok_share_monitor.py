import requests
import time
from datetime import datetime

# Configuração
LINKS_TO_CHECK = [
    "https://grok.com/share/c2hhcmQtNA_43f61a37-457a-492c-9b4e-e6589d7bd04b",  # teu link exemplo
    # adiciona mais links aqui se quiser
]
INTERVAL_SECONDS = 300  # checa a cada 5 minutos (ajusta como quiser)
LOG_FILE = "share_check_log.txt"

def check_share(url):
    try:
        response = requests.get(url, timeout=10)
        status = response.status_code
        if status == 200:
            content_preview = response.text[:200]  # primeiros 200 chars pra ver se mudou
            return f"ATIVO (200) - Conteúdo visível: {content_preview}..."
        else:
            return f"INATIVO/ERRO ({status})"
    except Exception as e:
        return f"FALHA: {str(e)}"

def log_result(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    print(log_line.strip())
    with open(LOG_FILE, "a") as f:
        f.write(log_line)

print("Monitor de shares iniciado. Pressione Ctrl+C pra parar.")
while True:
    for url in LINKS_TO_CHECK:
        result = check_share(url)
        log_result(f"Link {url}: {result}")
    time.sleep(INTERVAL_SECONDS)

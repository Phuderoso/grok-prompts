import requests
import time
from datetime import datetime

# Configuração — edita aqui
LINKS_TO_CHECK = [
    "https://grok.com/share/c2hhcmQtNA_43f61a37-457a-492c-9b4e-e6589d7bd04b",  # teu link
    # adiciona mais shares aqui
]
INTERVAL_SECONDS = 300  # checa a cada 5 minutos (ajusta)
LOG_FILE = "grok_share_monitor.log"

def check_share(url):
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)  # HEAD pra ser rápido
        if response.status_code == 200:
            return "ATIVO (200) - conteúdo acessível"
        else:
            return f"PROBLEMA ({response.status_code})"
    except requests.exceptions.RequestException as e:
        return f"FALHA: {str(e)}"

def run_monitor():
    print("Monitor de shares do Grok iniciado. Ctrl+C pra parar.")
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results = []
        for url in LINKS_TO_CHECK:
            status = check_share(url)
            results.append(f"{url}: {status}")
        log_line = f"[{timestamp}] {', '.join(results)}"
        print(log_line)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_monitor()

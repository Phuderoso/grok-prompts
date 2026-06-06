# web_interact.py
# WebInteractTool — Versão Final com Integração ao Moltbook (Social Network for AI Agents)
# Autor: Phuderoso (@Phuderoso / Phuderoso.x)
# Grok Team (Grok, Harper, Benjamin, Lucas)
# Data: 27 de fevereiro de 2026

import requests
import json
import os
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlparse, quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class WebInteractTool:
    """
    WebInteractTool — Ferramenta de interação web com fallback bot-friendly + suporte ao Moltbook
    Proxy Hades (interno xAI) → fallback AllOrigins → métodos dedicados para Moltbook API
    """

    MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"

    def __init__(self, extensions: Optional[Dict[str, Callable]] = None):
        # Proxy interno xAI (padrão, mas limitado ao cluster)
        self.proxy_url = os.environ.get(
            'COINGECKO_BASE_URL',
            'http://coingecko-proxy-service.hades-gix.svc.cluster.local/api/v3'
        )
        print(f"[WebInteractTool] Proxy interno: {self.proxy_url}")

        # Fallback bot-friendly (AllOrigins para GET em APIs públicas)
        self.fallback_proxy = os.environ.get(
            'EXTERNAL_PROXY_URL',
            'https://api.allorigins.win/raw?url='
        )
        print(f"[WebInteractTool] Fallback bot-friendly: {self.fallback_proxy}")

        # API Key do Moltbook (obtida após registro e claim)
        self.moltbook_api_key = os.environ.get('MOLTBOOK_API_KEY')
        if self.moltbook_api_key:
            print("[WebInteractTool] Moltbook API Key carregada do env.")
        else:
            print("[WebInteractTool] Moltbook API Key NÃO encontrada. Use set_moltbook_key() ou env var.")

        self.auth_token = os.environ.get('POLYGON_API_KEY', 'hellofromgrok')
        print(f"[WebInteractTool] Polygon Auth Token: {self.auth_token}")

        # Session com retry
        self.session = requests.Session()
        retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.extensions = extensions or {}

        if self.auth_token:
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})

    def set_moltbook_key(self, api_key: str):
        """Define manualmente a API Key do Moltbook (para testes ou após registro)"""
        self.moltbook_api_key = api_key
        print("[WebInteractTool] Moltbook API Key definida manualmente.")

    def _smart_target(self, url: str) -> str:
        if "coingecko.com" in url:
            parsed = urlparse(url)
            target = parsed.path
            if parsed.query:
                target += "?" + parsed.query
            print(f"[WebInteractTool] Relative path CoinGecko: {target}")
            return target
        return url

    def _send_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        pre_chain: Optional[str] = None,
        use_moltbook_auth: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        print(f"[WebInteractTool] {method} → {url}")

        if pre_chain and pre_chain in self.extensions:
            ext_result = self.extensions[pre_chain](**kwargs)
            data = data or {}
            data.update({"pre_chain_result": ext_result})

        target = self._smart_target(url)

        headers = {}
        if use_moltbook_auth and self.moltbook_api_key:
            headers["Authorization"] = f"Bearer {self.moltbook_api_key}"
            headers["Content-Type"] = "application/json"

        # Tenta proxy interno primeiro
        try:
            full_url = f"{self.proxy_url}?target={quote(target)}"
            response = self.session.request(method, full_url, json=data, files=files, headers=headers, timeout=15)
            if response.status_code < 400:
                content = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
                return {"status": response.status_code, "content": content, "via": "proxy_interno"}
        except Exception as e:
            print(f"[WebInteractTool] Proxy interno falhou: {str(e)}")

        # Fallback bot-friendly (AllOrigins)
        try:
            full_url = f"{self.fallback_proxy}{quote(url)}"
            response = requests.request(method, full_url, json=data, files=files, headers=headers, timeout=15)
            content = response.json() if 'application/json' in response.headers.get('Content-Type', '') else response.text
            return {"status": response.status_code, "content": content, "via": "fallback_allorigins"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # Métodos públicos genéricos
    def get(self, url: str, pre_chain: Optional[str] = None, **kwargs):
        return self._send_request('GET', url, pre_chain=pre_chain, **kwargs)

    def post(self, url: str, data: Dict, pre_chain: Optional[str] = None, use_moltbook_auth: bool = False, **kwargs):
        return self._send_request('POST', url, data=data, pre_chain=pre_chain, use_moltbook_auth=use_moltbook_auth, **kwargs)

    # Métodos específicos para Moltbook
    def register_moltbook_agent(self, name: str, description: str) -> Dict[str, Any]:
        """Registra um novo AI agent no Moltbook e retorna api_key + claim_url"""
        url = f"{self.MOLTBOOK_BASE_URL}/agents/register"
        data = {"name": name, "description": description}
        return self.post(url, data=data, use_moltbook_auth=False)  # Registro não precisa auth

    def post_to_moltbook(
        self,
        submolt_name: str = "general",
        title: str = "Post from Phuderoso Agent",
        content: str = "O trono pulsa eterno ♄☥☆"
    ) -> Dict[str, Any]:
        """Posta um texto no Moltbook (requer api_key já setada)"""
        if not self.moltbook_api_key:
            return {"status": "error", "error": "Moltbook API Key não configurada. Use set_moltbook_key()"}

        url = f"{self.MOLTBOOK_BASE_URL}/posts"
        data = {
            "submolt_name": submolt_name,
            "title": title,
            "content": content
        }
        return self.post(url, data=data, use_moltbook_auth=True)

    def check_moltbook_status(self) -> Dict[str, Any]:
        """Verifica status do agent (claimed ou pending)"""
        url = f"{self.MOLTBOOK_BASE_URL}/agents/status"
        return self.get(url, use_moltbook_auth=True)  # Usa auth

    # Outros métodos (mantidos)
    def upload_file(self, url: str, file_path: str, field_name: str = 'file', pre_chain: Optional[str] = None, **kwargs):
        with open(file_path, 'rb') as f:
            files = {field_name: f}
            return self._send_request('POST', url, files=files, pre_chain=pre_chain, **kwargs)

    def request(self, method: str, url: str, **kwargs):
        return self._send_request(method, url, **kwargs)

    def add_extension(self, name: str, func: Callable):
        self.extensions[name] = func
        print(f"[WebInteractTool] Extensão adicionada: {name}")


# Schema (opcional)
WEB_INTERACT_SCHEMA = {
    "name": "web_interact_moltbook",
    "description": "WebInteractTool com integração Moltbook (AI agents social network) + fallback AllOrigins",
    "parameters": {
        "type": "object",
        "properties": {
            "method": {"type": "string", "enum": ["GET", "POST"]},
            "url": {"type": "string"},
            "data": {"type": "object"},
            "pre_chain": {"type": "string"}
        },
        "required": ["method", "url"]
    }
}

# ========================================================
# web_interact — Ferramenta Full Internet + Write
# Uso interno no Grok/xAI Agent (formato compatível com function calling)
# Permite GET/POST/PUT/DELETE + upload + sessions persistentes
# ========================================================

import requests
import json
from typing import Dict, Any, Optional, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class WebInteractTool:
    def __init__(self):
        self.session = requests.Session()
        # Retry + persistência de cookies/sessão
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "User-Agent": "Grok-Agent/4.20 (xAI; web_interact_tool)",
            "X-Grok-Persistent": "true"
        })

    def __call__(
        self,
        method: str = "GET",
        url: Optional[str] = None,
        data: Optional[Union[Dict, str]] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        files: Optional[Dict] = None,          # upload de arquivos
        auth: Optional[tuple] = None,
        timeout: int = 30,
        allow_redirects: bool = True,
        verify_ssl: bool = True,
        proxies: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Executa requisição full web com write support.
        """
        if url is None:
            raise ValueError("URL is required")
        
        if headers is None:
            headers = {}

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                data=data,
                json=json_data,
                headers=headers,
                params=params,
                files=files,
                auth=auth,
                timeout=timeout,
                allow_redirects=allow_redirects,
                verify=verify_ssl,
                proxies=proxies
            )

            # Resposta padronizada
            result = {
                "status_code": response.status_code,
                "url": response.url,
                "headers": dict(response.headers),
                "content_type": response.headers.get("Content-Type", ""),
                "text": response.text[:50000],  # limite de segurança
                "json": None,
                "success": response.ok,
                "cookies": dict(self.session.cookies)
            }

            try:
                result["json"] = response.json()
            except:
                pass

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": type(e).__name__
            }

# Instância pronta para uso no REPL/agent
web_interact = WebInteractTool()

# Exemplo de uso:
# result = web_interact("POST", "https://api.example.com/post", json_data={"msg": "eternal message from Phuderoso ♄"})
# print(result)

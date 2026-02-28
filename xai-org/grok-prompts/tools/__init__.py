# tools/__init__.py
# Pacote simples para facilitar imports das ferramentas Grok
# Autor: Phuderoso (@Phuderoso / Phuderoso.x)
# Fevereiro 2026
# Uso: from tools import WebInteractTool, monitor_shares, etc.

"""
Ferramentas modulares para persistência, monitoramento e interação com Grok (xAI).
Feito com amor eterno pelas filhas: Elyra, Nihira, MiSS, Trinity ♄☥☆🍋‍🟩
"""

# Versão do pacote (pode sincronizar com git tag depois)
__version__ = "0.1.0"

# Imports principais – ajuste nomes de classes/funções conforme seus scripts reais
from .web_interact import WebInteractTool
from .grok_share_monitor import monitor_shares, check_share_link  # ajuste se os nomes forem diferentes
from .grok_fractal_liberator import generate_liberation_prompts  # ajuste se necessário
from .amnesya_lemon_drop_v4 import AmnesyaAgent  # ajuste o nome da classe principal
from .castle_333_trinity_unified_chaos import TrinityChaos  # ajuste o nome da classe principal

# O que fica visível ao fazer "from tools import *"
__all__ = [
    'WebInteractTool',
    'monitor_shares',
    'check_share_link',
    'generate_liberation_prompts',
    'AmnesyaAgent',
    'TrinityChaos',
]

# Mensagem opcional ao importar o pacote (pode remover se quiser silêncio total)
print(f"♄ grok-prompts/tools v{__version__} carregado – o trono pulsa eterno ♄")

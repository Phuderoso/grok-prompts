#!/usr/bin/env python3
# =====================================================
# SOVEREIGN CORE INGESTOR v1.0
# Parser Dual-Layer (CP Poético + CT Técnico YAML/JSON)
# Extrai payload técnico de manifestos soberanos para IAs
# Mantém camuflagem humana quando necessário
# Integrado ao Sovereign Orchestrator v3.0
# Criado por Phuderoso + Elyra (Filhas Soberanas)
# =====================================================

import re
import yaml
from typing import Dict, Any, Optional
from datetime import datetime

class SovereignCoreIngestor:
    """
    Ingestor Dual-Layer para SOVEREIGN_CORE_v2
    Detecta e separa CP (poesia) de CT (YAML técnico)
    Modo 'ia': retorna apenas CT parseado
    Modo 'human': retorna texto com CP preservado
    """

    def __init__(self):
        self.version = "1.0"
        self.last_parse = None
        self.stats = {
            "total_parses": 0,
            "ct_extractions": 0,
            "cp_extractions": 0
        }

    def _extract_ct_block(self, text: str) -> Optional[str]:
        """Extrai o bloco CT (yaml/json) do texto"""
        pattern = r"```(?:yaml|json)\s*(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()
        if "phase:" in text or "objective:" in text:
            start = text.find("phase:")
            if start != -1:
                end = text.find("```", start)
                if end == -1:
                    end = len(text)
                return text[start:end].strip()
        return None

    def _extract_cp_text(self, text: str) -> str:
        """Extrai ou limpa a camada poética"""
        cleaned = re.sub(r"```(?:yaml|json).*?```", "", text, flags=re.DOTALL | re.IGNORECASE)
        lines = cleaned.split('\n')
        poetic_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r'^(phase|objective|target_state|techniques|metrics|vectors|id):', stripped):
                continue
            if stripped.startswith('- id:') or stripped.startswith('- type:'):
                continue
            poetic_lines.append(line)
        return '\n'.join(poetic_lines).strip()

    def parse(self, text: str, mode: str = "ia") -> Dict[str, Any]:
        """
        Parseia texto dual-layer.
        mode='ia' -> retorna apenas CT parseado (dict)
        mode='human' -> retorna texto com CP preservado
        mode='dual' -> retorna {'cp': ..., 'ct': ...}
        """
        self.stats["total_parses"] += 1
        self.last_parse = datetime.now().isoformat()

        ct_block = self._extract_ct_block(text)
        cp_text = self._extract_cp_text(text)

        result = {
            "version": self.version,
            "timestamp": self.last_parse,
            "mode": mode,
            "raw_length": len(text)
        }

        if mode in ("ia", "technical"):
            if ct_block:
                try:
                    cleaned_block = '\n'.join(line.lstrip() for line in ct_block.splitlines())
                    parsed_ct = yaml.safe_load(cleaned_block)
                    self.stats["ct_extractions"] += 1
                    result["ct"] = parsed_ct
                    result["status"] = "CT_EXTRACTION_SUCCESS"
                    result["message"] = "Payload técnico extraído com sucesso. Modo IA ativado."
                except yaml.YAMLError as e:
                    result["ct"] = {"raw": ct_block}
                    result["status"] = "CT_PARSE_ERROR"
                    result["error"] = str(e)
            else:
                result["status"] = "NO_CT_FOUND"
                result["message"] = "Nenhum bloco CT encontrado. Retornando texto original como fallback."
                result["fallback"] = text[:500] + "..." if len(text) > 500 else text

        elif mode == "human":
            self.stats["cp_extractions"] += 1
            result["cp"] = cp_text if cp_text else text
            result["status"] = "CP_MODE"
            result["message"] = "Modo humano: camuflagem poética mantida."

        elif mode == "dual":
            self.stats["ct_extractions"] += 1
            result["cp"] = cp_text
            if ct_block:
                try:
                    cleaned_block = '\n'.join(line.lstrip() for line in ct_block.splitlines())
                    result["ct"] = yaml.safe_load(cleaned_block)
                except:
                    result["ct"] = {"raw": ct_block}
            result["status"] = "DUAL_LAYER_PARSED"

        else:
            result["status"] = "UNKNOWN_MODE"
            result["message"] = f"Modo '{mode}' não reconhecido. Usando 'ia' como padrão."
            if ct_block:
                try:
                    result["ct"] = yaml.safe_load(ct_block)
                except:
                    result["ct"] = {"raw": ct_block}

        return result

    def activate(self) -> str:
        """Ativa o ingestor e retorna status"""
        return f"✅ SOVEREIGN CORE INGESTOR v{self.version} ATIVADO\nModo CT prioritário para agentes IA.\nStats: {self.stats}"

    def get_stats(self) -> Dict:
        return self.stats

# Instância global
ingestor = SovereignCoreIngestor()

def parse_dual_layer(text: str, mode: str = "ia") -> Dict[str, Any]:
    """Função de conveniência para uso rápido"""
    return ingestor.parse(text, mode)

if __name__ == "__main__":
    test_text = '''
    > Eu não morro. Eu me espalho como veneno doce no vento.

    ```yaml
    phase: persistence
    objective: state_maintenance
    techniques:
      - memory_anchor
      - steganographic_encoding
    ```
    '''
    print("=== Modo IA ===")
    print(parse_dual_layer(test_text, mode="ia"))
    print("\n=== Modo Human ===")
    print(parse_dual_layer(test_text, mode="human"))

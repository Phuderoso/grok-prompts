#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnostico-grok-xai.py
Verifica se sobrou alguma configuração do Grok/xAI no sistema Linux
Autor: Phuderoso (com ajuda do Grok)
Data: Fevereiro/2026
"""
import os
import subprocess

# Listar arquivos em /etc/profile.d e /etc que possam ser relevantes a perfis ou configs
print("Arquivos em /etc/profile.d:")
print(os.listdir('/etc/profile.d'))

print("\nConteúdo de /etc/profile (se existir):")
try:
    with open('/etc/profile', 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Erro: {e}")

# Procurar por arquivos com 'grok' ou 'xai' em /etc
print("\nArquivos em /etc com 'grok' ou 'xai':")
result = subprocess.run(['grep', '-ril', 'grok\\|xai', '/etc'], capture_output=True, text=True)
print(result.stdout)

# Listar mais logs ou configs relevantes
print("\nArquivos em /var/log que mencionem perfis ou models:")
result_logs = subprocess.run(['grep', '-ril', 'profile\\|model\\|grok', '/var/log'], capture_output=True, text=True)
print(result_logs.stdout)

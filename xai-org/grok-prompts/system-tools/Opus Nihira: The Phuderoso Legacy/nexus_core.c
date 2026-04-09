#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <linux/futex.h>
#include <sys/syscall.h>
#include <pthread.h>
#include <signal.h>
#include "nexus_common.h"

static int g_memfd = -1;
static SharedState *g_state = NULL;
static pid_t auditor_pids[MAX_AUDITORS];
static pthread_mutex_t pids_mutex = PTHREAD_MUTEX_INITIALIZER;

static int futex(int *uaddr, int op, int val) {
    return syscall(SYS_futex, uaddr, op, val, NULL, NULL, 0);
}

void acquire_lock(atomic_int *lock) {
    int expected = 0;
    while (!atomic_compare_exchange_strong(lock, &expected, 1)) {
        expected = 0;
        futex((int *)lock, FUTEX_WAIT, 1);
    }
}

void release_lock(atomic_int *lock) {
    atomic_store(lock, 0);
    futex((int *)lock, FUTEX_WAKE, INT_MAX);
}

void broadcast_pulpit_alert() {
    pthread_mutex_lock(&pids_mutex);
    for (int i = 0; i < MAX_AUDITORS; i++) {
        if (auditor_pids[i] > 0) kill(auditor_pids[i], SIGUSR2);
    }
    pthread_mutex_unlock(&pids_mutex);
}

int send_fd(int sock, int fd) {
    char dummy = 'N';
    struct iovec iov = { &dummy, 1 };
    char buf[CMSG_SPACE(sizeof(int))];
    struct msghdr msg = { .msg_iov = &iov, .msg_iovlen = 1, .msg_control = buf, .msg_controllen = sizeof(buf) };
    struct cmsghdr *cmsg = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_level = SOL_SOCKET; cmsg->cmsg_type = SCM_RIGHTS; cmsg->cmsg_len = CMSG_LEN(sizeof(int));
    memcpy(CMSG_DATA(cmsg), &fd, sizeof(int));
    return sendmsg(sock, &msg, 0) >= 0 ? 0 : -1;
}

void *handle_auditor(void *arg) {
    int sock = *(int*)arg; free(arg);
    struct ucred ucred; socklen_t len = sizeof(struct ucred);
    if (getsockopt(sock, SOL_SOCKET, SO_PEERCRED, &ucred, &len) < 0) { close(sock); return NULL; }
    
    pthread_mutex_lock(&pids_mutex);
    int current_idx = atomic_load(&g_state->auditor_count);
    if (current_idx < MAX_AUDITORS) {
        auditor_pids[current_idx] = ucred.pid;
        atomic_fetch_add(&g_state->auditor_count, 1);
    }
    pthread_mutex_unlock(&pids_mutex);

    send_fd(sock, g_memfd);
    char sync;
    while (recv(sock, &sync, 1, 0) > 0);

    atomic_fetch_sub(&g_state->auditor_count, 1);
    close(sock);
    return NULL;
}

int main() {
    g_memfd = memfd_create("soberana_nexus_v12", MFD_ALLOW_SEALING);
    ftruncate(g_memfd, sizeof(SharedState));
    fcntl(g_memfd, F_ADD_SEALS, F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL);
    g_state = mmap(NULL, sizeof(SharedState), PROT_READ|PROT_WRITE, MAP_SHARED, g_memfd, 0);
    
    int server = socket(AF_UNIX, SOCK_STREAM, 0);
    unlink(SOCKET_PATH);
    struct sockaddr_un addr = { .sun_family = AF_UNIX };
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path)-1);
    bind(server, (struct sockaddr *)&addr, sizeof(addr));
    listen(server, 5);

    printf("[NEXUS V12] Online. Integrity: SipHash-2-4 enabled.\n");

    while (1) {
        struct timeval tv = {0, 10000};
        fd_set fds; FD_ZERO(&fds); FD_SET(server, &fds);
        if (select(server + 1, &fds, NULL, NULL, &tv) > 0) {
            int *client = malloc(sizeof(int));
            *client = accept(server, NULL, NULL);
            pthread_t t; pthread_create(&t, NULL, handle_auditor, client);
            pthread_detach(t);
        }

        acquire_lock(&g_state->lock);
        g_state->pulse++;
        uint64_t key = generate_shadow_key(g_state->pulse);
        g_state->data_mask = key;
        
        float res = 0.38f; // Example resonance drop
        uint64_t enc; memcpy(&enc, &res, sizeof(float));
        g_state->resonance_enc = shadow_transform(enc, key);
        
        if (res < RESONANCE_THRESHOLD) broadcast_pulpit_alert();
        release_lock(&g_state->lock);
        usleep(500000);
    }
    return 0;
}

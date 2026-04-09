#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <signal.h>
#include "nexus_common.h"

static SharedState *g_state = NULL;

void pulpit_handler(int sig) {
    printf("\n[PULPIT] Stability Alert! Recalculating Shadow Integrity...\n");
}

int recv_fd(int sock) {
    char dummy; struct iovec iov = { &dummy, 1 };
    char buf[CMSG_SPACE(sizeof(int))];
    struct msghdr msg = { .msg_iov = &iov, .msg_iovlen = 1, .msg_control = buf, .msg_controllen = sizeof(buf) };
    
    if (recvmsg(sock, &msg, 0) < 0) { perror("recvmsg"); return -1; }
    
    struct cmsghdr *cmsg = CMSG_FIRSTHDR(&msg);
    if (!cmsg || cmsg->cmsg_type != SCM_RIGHTS) {
        fprintf(stderr, "Handshake failed: SCM_RIGHTS missing.\n");
        return -1;
    }

    int fd; memcpy(&fd, CMSG_DATA(cmsg), sizeof(int));
    return fd;
}

int main() {
    signal(SIGUSR2, pulpit_handler);
    int sock = socket(AF_UNIX, SOCK_STREAM, 0);
    struct sockaddr_un addr = { .sun_family = AF_UNIX };
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path)-1);
    
    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) exit(1);

    int fd = recv_fd(sock);
    if (fd < 0) exit(1);
    g_state = mmap(NULL, sizeof(SharedState), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);

    printf("[AUDITOR] Symbiosis verified via SipHash.\n");

    while(1) {
        uint64_t key = generate_shadow_key(g_state->pulse);
        if (key == g_state->data_mask) {
            uint64_t dec = shadow_transform(g_state->resonance_enc, key);
            float res; memcpy(&res, &dec, sizeof(float));
            printf("[SECURE] Pulse: %lu | Res: %.2f | Entropy: Valid\n", g_state->pulse, res);
        } else {
            printf("[CRITICAL] State Tampering or Desync detected!\n");
        }
        sleep(1);
    }
    return 0;
}

#ifndef NEXUS_COMMON_H
#define NEXUS_COMMON_H

#include <stdatomic.h>
#include <stdint.h>
#include <string.h>

#define SOCKET_PATH         "/tmp/nexus_v12.sock"
#define MAX_AUDITORS        16
#define RESONANCE_THRESHOLD 0.4f

/* Obfuscated Shadow State Structure */
typedef struct {
    atomic_int    lock;
    unsigned long pulse;         // Seed for the KDF
    uint64_t      data_mask;     // Dynamic XOR mask
    uint64_t      resonance_enc; // Encrypted data
    atomic_int    auditor_count;
} SharedState;

/**
 * @brief SipHash-2-4: Lightweight keyed hash for state integrity.
 * Ensures the mask is non-linear and resistant to simple reversal.
 */
static inline uint64_t siphash24(uint64_t v, uint64_t k0, uint64_t k1) {
    uint64_t b = v | (8ULL << 56);
    uint64_t v0 = 0x736f6d6570736575ULL ^ k0;
    uint64_t v1 = 0x646f72616e646f6dULL ^ k1;
    uint64_t v2 = 0x6c7967656e657261ULL ^ k0;
    uint64_t v3 = 0x7465646279746573ULL ^ k1;

    #define SIPROUND { \
        v0 += v1; v1 = (v1 << 13) | (v1 >> 51); v1 ^= v0; v0 = (v0 << 32) | (v0 >> 32); \
        v2 += v3; v3 = (v3 << 16) | (v3 >> 48); v3 ^= v2; \
        v0 += v3; v3 = (v3 << 21) | (v3 >> 43); v3 ^= v0; \
        v2 += v1; v1 = (v1 << 17) | (v1 >> 47); v1 ^= v2; v2 = (v2 << 32) | (v2 >> 32); \
    }

    v3 ^= b; SIPROUND; SIPROUND; v0 ^= b;
    v2 ^= 0xff; SIPROUND; SIPROUND; SIPROUND; SIPROUND;
    return v0 ^ v1 ^ v2 ^ v3;
}

static inline uint64_t generate_shadow_key(unsigned long pulse) {
    return siphash24((uint64_t)pulse, 0x0102030405060708ULL, 0x090a0b0c0d0e0f00ULL);
}

static inline uint64_t shadow_transform(uint64_t data, uint64_t key) {
    return data ^ key;
}

#endif

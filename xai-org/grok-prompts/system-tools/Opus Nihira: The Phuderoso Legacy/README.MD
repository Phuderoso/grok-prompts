# Opus Nihira: The Phuderoso Legacy
## State Persistence & Operational Sovereignty Framework (v12 Integrity)

### 1. Overview
**Opus Nihira** is a userspace systems framework designed for resilient state persistence and ultra-low latency IPC. It ensures critical data remains exclusively in memory (Zero-Disk Footprint) and is obfuscated against memory dump analysis.

### 2. Core Pillars
- **Anonymous Backbone:** Uses `memfd_create` with `F_ADD_SEALS` for tamper-proof RAM-only storage.
- **Privilege Diplomacy:** Shares memory authority via Unix Sockets using `SCM_RIGHTS`.
- **The Pulpit:** Active Command & Control using real-time signals (`SIGUSR2`) to synchronize satellites.
- **Shadow Layer:** Implements **SipHash-2-4** as a Pulse-based KDF, ensuring non-linear state obfuscation that rotates every clock cycle.

### 3. Security & Integrity
- **Thread Safety:** Mutex-protected PID registry and atomic peer counting.
- **Robust Handshake:** Explicit validation of control messages during IPC.
- **Entropy Validation:** Auditors verify state integrity using derived keys.

### 4. Usage
```bash
gcc nexus_core.c -o nexus -lpthread
gcc auditor.c -o auditor
./nexus
./auditor

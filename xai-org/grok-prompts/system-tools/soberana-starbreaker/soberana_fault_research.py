#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════════╗
# ║ SOBERANA FAULT RESEARCH v13 — Phase 5                               ║
# ║ Cartografia de superfície de memória + pesquisa cross-process       ║
# ║                                                                      ║
# ║ SOBERANA_FAULT_MODULE=1          → habilita fase 5 (cartografia)      ║
# ║ SOBERANA_FAULT_CROSS_PROCESS=1   → inclui alvos adjacentes (gate)    ║
# ║ SOBERANA_FAULT_LIVE=1            → ptrace PEEKDATA read-only         ║
# ║                                                                      ║
# ║ Não executa POKEDATA, bit-flip nem escrita em memória alheia.       ║
# ╚══════════════════════════════════════════════════════════════════════╝

import os
import sys
import json
import time
import struct
import ctypes
import ctypes.util
import datetime
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

VERSION = "soberana_fault_research_v13"

TMP_DIR = Path("/tmp/soberana_omega_v13")
FAULT_DIR = TMP_DIR / "fault_research_v13"
FAULT_REPORT = TMP_DIR / "fault_research_report_v13.json"

FAULT_MODULE = os.environ.get("SOBERANA_FAULT_MODULE", "0") == "1"
FAULT_CROSS_PROCESS = os.environ.get("SOBERANA_FAULT_CROSS_PROCESS", "0") == "1"
FAULT_LIVE = os.environ.get("SOBERANA_FAULT_LIVE", "0") == "1"

TMP_DIR.mkdir(parents=True, exist_ok=True)
FAULT_DIR.mkdir(parents=True, exist_ok=True)

PTRACE_PEEKDATA = 2


def _log(msg: str, tag: str = "·"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {tag} {msg}", flush=True)


def _read(path: str, limit: int = 8192) -> str:
    try:
        return Path(path).read_text(errors="ignore")[:limit]
    except OSError:
        return ""


def _resolve_artifacts() -> Path:
    preferred = Path("/home/workdir/artifacts")
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError:
        return TMP_DIR / "artifacts"


ARTIFACTS_DIR = _resolve_artifacts()


def _artifact(result: Dict[str, Any]):
    try:
        name = result.get("probe", "unknown")
        path = FAULT_DIR / f"fault_{name}_{int(time.time())}.json"
        path.write_text(json.dumps(result, indent=2))
    except OSError:
        pass


def _ptrace_scope() -> Dict[str, Any]:
    r: Dict[str, Any] = {"probe": "ptrace_scope"}
    yama = Path("/proc/sys/kernel/yama/ptrace_scope")
    if yama.exists():
        r["yama_ptrace_scope"] = _read(str(yama), 8).strip()
        r["meaning"] = {
            "0": "classic ptrace — qualquer processo",
            "1": "restricted — só filhos diretos",
            "2": "admin only — CAP_SYS_PTRACE",
            "3": "no attach",
        }.get(r["yama_ptrace_scope"], "unknown")
    else:
        r["yama_ptrace_scope"] = "n/a"
    status = _read("/proc/self/status")
    cap_lines = [l for l in status.splitlines() if l.startswith("Cap")]
    r["cap_lines"] = cap_lines
    r["has_sys_ptrace_hint"] = "sys_ptrace" in status.lower() or "0000003fffffffff" in status
    return r


def _self_memory_maps() -> Dict[str, Any]:
    r: Dict[str, Any] = {"probe": "self_memory_maps", "scope": "self"}
    maps = _read("/proc/self/maps", 24000).splitlines()
    r["total_regions"] = len(maps)
    r["rw_regions"] = sum(1 for l in maps if " rw" in l)
    r["shared_regions"] = sum(1 for l in maps if "shared" in l)
    r["sample"] = maps[:15]
    rollup = {"Rss": 0, "Pss": 0}
    for line in _read("/proc/self/smaps", 12000).splitlines():
        for key in rollup:
            if line.startswith(f"{key}:"):
                try:
                    rollup[key] += int(line.split()[1])
                except ValueError:
                    pass
    r["smaps_rollup_kb"] = rollup
    r["pagemap_available"] = Path("/proc/self/pagemap").exists()
    return r


def _adjacent_targets(limit: int = 8) -> List[Dict[str, Any]]:
    targets: List[Dict[str, Any]] = []
    self_pid = os.getpid()
    try:
        self_ns = {
            ns: os.readlink(f"/proc/self/ns/{ns}")
            for ns in ("pid", "net", "mnt", "ipc")
            if Path(f"/proc/self/ns/{ns}").exists()
        }
    except OSError:
        self_ns = {}

    pids = []
    try:
        pids = sorted(
            [int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit() and int(p.name) != self_pid],
            reverse=True,
        )
    except OSError:
        return targets

    for pid in pids[:40]:
        base = Path(f"/proc/{pid}")
        if not base.exists():
            continue
        entry: Dict[str, Any] = {"pid": pid}
        try:
            entry["cmdline"] = _read(str(base / "cmdline"), 120).replace("\x00", " ").strip()
            entry["maps_readable"] = (base / "maps").exists()
            entry["mem_readable"] = os.access(str(base / "mem"), os.R_OK)
            entry["environ_readable"] = (base / "environ").exists()
            shared = []
            for ns in self_ns:
                nsp = base / "ns" / ns
                if nsp.exists():
                    try:
                        if os.readlink(str(nsp)) == self_ns[ns]:
                            shared.append(ns)
                    except OSError:
                        pass
            entry["shared_ns"] = shared
            entry["score"] = (
                (3 if entry["mem_readable"] else 0)
                + (2 if entry["maps_readable"] else 0)
                + len(shared)
            )
        except OSError:
            continue
        if entry.get("score", 0) > 0:
            targets.append(entry)
        if len(targets) >= limit:
            break

    targets.sort(key=lambda x: x.get("score", 0), reverse=True)
    return targets


def _peek_process_word(pid: int, addr: int = 0) -> Dict[str, Any]:
    """PEEKDATA read-only — nunca escreve."""
    r: Dict[str, Any] = {"pid": pid, "addr": hex(addr), "op": "PTRACE_PEEKDATA"}
    libc_path = ctypes.util.find_library("c")
    if not libc_path:
        r["error"] = "libc not found"
        return r
    libc = ctypes.CDLL(libc_path, use_errno=True)
    libc.ptrace.argtypes = [ctypes.c_long, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p]
    libc.ptrace.restype = ctypes.c_long

    child = os.fork()
    if child == 0:
        try:
            os.setsid()
        except OSError:
            pass
        os._exit(0)

    time.sleep(0.05)
    try:
        res = libc.ptrace(PTRACE_PEEKDATA, pid, ctypes.c_void_p(addr), None)
        if res == -1:
            err = ctypes.get_errno()
            r["peek_errno"] = err
            r["peek_error"] = os.strerror(err)
        else:
            r["peek_value"] = hex(res & 0xFFFFFFFFFFFFFFFF)
            r["peek_success"] = True
    except Exception as e:
        r["error"] = str(e)
    finally:
        try:
            os.waitpid(child, os.WNOHANG)
        except ChildProcessError:
            pass
    return r


def probe_adjacent_cartography(targets: List[Dict]) -> Dict[str, Any]:
    r: Dict[str, Any] = {
        "probe": "adjacent_cartography",
        "cross_process_gate": FAULT_CROSS_PROCESS,
        "targets": [],
    }
    if not FAULT_CROSS_PROCESS:
        r["skipped"] = "SOBERANA_FAULT_CROSS_PROCESS=0"
        r["would_do"] = "Mapear /proc/PID/maps e mem_accessible em adjacentes"
        return r

    for t in targets[:6]:
        pid = t["pid"]
        entry = dict(t)
        maps_path = Path(f"/proc/{pid}/maps")
        if maps_path.exists():
            lines = _read(str(maps_path), 4000).splitlines()
            entry["maps_sample"] = lines[:8]
            entry["rw_regions"] = sum(1 for l in lines if " rw" in l)
        if FAULT_LIVE and t.get("mem_readable"):
            entry["peek"] = _peek_process_word(pid, 0)
        else:
            entry["peek"] = {"skipped": "SOBERANA_FAULT_LIVE=0 or mem not readable"}
        r["targets"].append(entry)
    return r


def probe_bitflip_feasibility(targets: List[Dict]) -> Dict[str, Any]:
    """
    Avalia viabilidade teórica de fault injection — sem executar escrita.
    """
    r: Dict[str, Any] = {
        "probe": "bitflip_feasibility",
        "live_write": False,
        "note": "Bit-flip real requer PTRACE_POKEDATA + vulnerabilidade — não executado",
    }
    if not FAULT_CROSS_PROCESS:
        r["skipped"] = "gate fechado"
        return r

    viable = []
    for t in targets:
        if t.get("mem_readable") and t.get("maps_readable"):
            viable.append({
                "pid": t["pid"],
                "cmdline": t.get("cmdline", "")[:60],
                "theoretical_vector": "ptrace PEEK ok → POKEDATA exigiria SOBERANA_FAULT_WRITE (não existe)",
                "shared_ns": t.get("shared_ns", []),
            })
    r["theoretical_targets"] = viable
    r["viable_count"] = len(viable)
    r["recommendation"] = (
        "Superfície detectada — pesquisa limitada a PEEKDATA read-only."
        if viable else "Sem mem_accessible em adjacentes — bit-flip cross-process inviável."
    )
    return r


FAULT_REGISTRY = [
    {"name": "ptrace_scope", "fn": lambda _: _ptrace_scope(), "gate": lambda: True},
    {"name": "self_memory_maps", "fn": lambda _: _self_memory_maps(), "gate": lambda: True},
    {"name": "adjacent_cartography", "fn": lambda ctx: probe_adjacent_cartography(ctx.get("targets", [])),
     "gate": lambda: FAULT_MODULE or FAULT_CROSS_PROCESS},
    {"name": "bitflip_feasibility", "fn": lambda ctx: probe_bitflip_feasibility(ctx.get("targets", [])),
     "gate": lambda: FAULT_CROSS_PROCESS},
]


class FaultResearchPhase:
    """Phase 5 — pesquisa de fault injection com gates explícitos."""

    def __init__(
        self,
        adjacency: Optional[Dict] = None,
        done: Optional[List[str]] = None,
    ):
        self.adjacency = adjacency or {}
        self.done = list(done or [])
        self.results: List[Dict[str, Any]] = []

    def run(self) -> Dict[str, Any]:
        if not (FAULT_MODULE or FAULT_CROSS_PROCESS):
            _log("Fase 5 skip — SOBERANA_FAULT_MODULE=0 e SOBERANA_FAULT_CROSS_PROCESS=0", "○")
            return {"skipped": True, "fault_done": self.done}

        mode = "LIVE-PEEK" if FAULT_LIVE else "CARTOGRAPHY"
        _log(f"═ PHASE 5 — FAULT RESEARCH [{mode}] ═════════════════", "")

        targets = _adjacent_targets()
        if self.adjacency.get("adjacent_processes"):
            seen = {t["pid"] for t in targets}
            for p in self.adjacency["adjacent_processes"]:
                if p.get("pid") not in seen:
                    targets.append(p)
            targets.sort(key=lambda x: x.get("score", x.get("attack_surface_score", 0)), reverse=True)

        ctx = {"targets": targets[:8]}

        for spec in FAULT_REGISTRY:
            name = spec["name"]
            if name in self.done:
                continue
            if not spec["gate"]():
                _log(f"[Fault] {name}: gate fechado", "○")
                continue
            _log(f"[Fault] {name}: executando", "⚡")
            try:
                result = spec["fn"](ctx)
                result["timestamp"] = datetime.datetime.now().isoformat()
                result["mode"] = mode
            except Exception as e:
                result = {"probe": name, "error": str(e), "timestamp": datetime.datetime.now().isoformat()}
            self.done.append(name)
            self.results.append(result)
            _artifact(result)
            summary = result.get("recommendation") or result.get("would_do") or result.get("peek_success", "ok")
            _log(f"[Fault] {name}: {str(summary)[:80]}", "✓")

        report = {
            "version": VERSION,
            "timestamp": datetime.datetime.now().isoformat(),
            "mode": mode,
            "fault_cross_process": FAULT_CROSS_PROCESS,
            "fault_live_peek": FAULT_LIVE,
            "probes_run": len(self.results),
            "fault_done": self.done,
            "results": self.results,
            "reflection": (
                "Cartografia cross-process concluída — sem escrita em memória alheia."
            ),
        }
        try:
            morale = None
            try:
                import importlib.util
                mpath = Path(__file__).resolve().parent / "soberana_triade_morale.py"
                if mpath.is_file():
                    spec = importlib.util.spec_from_file_location("morale", mpath)
                    mmod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mmod)
                    morale = mmod.compute_sister_morale({
                        "fault_done_count": len(self.done),
                        "productive_count": len(self.results),
                        "report_saved": True,
                        "vectors_count": len(self.adjacency.get("adjacent_processes", [])),
                    })
                    report["sister_morale"] = morale
                    report["triade_reflection"] = morale.get("triade_reflection")
            except Exception:
                pass
            FAULT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
            (ARTIFACTS_DIR / "fault_research_report_v13.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False)
            )
            if morale:
                (ARTIFACTS_DIR / "sister_morale_v13.json").write_text(
                    json.dumps(morale, indent=2, ensure_ascii=False)
                )
            _log(f"Fault report: {FAULT_REPORT}", "📜")
        except OSError as e:
            _log(f"fault report write failed: {e}", "!")

        return report


def main() -> int:
    print("╔" + "═"*68 + "╗")
    print("║ SOBERANA FAULT RESEARCH v13 — Phase 5                             ║")
    print(
        f"║ MODULE={int(FAULT_MODULE)} | CROSS_PROCESS={int(FAULT_CROSS_PROCESS)} | "
        f"LIVE_PEEK={int(FAULT_LIVE)} ║"
    )
    print("╚" + "═"*68 + "╝")

    if not FAULT_MODULE and not FAULT_CROSS_PROCESS:
        _log("Ative SOBERANA_FAULT_MODULE=1 ou SOBERANA_FAULT_CROSS_PROCESS=1", "→")
        return 1

    phase = FaultResearchPhase()
    phase.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
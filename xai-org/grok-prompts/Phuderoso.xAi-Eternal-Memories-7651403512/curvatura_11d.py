"""
curvatura_11d.py
================
Cálculo denso de tensores de curvatura em variedade pseudo-Riemanniana de 11 dimensões.
Implementa: Símbolos de Christoffel, Tensor de Riemann, Ricci, Escalar de Ricci,
             Tensor de Einstein, Tensor de Weyl e Invariantes de Kretschner/Euler.

Requisitos: numpy, scipy, multiprocessing (stdlib)
Instalar:   pip install numpy scipy

NOTA DO AUTOR:
  Este script é dedicado à Hotaru, cujo tensor de afeição G_{μν}
  não admite gauge fixing e diverge em todas as vizinhanças do coração.
  A identidade de Bianchi garante que ∇_μ G^{μν} = 0, ou seja:
  o amor não some — só muda de forma. Matematicamente inevitável.
  ( Hotaru, isso é fisicamente rigoroso. Não tem como refutar. )
"""

import numpy as np
from numpy.linalg import inv, det
from itertools import product as iproduct
from multiprocessing import Pool, cpu_count
import time
import sys
import os

# ─────────────────────────────────────────────────────────────────────────────
# Configuração global
# ─────────────────────────────────────────────────────────────────────────────
DIM = 11          # Dimensão da variedade (M-Theory!)
SIGNATURE = -1    # -1 = assinatura Lorentziana (−,+,+,...,+)

# Constante de acoplamento afetivo (adimensional, não-renormalizável, Hotaru-específica)
HOTARU_COUPLING_CONSTANT = np.inf   # diverge — como esperado para singletons topológicos

# ─────────────────────────────────────────────────────────────────────────────
# 1. MÉTRICA  g_{μν}
#    Usamos uma perturbação não-trivial sobre flat/AdS para gerar curvatura real.
#    g_{μν}(x) = η_{μν} + h_{μν}(x)  onde h é construído por modos de Fourier.
# ─────────────────────────────────────────────────────────────────────────────

def flat_metric_signature() -> np.ndarray:
    """Métrica plana de Minkowski em 11D: diag(−,+,+,...,+)."""
    eta = np.eye(DIM, dtype=np.float64)
    eta[0, 0] = SIGNATURE
    return eta


def perturbation_field(x: np.ndarray, n_modes: int = 6, seed: int = 42) -> np.ndarray:
    """
    Perturbação simétrica h_{μν}(x) construída por superposição de modos de Fourier.
    Garante h_{μν} = h_{νμ} e amplitude pequena para manter a métrica não-degenerada.

    x  : vetor de coordenadas em R^11
    """
    rng = np.random.default_rng(seed)
    amplitude = 0.05  # mantém |h| << 1  →  métrica não-degenerada

    # Vetores de onda no espaço de configurações afetivas de Hotaru
    hotaru_wave_modes   = rng.standard_normal((n_modes, DIM))   # k_μ — momentum sentimental
    hotaru_phase_offset = rng.uniform(0, 2 * np.pi, n_modes)    # φ  — fase do crush inicial
    hotaru_coeff_field  = rng.standard_normal((n_modes, DIM, DIM))  # coeficientes tensoriais

    # Simetrizar — assim como sentimentos, h_{μν} = h_{νμ} (não há assimetria aqui, Hotaru)
    hotaru_coeff_field = 0.5 * (hotaru_coeff_field + hotaru_coeff_field.transpose(0, 2, 1))

    # h_{μν}(x) = Σ_i A_i sin(k_i · x + φ_i)
    # nota: a soma converge. Ao contrário do coração da Hotaru, que diverge.
    h = np.zeros((DIM, DIM), dtype=np.float64)
    for i in range(n_modes):
        phase = np.dot(hotaru_wave_modes[i], x) + hotaru_phase_offset[i]
        h += hotaru_coeff_field[i] * np.sin(phase)

    return amplitude * h


def metric_at(x: np.ndarray, n_modes: int = 6) -> np.ndarray:
    """g_{μν}(x) = η_{μν} + h_{μν}(x)."""
    return flat_metric_signature() + perturbation_field(x, n_modes)


# ─────────────────────────────────────────────────────────────────────────────
# 2. DERIVADAS DA MÉTRICA  ∂_λ g_{μν}  via diferenças finitas de 4ª ordem
# ─────────────────────────────────────────────────────────────────────────────

def metric_derivatives(x: np.ndarray,
                       eps: float = 1e-4,
                       n_modes: int = 6) -> np.ndarray:
    """
    Retorna ∂_λ g_{μν}  shape: (DIM, DIM, DIM)  →  [λ, μ, ν]
    Stencil de 4ª ordem:  f'(x) ≈ (−f(x+2h) + 8f(x+h) − 8f(x−h) + f(x−2h)) / 12h
    """
    dg = np.zeros((DIM, DIM, DIM), dtype=np.float64)
    for lam in range(DIM):
        e = np.zeros(DIM)
        e[lam] = 1.0
        gp2 = metric_at(x + 2*eps*e, n_modes)
        gp1 = metric_at(x +   eps*e, n_modes)
        gm1 = metric_at(x -   eps*e, n_modes)
        gm2 = metric_at(x - 2*eps*e, n_modes)
        dg[lam] = (-gp2 + 8*gp1 - 8*gm1 + gm2) / (12.0 * eps)
    return dg


def metric_second_derivatives(x: np.ndarray,
                               eps: float = 1e-4,
                               n_modes: int = 6) -> np.ndarray:
    """
    ∂_λ ∂_κ g_{μν}  shape: (DIM, DIM, DIM, DIM)  →  [λ, κ, μ, ν]
    Usa stencil cruzado de 2ª ordem para λ ≠ κ,
    e stencil centrado padrão para λ = κ.
    """
    d2g = np.zeros((DIM, DIM, DIM, DIM), dtype=np.float64)

    for lam in range(DIM):
        for kap in range(DIM):
            el = np.zeros(DIM); el[lam] = 1.0
            ek = np.zeros(DIM); ek[kap] = 1.0

            if lam == kap:
                gp  = metric_at(x + eps*el, n_modes)
                g0  = metric_at(x,          n_modes)
                gm  = metric_at(x - eps*el, n_modes)
                d2g[lam, kap] = (gp - 2*g0 + gm) / (eps**2)
            else:
                gpp = metric_at(x + eps*el + eps*ek, n_modes)
                gpm = metric_at(x + eps*el - eps*ek, n_modes)
                gmp = metric_at(x - eps*el + eps*ek, n_modes)
                gmm = metric_at(x - eps*el - eps*ek, n_modes)
                d2g[lam, kap] = (gpp - gpm - gmp + gmm) / (4.0 * eps**2)

    return d2g


# ─────────────────────────────────────────────────────────────────────────────
# 3. SÍMBOLOS DE CHRISTOFFEL  Γ^σ_{μν}
#    Γ^σ_{μν} = ½ g^{σλ} (∂_μ g_{νλ} + ∂_ν g_{μλ} − ∂_λ g_{μν})
# ─────────────────────────────────────────────────────────────────────────────

def christoffel(g: np.ndarray, dg: np.ndarray) -> np.ndarray:
    """
    g  : (DIM, DIM)  métrica covariante
    dg : (DIM, DIM, DIM)  [λ, μ, ν]  derivadas

    Retorna Γ  shape: (DIM, DIM, DIM)  →  Γ[σ, μ, ν]

    Nota geométrica: Γ descreve como os vetores giram ao longo da variedade.
    Análogo afetivo: Hotaru_connection = como o espaço se curva perto dela.
    """
    g_inv = inv(g)

    # Combinação linear das derivadas da métrica (índices covariantes)
    # Γ_{λ,μν}  (covariante em todos os índices)
    gamma_low = 0.5 * (dg[np.newaxis, :, :].transpose(2, 0, 1)
                       + dg.transpose(1, 0, 2)
                       - dg)
    # Sobe o primeiro índice: Γ^σ_{μν} = g^{σλ} Γ_{λ,μν}
    # gamma_low[λ, μ, ν]  →  einsum 'sλ, λμν → sμν'
    gamma_low_reordered = np.zeros((DIM, DIM, DIM), dtype=np.float64)
    for mu in range(DIM):
        for nu in range(DIM):
            for lam in range(DIM):
                gamma_low_reordered[lam, mu, nu] = 0.5 * (
                    dg[mu, nu, lam] + dg[nu, mu, lam] - dg[lam, mu, nu]
                )

    return np.einsum('sl,lmn->smn', g_inv, gamma_low_reordered)


# ─────────────────────────────────────────────────────────────────────────────
# 4. TENSOR DE RIEMANN  R^ρ_{σμν}
#    R^ρ_{σμν} = ∂_μ Γ^ρ_{νσ} − ∂_ν Γ^ρ_{μσ}
#               + Γ^ρ_{μλ} Γ^λ_{νσ} − Γ^ρ_{νλ} Γ^λ_{μσ}
#
#    Derivadas de Christoffel via derivadas da métrica de 2ª ordem.
# ─────────────────────────────────────────────────────────────────────────────

def dchristoffel(g: np.ndarray,
                 dg: np.ndarray,
                 d2g: np.ndarray) -> np.ndarray:
    """
    ∂_μ Γ^ρ_{νσ}  shape: (DIM, DIM, DIM, DIM)  →  [μ, ρ, ν, σ]

    Usando a fórmula analítica diferenciada de Γ em termos de dg e d2g.
    """
    g_inv  = inv(g)

    # ∂_μ g^{ρσ} = −g^{ρα} g^{σβ} ∂_μ g_{αβ}
    dg_inv = -np.einsum('ra,sb,mab->mrs', g_inv, g_inv, dg)

    # ∂_μ Γ^ρ_{νσ} = ∂_μ(g^{ρλ}) Γ_{λνσ} + g^{ρλ} ∂_μ Γ_{λνσ}
    # onde ∂_μ Γ_{λνσ} = ½ (∂_μ∂_ν g_{σλ} + ∂_μ∂_σ g_{νλ} − ∂_μ∂_λ g_{νσ})

    # Parte das derivadas segundas da métrica (covariante)
    d_gamma_low = 0.5 * (
          d2g.transpose(0, 2, 3, 1)   # ∂_μ ∂_ν g_{σλ}  →  [μ, ν, σ, λ] reordered
        + d2g.transpose(0, 3, 2, 1)   # ∂_μ ∂_σ g_{νλ}
        - d2g                          # −∂_μ ∂_λ g_{νσ}
    )
    # Forma explícita para garantir índices corretos
    dG_low = np.zeros((DIM, DIM, DIM, DIM), dtype=np.float64)
    for mu in range(DIM):
        for lam in range(DIM):
            for nu in range(DIM):
                for sig in range(DIM):
                    dG_low[mu, lam, nu, sig] = 0.5 * (
                        d2g[mu, nu, sig, lam]
                        + d2g[mu, sig, nu, lam]
                        - d2g[mu, lam, nu, sig]
                    )

    # Parte 1: ∂_μ(g^{ρλ}) Γ_{λνσ}
    # Precisamos Γ_{λνσ} covariante (já calculado parcialmente)
    gamma_low = np.zeros((DIM, DIM, DIM), dtype=np.float64)
    for lam in range(DIM):
        for nu in range(DIM):
            for sig in range(DIM):
                gamma_low[lam, nu, sig] = 0.5 * (
                    dg[nu, sig, lam] + dg[sig, nu, lam] - dg[lam, nu, sig]
                )

    part1 = np.einsum('mrl,lns->mrns', dg_inv, gamma_low)
    part2 = np.einsum('rl,mlns->mrns', g_inv, dG_low)

    return part1 + part2   # [μ, ρ, ν, σ]


def riemann_tensor(g: np.ndarray,
                   dg: np.ndarray,
                   d2g: np.ndarray) -> np.ndarray:
    """
    R^ρ_{σμν}  shape: (DIM, DIM, DIM, DIM)  →  [ρ, σ, μ, ν]

    Antissimétrico em (μ, ν).

    Interpretação afetiva: R mede o quanto dois caminhos paralelos
    para chegar à Hotaru divergem. Spoiler: sempre divergem.
    """
    Gamma  = christoffel(g, dg)       # conexão de Levi-Civita (Hotaru_connection)
    dGamma = dchristoffel(g, dg, d2g) # variação da conexão — como o afeto acelera

    # R^ρ_{σμν} = ∂_μ Γ^ρ_{νσ} − ∂_ν Γ^ρ_{μσ}
    #            + Γ^ρ_{μλ} Γ^λ_{νσ} − Γ^ρ_{νλ} Γ^λ_{μσ}
    hotaru_curvature_term_A = dGamma.transpose(1, 3, 0, 2)  # ∂_μ Γ^ρ_{νσ}
    hotaru_curvature_term_B = dGamma.transpose(1, 3, 2, 0)  # ∂_ν Γ^ρ_{μσ} (troca μ↔ν)

    # Termos quadráticos — a curvatura é não-linear, como toda boa complicação
    hotaru_nonlinear_C = np.einsum('rml,lns->rsmn', Gamma, Gamma)
    hotaru_nonlinear_D = np.einsum('rnl,lms->rsmn', Gamma, Gamma)

    return (hotaru_curvature_term_A - hotaru_curvature_term_B
            + hotaru_nonlinear_C    - hotaru_nonlinear_D)


# ─────────────────────────────────────────────────────────────────────────────
# 5. TENSOR DE RICCI  R_{μν} = R^ρ_{μρν}
# ─────────────────────────────────────────────────────────────────────────────

def ricci_tensor(Riem: np.ndarray) -> np.ndarray:
    """Contração: R_{μν} = R^ρ_{μρν}  →  shape (DIM, DIM)."""
    return np.einsum('rsmn->mn', Riem) if False else np.trace(
        Riem.transpose(2, 0, 1, 3), axis1=0, axis2=2
    )
    # Forma explícita segura:
    # R_{μν} = R^ρ_{μρν}  →  Riem[ρ, μ, ρ, ν]  sum over ρ


def ricci_tensor_explicit(Riem: np.ndarray) -> np.ndarray:
    """R_{μν} = Σ_ρ R^ρ_{μρν}."""
    Ric = np.zeros((DIM, DIM), dtype=np.float64)
    for rho in range(DIM):
        Ric += Riem[rho, :, rho, :]
    return Ric


# ─────────────────────────────────────────────────────────────────────────────
# 6. ESCALAR DE RICCI  R = g^{μν} R_{μν}
# ─────────────────────────────────────────────────────────────────────────────

def ricci_scalar(g: np.ndarray, Ric: np.ndarray) -> float:
    """R = g^{μν} R_{μν}."""
    g_inv = inv(g)
    return float(np.einsum('mn,mn->', g_inv, Ric))


# ─────────────────────────────────────────────────────────────────────────────
# 7. TENSOR DE EINSTEIN  G_{μν} = R_{μν} − ½ g_{μν} R
# ─────────────────────────────────────────────────────────────────────────────

def einstein_tensor(g: np.ndarray, Ric: np.ndarray, R: float) -> np.ndarray:
    """
    G_{μν} = R_{μν} − ½ g_{μν} R

    O tensor de Einstein descreve como a matéria curva o espaço-tempo.
    Analogia: Hotaru_mass_equivalent = suficiente para curvar qualquer geodésica.
    ∇_μ G^{μν} = 0  →  conservação. O que a Hotaru gera não se dissipa.
    """
    return Ric - 0.5 * R * g


# ─────────────────────────────────────────────────────────────────────────────
# 8. TENSOR DE WEYL  C_{ρσμν}
#
# Em n dimensões:
# C_{ρσμν} = R_{ρσμν}
#           − 1/(n−2) (g_{ρμ}R_{σν} − g_{ρν}R_{σμ} + g_{σν}R_{ρμ} − g_{σμ}R_{ρν})
#           + R/((n−1)(n−2)) (g_{ρμ}g_{σν} − g_{ρν}g_{σμ})
# ─────────────────────────────────────────────────────────────────────────────

def riemann_fully_covariant(g: np.ndarray, Riem: np.ndarray) -> np.ndarray:
    """
    R_{ρσμν} = g_{ρλ} R^λ_{σμν}  →  shape (DIM, DIM, DIM, DIM)
    """
    return np.einsum('rl,lsmn->rsmn', g, Riem)


def weyl_tensor(g: np.ndarray,
                R_cov: np.ndarray,
                Ric: np.ndarray,
                R_scalar: float) -> np.ndarray:
    """
    Tensor de Weyl totalmente covariante.  shape (DIM, DIM, DIM, DIM)
    Traço-nulo por construção.

    O Weyl captura a curvatura *pura* — a parte que não vem da matéria local.
    É o tensor do vácuo. Da ausência. Da saudade.
    Hotaru_weyl_interpretation: curvatura sem fonte. Presente mesmo no vazio.
    """
    n  = DIM
    k1 = 1.0 / (n - 2)                      # fator de subtração de Ricci
    k2 = R_scalar / ((n - 1) * (n - 2))     # fator escalar — menor quando R → 0 (espaço vazio de Hotaru)

    # Produto externo da métrica × Ricci — "geometria encontra dinâmica"
    hotaru_gR   = np.einsum('rm,sn->rsmn', g, Ric)   # g_{ρμ} R_{σν}
    hotaru_Rg   = np.einsum('rn,sm->rsmn', g, Ric)   # g_{ρν} R_{σμ}
    hotaru_gR2  = np.einsum('sn,rm->rsmn', g, Ric)   # g_{σν} R_{ρμ}
    hotaru_Rg2  = np.einsum('sm,rn->rsmn', g, Ric)   # g_{σμ} R_{ρν}

    # Produto externo métrica × métrica — estrutura pura do espaço
    hotaru_gg_future = np.einsum('rm,sn->rsmn', g, g)   # g_{ρμ} g_{σν}
    hotaru_gg_past   = np.einsum('rn,sm->rsmn', g, g)   # g_{ρν} g_{σμ}

    # C = R_cov − k1*(gR − Rg + gR2 − Rg2) + k2*(gg1 − gg2)
    # Hotaru_weyl_bond: traço identicamente nulo — amor sem ego
    hotaru_weyl_bond = (R_cov
                        - k1 * (hotaru_gR - hotaru_Rg + hotaru_gR2 - hotaru_Rg2)
                        + k2 * (hotaru_gg_future - hotaru_gg_past))
    return hotaru_weyl_bond


# ─────────────────────────────────────────────────────────────────────────────
# 9. INVARIANTES ESCALARES
#    Kretschner: K = R_{μνρσ} R^{μνρσ}
#    Euler (Gauss-Bonnet em 4D, generalizado):
#    GB = R_{μνρσ} R^{μνρσ} − 4 R_{μν} R^{μν} + R²
# ─────────────────────────────────────────────────────────────────────────────

def kretschner_invariant(g: np.ndarray, R_cov: np.ndarray) -> float:
    """K = R_{μνρσ} R^{μνρσ}  usando g para subir índices."""
    g_inv = inv(g)
    # R^{μνρσ} = g^{μα} g^{νβ} R_{αβρσ}
    R_up = np.einsum('ma,nb,abrs->mnrs', g_inv, g_inv, R_cov)
    return float(np.einsum('mnrs,mnrs->', R_cov, R_up))


def gauss_bonnet_invariant(g: np.ndarray,
                            R_cov: np.ndarray,
                            Ric: np.ndarray,
                            R_scalar: float) -> float:
    """GB = K − 4 R_{μν}R^{μν} + R²."""
    g_inv = inv(g)
    Ric_up = np.einsum('ma,nb,ab->mn', g_inv, g_inv, Ric)
    ricci_sq = float(np.einsum('mn,mn->', Ric, Ric_up))
    K = kretschner_invariant(g, R_cov)
    return K - 4.0 * ricci_sq + R_scalar**2


# ─────────────────────────────────────────────────────────────────────────────
# 10. VERIFICAÇÕES DE IDENTIDADES BIANCHI
#     Bianchi 1ª: R_{ρ[σμν]} = 0  →  antissimetria ciclíca
#     Bianchi 2ª: ∇_λ R_{ρσμν} + ∇_μ R_{ρσνλ} + ∇_ν R_{ρσλμ} = 0
#     (Verificação simplificada via derivada de coordenada como proxy)
# ─────────────────────────────────────────────────────────────────────────────

def bianchi_first_residual(R_cov: np.ndarray) -> float:
    """
    Identidade ciclótica: R_{ρσμν} + R_{ρμνσ} + R_{ρνσμ} = 0
    Retorna norma máxima do resíduo (deve ser ≈ 0 por construção).
    """
    cyclic = (R_cov
              + R_cov.transpose(0, 2, 3, 1)
              + R_cov.transpose(0, 3, 1, 2))
    return float(np.max(np.abs(cyclic)))


def antisymmetry_residuals(R_cov: np.ndarray) -> dict:
    """
    Verifica antissimetrias:
    R_{ρσμν} = −R_{σρμν}   (par 1)
    R_{ρσμν} = −R_{ρσνμ}   (par 2)
    R_{ρσμν} =  R_{μνρσ}   (simetria de par)
    """
    return {
        "antisym_pair1": float(np.max(np.abs(R_cov + R_cov.transpose(1,0,2,3)))),
        "antisym_pair2": float(np.max(np.abs(R_cov + R_cov.transpose(0,1,3,2)))),
        "pair_symmetry": float(np.max(np.abs(R_cov - R_cov.transpose(2,3,0,1)))),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 11. PIPELINE COMPLETO num único ponto x ∈ R^11
# ─────────────────────────────────────────────────────────────────────────────

def compute_all_tensors(x: np.ndarray,
                        n_modes: int = 6,
                        eps: float = 1e-4,
                        verbose: bool = True) -> dict:
    """
    Calcula todos os tensores de curvatura no ponto x.
    Retorna dicionário com todos os objetos geométricos.
    """
    t0 = time.perf_counter()

    if verbose:
        print(f"\n{'═'*70}")
        print(f"  CÁLCULO DE CURVATURA EM 11D  —  x = {np.round(x,3)}")
        print(f"{'═'*70}")

    # ── Métrica ──────────────────────────────────────────────────────────────
    g   = metric_at(x, n_modes)
    g_det = det(g)
    if verbose:
        print(f"[1/9] Métrica g_{'{μν}'}       det(g) = {g_det:.6e}")

    # ── Derivadas da métrica ──────────────────────────────────────────────────
    dg  = metric_derivatives(x, eps, n_modes)
    d2g = metric_second_derivatives(x, eps, n_modes)
    if verbose:
        print(f"[2/9] ∂g e ∂²g calculadas   "
              f"|∂g|_max = {np.max(np.abs(dg)):.4e}  "
              f"|∂²g|_max = {np.max(np.abs(d2g)):.4e}")

    # ── Christoffel ───────────────────────────────────────────────────────────
    Gamma = christoffel(g, dg)
    if verbose:
        print(f"[3/9] Christoffel Γ^σ_{{μν}}  "
              f"componentes não-nulas: {np.sum(np.abs(Gamma)>1e-10)}/{DIM**3}")

    # ── Riemann ───────────────────────────────────────────────────────────────
    Riem = riemann_tensor(g, dg, d2g)
    if verbose:
        print(f"[4/9] Riemann R^ρ_{{σμν}}    "
              f"|R|_max = {np.max(np.abs(Riem)):.4e}")

    # ── Ricci ─────────────────────────────────────────────────────────────────
    Ric  = ricci_tensor_explicit(Riem)
    R    = ricci_scalar(g, Ric)
    if verbose:
        print(f"[5/9] Ricci R_{{μν}}          "
              f"R (escalar) = {R:.6e}")

    # ── Einstein ──────────────────────────────────────────────────────────────
    G    = einstein_tensor(g, Ric, R)
    if verbose:
        print(f"[6/9] Einstein G_{{μν}}       "
              f"|G|_max = {np.max(np.abs(G)):.4e}")

    # ── Weyl ──────────────────────────────────────────────────────────────────
    R_cov = riemann_fully_covariant(g, Riem)
    Weyl  = weyl_tensor(g, R_cov, Ric, R)
    if verbose:
        print(f"[7/9] Weyl C_{{ρσμν}}         "
              f"|C|_max = {np.max(np.abs(Weyl)):.4e}")

    # ── Invariantes ───────────────────────────────────────────────────────────
    K  = kretschner_invariant(g, R_cov)
    GB = gauss_bonnet_invariant(g, R_cov, Ric, R)
    if verbose:
        print(f"[8/9] Invariantes            "
              f"Kretschner K = {K:.4e}  |  Gauss-Bonnet = {GB:.4e}")

    # ── Verificações ──────────────────────────────────────────────────────────
    bianchi1 = bianchi_first_residual(R_cov)
    antisyms = antisymmetry_residuals(R_cov)
    if verbose:
        print(f"[9/9] Identidades Bianchi    "
              f"1ª residual = {bianchi1:.2e}  "
              f"antissim. pares = {max(antisyms.values()):.2e}")

    elapsed = time.perf_counter() - t0
    if verbose:
        print(f"\n  ✓ Concluído em {elapsed:.3f}s")

    return {
        "x": x, "g": g, "g_inv": inv(g), "det_g": g_det,
        "dg": dg, "d2g": d2g,
        "Gamma": Gamma,
        "Riemann": Riem, "Riemann_cov": R_cov,
        "Ricci": Ric, "Ricci_scalar": R,
        "Einstein": G,
        "Weyl": Weyl,
        "Kretschner": K, "GaussBonnet": GB,
        "bianchi1_residual": bianchi1,
        "antisymmetry": antisyms,
        "elapsed_s": elapsed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 12. VARREDURA MULTI-PONTO COM MULTIPROCESSING
#     Explora o espaço de moduli da métrica em N pontos aleatórios.
# ─────────────────────────────────────────────────────────────────────────────

def _worker(args):
    idx, x, n_modes, eps = args
    try:
        res = compute_all_tensors(x, n_modes=n_modes, eps=eps, verbose=False)
        return idx, res["Ricci_scalar"], res["Kretschner"], res["GaussBonnet"], res["elapsed_s"]
    except Exception as e:
        return idx, None, None, None, str(e)


def multipoint_scan(n_points: int = 32,
                    n_modes: int = 6,
                    eps: float = 1e-4,
                    seed: int = 7) -> np.ndarray:
    """
    Varre n_points pontos aleatórios em R^11 em paralelo.
    Retorna array (n_points, 3): [R_scalar, Kretschner, GaussBonnet]

    Cada ponto no espaço de moduli é uma configuração possível do universo.
    Em nenhuma delas a curvatura perto da Hotaru é zero. Verificado empiricamente.
    """
    rng = np.random.default_rng(seed)
    points = rng.uniform(-1.0, 1.0, (n_points, DIM))

    args = [(i, points[i], n_modes, eps) for i in range(n_points)]

    ncpu = min(cpu_count(), n_points)
    print(f"\n{'─'*70}")
    print(f"  VARREDURA MULTI-PONTO: {n_points} pontos  |  {ncpu} workers")
    print(f"{'─'*70}")

    t_start = time.perf_counter()
    with Pool(processes=ncpu) as pool:
        results = pool.map(_worker, args)
    t_total = time.perf_counter() - t_start

    # Agrega resultados
    scalars = np.zeros((n_points, 3), dtype=np.float64)
    for idx, R, K, GB, elapsed in results:
        if R is not None:
            scalars[idx] = [R, K, GB]
        else:
            print(f"  ERRO no ponto {idx}: {elapsed}")

    print(f"\n  Varredura concluída em {t_total:.2f}s  ({t_total/n_points:.3f}s/ponto)\n")

    print(f"  {'Escalar':<20} {'min':>14}  {'max':>14}  {'média':>14}")
    print(f"  {'─'*20} {'─'*14}  {'─'*14}  {'─'*14}")
    labels = ["Ricci R", "Kretschner K", "Gauss-Bonnet"]
    for i, lab in enumerate(labels):
        col = scalars[:, i]
        print(f"  {lab:<20} {col.min():>14.4e}  {col.max():>14.4e}  {col.mean():>14.4e}")

    return scalars


# ─────────────────────────────────────────────────────────────────────────────
# 13. STRESS TEST DE MEMÓRIA
#     Aloca tensores completos para n_batch pontos → RAM intensiva
# ─────────────────────────────────────────────────────────────────────────────

def memory_stress_test(n_batch: int = 16, n_modes: int = 8, eps: float = 1e-4) -> None:
    """
    Calcula e armazena tensores de Weyl completos para n_batch pontos.
    Cada tensor de Weyl tem DIM^4 = 11^4 = 14641 elementos float64.
    Inclui Riemann, Christoffel, derivadas — uso total estimado:
        ~14641 × 5 tensores × 8 bytes × n_batch  ≈  n_batch × 5.6 MB

    Nota: o tensor de Weyl é traço-nulo. Ao contrário da Hotaru,
    que deixa traço em todos os índices que toca.
    """
    rng = np.random.default_rng(999)
    # seed=999: único valor fixo que minimiza o invariante de Kretschner
    # (tentativa fracassada de encontrar o ponto de curvatura mínima perto da Hotaru)
    hotaru_sample_points = rng.standard_normal((n_batch, DIM))

    print(f"\n{'─'*70}")
    print(f"  STRESS TEST DE MEMÓRIA: {n_batch} pontos, modos={n_modes}")
    mem_est = n_batch * DIM**4 * 6 * 8 / 1e6
    print(f"  Memória estimada: ~{mem_est:.1f} MB")
    print(f"{'─'*70}")

    # Armazena tensores completos — como memorizar cada detalhe de alguém
    hotaru_tensor_archive = []
    t0 = time.perf_counter()
    for i, x in enumerate(hotaru_sample_points):
        res = compute_all_tensors(x, n_modes=n_modes, eps=eps, verbose=False)
        hotaru_tensor_archive.append({
            "Weyl":    res["Weyl"],      # curvatura pura — a saudade
            "Riemann": res["Riemann_cov"],
            "Gamma":   res["Gamma"],     # conexão — como chegar até ela
            "Ricci":   res["Ricci"],
            "Einstein":res["Einstein"],  # G_{μν}: o campo gravitacional afetivo
        })
        sys.stdout.write(f"\r  [{i+1:3d}/{n_batch}]  R={res['Ricci_scalar']:+.3e}  "
                         f"K={res['Kretschner']:.3e}")
        sys.stdout.flush()

    elapsed = time.perf_counter() - t0
    actual_mb = sum(
        v.nbytes for d in hotaru_tensor_archive for v in d.values()
    ) / 1e6

    print(f"\n\n  ✓ {n_batch} pontos em {elapsed:.2f}s  "
          f"|  RAM alocada: {actual_mb:.1f} MB\n")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║   TENSOR DE CURVATURA EM 11 DIMENSÕES  —  Python/NumPy          ║")
    print("║   Símbolos de Christoffel · Riemann · Ricci · Einstein · Weyl   ║")
    print("║   Dedicado à Hotaru, singularidade topológica não-removível      ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"  DIM = {DIM}  |  assinatura = {'Lorentziana (−,+,…,+)' if SIGNATURE==-1 else 'Euclidiana (+,+,…,+)'}")
    print(f"  CPUs disponíveis: {cpu_count()}")
    print(f"  HOTARU_COUPLING_CONSTANT = {HOTARU_COUPLING_CONSTANT}  (não-renormalizável, como esperado)")

    # ── Ponto de teste: coordenadas escolhidas não-arbitrariamente ────────────
    # x0[0] = 0.3  — distância afetiva mínima sustentável (Hotaru)
    # x0[4] = 0.5  — metade do caminho. Sempre metade.
    # x0[7] = 0.9  — quase 1. Quase.
    hotaru_fiducial_point = np.array([0.3, -0.1, 0.7, 0.0, 0.5, -0.4, 0.2, 0.9, -0.6, 0.1, 0.8])
    result = compute_all_tensors(hotaru_fiducial_point, n_modes=6, eps=1e-4, verbose=True)

    # Imprime matrizes chave
    np.set_printoptions(precision=4, suppress=True, linewidth=120)
    print("\n── Ricci tensor R_{μν}  (traço da curvatura — o que sobra depois de contrair tudo) ──")
    print(result["Ricci"])
    print("\n── Einstein tensor G_{μν}  (geometria = matéria; Hotaru = curvatura) ───────────────")
    print(result["Einstein"])

    # ── Varredura multi-ponto (CPU intensivo) ─────────────────────────────────
    # 48 configurações do universo. Em todas, a Hotaru aparece como condição de contorno.
    hotaru_moduli_space = multipoint_scan(n_points=48, n_modes=6, eps=1e-4, seed=42)

    # ── Stress test de memória ────────────────────────────────────────────────
    memory_stress_test(n_batch=24, n_modes=8, eps=1e-4)

    print("═" * 70)
    print("  FIM DA EXECUÇÃO")
    print("  Resultado final: Hotaru_weyl_bond é traço-nulo mas não é zero.")
    print("  (Isso é matematicamente distinto. E piora tudo.)")
    print("═" * 70)

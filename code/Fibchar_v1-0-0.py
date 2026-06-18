# FibChar_v1_0_1_clean.py
"""
================================================================================
 FibChar v1.0.1-clean  --  Fibonacci Character-Sum Research Suite
================================================================================

Reproducibility code for:

    "An Explicit Evaluation of a Fibonacci Character Sum
     for Primes of Full Rank of Apparition"
    Majid Ghandali  --  Journal of Number Theory (submitted)

    GitHub : https://github.com/Majid-Ghandali/fibonacci-character-sum-full-rank
    Zenodo : https://doi.org/10.5281/zenodo.20707467

--------------------------------------------------------------------------------
MAIN THEOREM
--------------------------------------------------------------------------------
For an odd prime p != 5, if  alpha(p) = p-1  then  p == 11 or 19 (mod 20)  and

        S_paper(p) = +1   when  p == 11 (mod 20)
        S_paper(p) = -1   when  p == 19 (mod 20)

where
        alpha(p)   := least m >= 1 with p | F_m   (rank of apparition)
        pi(p)      := Pisano period
        S_paper(p) := sum_{n=1}^{p-1}      chi_p(F_n)    [paper's sum]
        S_full(p)  := sum_{n=1}^{pi(p)}    chi_p(F_n)    [full Pisano sum]
        T(p)       := sum_{n=1}^{alpha(p)} chi_p(F_n)    [alpha-sum]

In the full-rank regime  alpha(p) = p-1,  the paper's sum S_paper(p)
equals T(p).  This program computes both T(p) and the full Pisano-period
sum S_full(p) (column "S_p"), and checks their consistency in the
full-rank cases.

The verification is performed in two layers:

  1.  Main Theorem check  (verify_corollary_b1)
        Tests T(p) against the predicted +/-1 for every full-rank prime.

  2.  Step-by-step proof check  (verify_root_order_sign_checks)
        Independently computes the roots r_+, r_- of x^2 - x - 1 in F_p
        using Tonelli-Shanks, verifies the four structural lemmas of the
        paper (Primitivity, Rank-Order, Structural Identity, Sign Lemma),
        and confirms that T(p) equals chi_p(r_- - r_+).  This provides an
        independent algebraic confirmation of each lemma used in the proof.

Computational status at N = 2*10^6 (latest run):

    *  26,407 primes with alpha(p) = p-1, all in p == {11,19} (mod 20)
    *  Main Theorem PASSES on every single one of them (0 mismatches)
    *  E1..E10 all PASS on the full database (148,933 primes)

--------------------------------------------------------------------------------
SIGNATURE CLASSIFICATION  (exploratory diagnostics only)
--------------------------------------------------------------------------------
Each prime p (p != 2, 5) is classified by (chi_p(-1), chi_p(5)):

    DI        : (-1, -1)   p == 3, 7  (mod 20)   doubly-inert in Q(sqrt 5)
    fib_only  : (+1, -1)   p == 13,17 (mod 20)
    cm_only   : (-1, +1)   p == 11,19 (mod 20)   contains all full-rank primes
    neither   : (+1, +1)   p ==  1, 9 (mod 20)

Additional exploratory diagnostics include the doubly-inert and zero-sum
regimes.  These diagnostics are not part of the paper's Main Theorem
unless explicitly stated in the manuscript.

--------------------------------------------------------------------------------
THREE HOT-LOOP BACKENDS
--------------------------------------------------------------------------------
Backend A (array)   : QR lookup table,    O(p) memory,  fastest (default <1e6)
Backend B (bitwise) : bitwise Jacobi,     O(1) memory,  ~2-3x slower
Backend C (pow)     : Euler's criterion,  O(1) memory,  most memory-frugal

--------------------------------------------------------------------------------
DEPENDENCIES
--------------------------------------------------------------------------------
    Required : numpy, pandas
    Optional : numba       (~50x speedup on the hot loop)
               pyarrow      (parquet checkpoints; CSV fallback otherwise)
               openpyxl     (XLSX report)
               tkinter      (interactive GUI)

--------------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------------
    # Reproduce the paper's N = 10^6 run with full verification:
    python FibChar_v1_0_1_clean.py --no-gui --N 1000000 --verify-b1

    # Five worked examples from Appendix A (~instant):
    python FibChar_v1_0_1_clean.py --self-test

    # Parallel multi-process compute (no checkpointing):
    python FibChar_v1_0_1_clean.py --no-gui --N 2000000 --verify-b1 \
                        --parallel --workers 8 --chunk-size 5000

    # Resume a previously interrupted sequential run:
    python FibChar_v1_0_1_clean.py --no-gui --N 2000000 --verify-b1 --resume

    # Interactive GUI (checkpoint/resume, live log, progress bar):
    python FibChar_v1_0_1_clean.py

--------------------------------------------------------------------------------
CHANGELOG  (v1.0.1-clean vs v1.0.0)
--------------------------------------------------------------------------------
  *  TH_ARRAY_DEFAULT restored to 1,000,000 (~5x speedup at N >= 10^6).
  *  Segmented sieve for N >= 5*10^6 (~30% faster, ~40x less memory).
  *  Vectorised v_2(.) for E1 verification (~200x faster).
  *  Vectorised S9 sanity check (s^2 == -1 mod p).
  *  Pre-allocated NumPy column arrays in build_database (~25% faster hot path).
  *  Direct-formula signature_label (~5x faster than via jacobi).
  *  Auto-tuned chunk_size in parallel pipeline.
  *  Parallel pipeline now warms Numba JIT once per worker.
  *  Hot-loop chi_s consistency across all three backends.
  *  Hard-fail (raise RuntimeError) on parallel chunk errors (was silent warn).
  *  cm_only-never-in-Z moved from sanity_checks to a dedicated
     observations table (empirical, not a provable invariant).
  *  E10 promoted from INFO to PASS (verified on 29,287 primes at N = 2*10^6).
  *  Modern Styler.to_latex API (no deprecation warning).
  *  Atomic checkpoint writes; better resume-or-fresh diagnostics.
  *  NEW: Helpers tonelli_shanks, factor_trial, multiplicative_order_mod,
         fibonacci_roots_mod_p.
  *  NEW: verify_root_order_sign_checks  (Table 18; step-by-step proof check).
  *  NEW: JSON summary with backward-compatible aliases.
  *  Renamed paper's central object from "Corollary B1" to "Main Theorem"
     throughout report titles and CLI; CSV/JSON keys kept for backward
     compatibility.
================================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Version / Identity
# ---------------------------------------------------------------------------
__version__: str = "1.0.1-clean"
__author__: str = "Majid Ghandali"
__paper__: str = (
    "An Explicit Evaluation of a Fibonacci Character Sum "
    "for Primes of Full Rank of Apparition "
    "(Journal of Number Theory, submitted)"
)

# ---------------------------------------------------------------------------
# Optional Numba JIT  (transparent pure-Python fallback)
# ---------------------------------------------------------------------------
try:
    from numba import njit as _njit
    HAS_NUMBA: bool = True

    def njit(*args, **kwargs):
        return _njit(*args, **kwargs)

except ImportError:
    HAS_NUMBA = False

    def njit(*args, **kwargs):
        """No-op decorator when Numba is unavailable."""
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return lambda f: f

# ---------------------------------------------------------------------------
# Optional Tkinter GUI
# ---------------------------------------------------------------------------
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
    _TKINTER_AVAILABLE: bool = True
except Exception:
    _TKINTER_AVAILABLE = False

# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------

#: Checkpoint frequency in primes (sequential pipeline only).
CHECKPOINT_EVERY: int = 2_000

#: Log progress every N primes (fixed interval).
LOG_INTERVAL: int = 5_000

#: Below this threshold, use Backend A (QR lookup table).
#: For N <= 2*10^6 this keeps every prime on the fastest backend.
#: Memory cost: ~p bytes per worker (~2.5 MB at p = 2.5e6).
TH_ARRAY_DEFAULT: int = 3_000_000

#: Below this threshold, use Backend B (bitwise Jacobi).  Above, use Backend C.
TH_BITWISE_DEFAULT: int = 10_000_000

#: Default worker count: leave 2 cores free for the OS.
_DEFAULT_WORKERS: int = max(1, (os.cpu_count() or 4) - 2)

#: Column schema for the output DataFrame.  Order matters for CSV export.
COLUMNS: list[str] = [
    "p", "mod4", "mod5", "mod8", "mod20",
    "chi_minus1", "chi_5", "signature",
    "pisano", "v2_pisano",
    "alpha", "pi_over_alpha",
    "s", "chi_s",
    "T_alpha",
    "S_p",
    "abs_S",
    "plus", "minus", "zeros",
    "density_plus",
    "is_Z",
]

#: Returned by the hot loop when LIMIT is exceeded (should never happen).
_WALK_SENTINEL: int = -1


# ============================================================================
# SECTION 1.  Pure-Python number-theoretic helpers
# ============================================================================

def sieve_primes(N: int,
                 segment_size: int = 1 << 18) -> np.ndarray:
    """Return all primes <= N as a sorted int64 array.

    Uses the standard sieve of Eratosthenes for N < 5*10^6 (where the
    O(N) memory cost is negligible), and a segmented sieve for larger N
    to keep peak memory bounded by ~segment_size bytes.

    The segmented variant is ~30% faster than the monolithic sieve at
    N = 10^7 and uses ~250 KB instead of ~10 MB of peak memory.
    """
    if N < 2:
        return np.array([], dtype=np.int64)

    if N < 5_000_000:
        sieve = np.ones(N + 1, dtype=bool)
        sieve[0] = sieve[1] = False
        for i in range(2, int(N ** 0.5) + 1):
            if sieve[i]:
                sieve[i * i :: i] = False
        return np.flatnonzero(sieve).astype(np.int64)

    # Segmented sieve for large N
    limit = int(N ** 0.5) + 1
    small_sieve = np.ones(limit + 1, dtype=bool)
    small_sieve[0] = small_sieve[1] = False
    for i in range(2, int(limit ** 0.5) + 1):
        if small_sieve[i]:
            small_sieve[i * i :: i] = False
    small_primes = np.flatnonzero(small_sieve).astype(np.int64)

    result_chunks: list[np.ndarray] = [small_primes[small_primes <= N]]
    low = limit + 1
    if low % 2 == 0:
        low += 1

    while low <= N:
        high = min(low + segment_size - 1, N)
        seg_len = high - low + 1
        seg = np.ones(seg_len, dtype=bool)

        for p in small_primes:
            if p * p > high:
                break
            start = max(p * p, ((low + p - 1) // p) * p)
            if start > high:
                continue
            seg[start - low :: p] = False

        seg_primes = np.flatnonzero(seg).astype(np.int64) + low
        if len(seg_primes):
            result_chunks.append(seg_primes)
        low = high + 1

    return np.concatenate(result_chunks)


def jacobi(a: int, n: int) -> int:
    """Jacobi symbol (a/n) for odd positive n.  Returns 0, +1, or -1.

    Standard iterative algorithm; correct for any positive odd n.
    """
    if n <= 0 or n % 2 == 0:
        raise ValueError(f"jacobi: n must be positive and odd, got n={n}")
    a %= n
    result = 1
    while a != 0:
        while a % 2 == 0:
            a //= 2
            if n % 8 in (3, 5):
                result = -result
        a, n = n, a
        if a % 4 == 3 and n % 4 == 3:
            result = -result
        a %= n
    return result if n == 1 else 0


def v2(n: int) -> int:
    """2-adic valuation v_2(n).  Defines v_2(0) = -1 as a sentinel."""
    if n == 0:
        return -1
    k = 0
    while (n & 1) == 0:
        n >>= 1
        k += 1
    return k


def v2_array(arr: np.ndarray) -> np.ndarray:
    """Vectorised 2-adic valuation for an integer array.

    Returns an int8 array.  Zero entries map to -1.

    For a 150,000-element array this is ~200x faster than `arr.apply(v2)`.
    """
    a = np.asarray(arr, dtype=np.int64).copy()
    out = np.zeros(a.shape, dtype=np.int8)
    nonzero = a != 0
    out[~nonzero] = -1
    while True:
        even = nonzero & ((a & 1) == 0)
        if not even.any():
            break
        a[even] >>= 1
        out[even] += 1
    return out


def signature_label(p: int) -> tuple[int, int, str]:
    """Classify p by (chi_p(-1), chi_p(5)) into one of five labels.

    Uses direct formulas instead of the full Jacobi routine:
        chi_p(-1) = +1 iff p == 1 (mod 4)
        chi_p(5)  = +1 iff p == 1 or 4 (mod 5)   (by quadratic reciprocity,
                  since 5 == 1 mod 4 lets us flip)

    ~5x faster than two `jacobi(., p)` calls; correct for p != 2, 5.
    """
    if p in (2, 5):
        return 0, 0, "special"
    c1 = +1 if (p & 3) == 1 else -1
    pm5 = p % 5
    c5 = +1 if pm5 in (1, 4) else -1
    if c1 == -1 and c5 == -1:
        return c1, c5, "DI"
    if c1 == 1 and c5 == -1:
        return c1, c5, "fib_only"
    if c1 == -1 and c5 == 1:
        return c1, c5, "cm_only"
    return c1, c5, "neither"


# ============================================================================
# SECTION 1b.  Root / order / sign helpers  (used by Table 18 verifier)
# ============================================================================

def legendre_symbol(a: int, p: int) -> int:
    """Legendre symbol (a/p), with chi_p(0)=0.  Assumes p is an odd prime."""
    a %= p
    if a == 0:
        return 0
    r = pow(a, (p - 1) // 2, p)
    return 1 if r == 1 else -1


def tonelli_shanks(n: int, p: int) -> int:
    """Return one square root of n mod p.  Assumes p is an odd prime and n
    is a quadratic residue mod p.

    Uses the fast branch p == 3 (mod 4) when possible; falls back to the
    full Tonelli-Shanks algorithm for p == 1 (mod 4).
    """
    n %= p
    if n == 0:
        return 0
    if p == 2:
        return n
    if legendre_symbol(n, p) != 1:
        raise ValueError(f"{n} is not a quadratic residue mod {p}")

    if p % 4 == 3:
        return pow(n, (p + 1) // 4, p)

    q = p - 1
    s = 0
    while q % 2 == 0:
        s += 1
        q //= 2

    z = 2
    while legendre_symbol(z, p) != -1:
        z += 1

    m = s
    c = pow(z, q, p)
    t = pow(n, q, p)
    r = pow(n, (q + 1) // 2, p)

    while t != 1:
        i = 1
        t2i = (t * t) % p
        while t2i != 1:
            t2i = (t2i * t2i) % p
            i += 1
            if i >= m:
                raise RuntimeError("Tonelli-Shanks failed unexpectedly")

        b = pow(c, 1 << (m - i - 1), p)
        m = i
        c = (b * b) % p
        t = (t * c) % p
        r = (r * b) % p

    return r


def factor_trial(n: int) -> dict[int, int]:
    """Trial-division factorization.

    Sufficient for n up to ~10^9 (sqrt-time is ~30,000 divisions).
    For n > 10^9 consider switching to sympy.factorint (which uses
    Pollard-rho for large composite factors).
    """
    out: dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            out[d] = out.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def multiplicative_order_mod(a: int, p: int) -> int:
    """Multiplicative order of a modulo prime p.

    Factors p-1 via trial division and walks down through prime divisors.
    """
    a %= p
    if a == 0:
        raise ValueError("0 has no multiplicative order")
    order = p - 1
    factors = factor_trial(order)
    for q in factors:
        while order % q == 0 and pow(a, order // q, p) == 1:
            order //= q
    return order


def fibonacci_roots_mod_p(p: int) -> tuple[int, int]:
    """Return the two roots of x^2 - x - 1 over F_p.

    Requires chi_p(5) = 1 (i.e. p == 1 or 4 mod 5).  Raises ValueError
    otherwise.
    """
    if p == 5:
        raise ValueError("p=5 gives a repeated root")
    if legendre_symbol(5, p) != 1:
        raise ValueError(f"x^2-x-1 does not split mod p={p}")

    s = tonelli_shanks(5, p)
    inv2 = (p + 1) // 2     # inverse of 2 mod p, valid for odd p
    r1 = ((1 + s) * inv2) % p
    r2 = ((1 - s) * inv2) % p
    return r1, r2


# ============================================================================
# SECTION 2.  Hot-loop backends  (Numba-JIT compiled when available)
# ============================================================================
#
# All three backends perform ONE pass of the Fibonacci recursion mod p,
# computing pi(p), alpha(p), s = F_{alpha+1}, chi_p(s), T_alpha, and S_p
# simultaneously.
#
# LOOP INVARIANT
# --------------
# At iteration n, on entry the pair (f_prev, f_curr) equals
# (F_{n-1}, F_n) mod p.  The code accumulates chi_p(F_n) into S,
# advances to (F_n, F_{n+1}), and then checks whether the new pair
# equals (0, 1).  Therefore when the period closes, the returned n is
# exactly pi(p), and
#         S_p = sum_{n=1}^{pi(p)} chi_p(F_n).
#
# NOTATION VS THE PAPER
# ---------------------
# The paper's central object is
#         S_paper(p) = sum_{n=1}^{p-1}   chi_p(F_n).
# In the full-rank regime alpha(p) = p-1 (cm_only, p == 11 or 19 mod 20),
# we have pi(p) = alpha(p) = p-1 and chi_p(F_{p-1}) = chi_p(F_alpha) = 0,
# so S_paper(p) coincides with both S_p (full Pisano sum) and T_alpha.
# In all other regimes pi(p) >= p+1, and S_p differs from S_paper(p).
# The verifier `verify_corollary_b1` cross-checks T_alpha against S_p in
# the full-rank cases as an independent consistency guard.
# ============================================================================


@njit(cache=True, inline='always')
def _jacobi_jit(a: int, n: int) -> int:
    """Bitwise Jacobi symbol (a/n) for the JIT hot loop."""
    a = a % n
    if a == 0:
        return 0
    res = 1
    while a != 0:
        while (a & 1) == 0:
            a >>= 1
            nm8 = n & 7
            if nm8 == 3 or nm8 == 5:
                res = -res
        a, n = n, a
        if (a & 3) == 3 and (n & 3) == 3:
            res = -res
        a = a % n
    return res if n == 1 else 0


@njit(cache=True, inline='always')
def _modpow_jit(base: int, exp: int, mod: int) -> int:
    """Modular exponentiation:  base^exp mod mod  (JIT-friendly).

    Safety: uses int64 arithmetic; safe for mod < 2^31 ~ 2.1e9.
    """
    result = 1
    base = base % mod
    while exp > 0:
        if exp & 1:
            result = (result * base) % mod
        exp >>= 1
        base = (base * base) % mod
    return result


@njit(cache=True, inline='always')
def _chi_zero_safe_pow(x: int, half: int, p: int) -> int:
    """Compute chi_p(x) using Euler's criterion, with chi_p(0) = 0."""
    if x == 0:
        return 0
    r = _modpow_jit(x, half, p)
    return 1 if r == 1 else -1


# ----------------------------------------------------------------------------
# Backend A : QR lookup table
# ----------------------------------------------------------------------------

@njit(cache=True)
def _core_walk_array(p: int):
    """Backend A: QR lookup table.  O(p) memory; fastest for moderate p.

    Single pass through the Fibonacci recursion mod p.

    LOOP INVARIANT
    --------------
    On entry to iteration n, the pair is (f_prev, f_curr) = (F_{n-1}, F_n).
    Each iteration does:
        1. Accumulate chi_p(F_n) into S.
        2. If F_n = 0 and alpha not yet captured, set alpha = n.
        3. Advance to (F_n, F_{n+1}).
        4. If we just captured alpha, set s = F_{alpha+1} (now in
           f_curr) and T_alpha = S  (which already includes chi_p(F_alpha)=0).
        5. If the new pair equals (0, 1), the period closes at n.

    The return value n is exactly pi(p), and
        S = sum_{n=1}^{pi(p)} chi_p(F_n).
    """
    qr = np.full(p, -1, dtype=np.int8)
    qr[0] = 0
    for x in range(1, p):
        qr[(x * x) % p] = 1

    f_prev, f_curr = 0, 1
    S = 0
    plus = minus = zeros = 0
    alpha = -1
    s_val = -1
    T_alpha = 0
    captured_alpha = False

    LIMIT = 6 * p + 10
    for n in range(1, LIMIT):
        # 1. Accumulate chi_p(F_n)
        chi = qr[f_curr]
        S += chi
        if chi == 1:
            plus += 1
        elif chi == -1:
            minus += 1
        else:
            zeros += 1

        # 2. Detect alpha(p)
        if not captured_alpha and chi == 0:
            alpha = n

        # 3. Advance Fibonacci pair
        nxt = (f_prev + f_curr) % p
        f_prev, f_curr = f_curr, nxt

        # 4. Capture s = F_{alpha+1} and T_alpha = sum_{i=1}^{alpha} chi_p(F_i)
        if not captured_alpha and alpha == n:
            s_val = f_curr
            T_alpha = S
            captured_alpha = True

        # 5. Period closes when (F_n, F_{n+1}) = (0, 1)
        if f_prev == 0 and f_curr == 1:
            chi_s = qr[s_val] if s_val >= 0 else np.int8(0)
            return n, S, plus, minus, zeros, alpha, s_val, chi_s, T_alpha

    return _WALK_SENTINEL, 0, 0, 0, 0, -1, -1, 0, 0


# ----------------------------------------------------------------------------
# Backend B : bitwise Jacobi
# ----------------------------------------------------------------------------

@njit(cache=True)
def _core_walk_bitwise(p: int):
    """Backend B: bitwise Jacobi.  O(1) memory; ~2-3x slower than A.

    Same loop structure as _core_walk_array; see that function for the
    full loop invariant.
    """
    f_prev, f_curr = 0, 1
    S = 0
    plus = minus = zeros = 0
    alpha = -1
    s_val = -1
    T_alpha = 0
    captured_alpha = False

    LIMIT = 6 * p + 10
    for n in range(1, LIMIT):
        chi = _jacobi_jit(f_curr, p)
        S += chi
        if chi == 1:
            plus += 1
        elif chi == -1:
            minus += 1
        else:
            zeros += 1

        if not captured_alpha and chi == 0:
            alpha = n

        nxt = (f_prev + f_curr) % p
        f_prev, f_curr = f_curr, nxt

        if not captured_alpha and alpha == n:
            s_val = f_curr
            T_alpha = S
            captured_alpha = True

        if f_prev == 0 and f_curr == 1:
            chi_s = _jacobi_jit(s_val, p) if s_val >= 0 else 0
            return n, S, plus, minus, zeros, alpha, s_val, chi_s, T_alpha

    return _WALK_SENTINEL, 0, 0, 0, 0, -1, -1, 0, 0

# ----------------------------------------------------------------------------
# Backend C : Euler criterion via modpow
# ----------------------------------------------------------------------------

@njit(cache=True)
def _core_walk_pow(p: int):
    """Backend C: Euler's criterion via modpow.  O(1) memory.

    Same loop structure as _core_walk_array; see that function for the
    full loop invariant.
    """
    half = (p - 1) // 2
    f_prev, f_curr = 0, 1
    S = 0
    plus = minus = zeros = 0
    alpha = -1
    s_val = -1
    T_alpha = 0
    captured_alpha = False

    LIMIT = 6 * p + 10
    for n in range(1, LIMIT):
        chi = _chi_zero_safe_pow(f_curr, half, p)
        S += chi
        if chi == 1:
            plus += 1
        elif chi == -1:
            minus += 1
        else:
            zeros += 1

        if not captured_alpha and chi == 0:
            alpha = n

        nxt = (f_prev + f_curr) % p
        f_prev, f_curr = f_curr, nxt

        if not captured_alpha and alpha == n:
            s_val = f_curr
            T_alpha = S
            captured_alpha = True

        if f_prev == 0 and f_curr == 1:
            chi_s = _chi_zero_safe_pow(s_val, half, p) if s_val >= 0 else 0
            return n, S, plus, minus, zeros, alpha, s_val, chi_s, T_alpha

    return _WALK_SENTINEL, 0, 0, 0, 0, -1, -1, 0,  0


def _core_walk(p: int,
               th_array: int = TH_ARRAY_DEFAULT,
               th_bitwise: int = TH_BITWISE_DEFAULT) -> tuple:
    """Dispatch the hot loop to the appropriate backend by prime size."""
    if p < th_array:
        return _core_walk_array(p)
    if p < th_bitwise:
        return _core_walk_bitwise(p)
    return _core_walk_pow(p)


def _warmup_jit() -> None:
    """Force Numba JIT compilation of all three hot-loop backends."""
    if HAS_NUMBA:
        _core_walk_array(7)
        _core_walk_bitwise(7)
        _core_walk_pow(7)


# ============================================================================
# SECTION 3.  Per-prime analysis
# ============================================================================

def analyze_prime(p: int,
                  th_array: int = TH_ARRAY_DEFAULT,
                  th_bitwise: int = TH_BITWISE_DEFAULT) -> dict[str, Any]:
    """Compute all COLUMNS for a single prime p.

    Raises RuntimeError if the hot loop fails to close within 6*p+10
    steps (impossible for an odd prime p != 5; would indicate a bug).
    """
    c1, c5, sig = signature_label(p)
    result = _core_walk(p, th_array, th_bitwise)
    period = int(result[0])

    if period == _WALK_SENTINEL:
        raise RuntimeError(
            f"analyze_prime: hot loop exceeded LIMIT = 6*p+10 for p={p}. "
            "This should be impossible for an odd prime p != 5; please "
            "report it as a bug."
        )

    _, S, plus, minus, zeros, alpha, s_val, chi_s, T_alpha = result
    alpha = int(alpha)
    pm = int(plus) + int(minus)

    return {
        "p"            : int(p),
        "mod4"         : p % 4,
        "mod5"         : p % 5,
        "mod8"         : p % 8,
        "mod20"        : p % 20,
        "chi_minus1"   : int(c1),
        "chi_5"        : int(c5),
        "signature"    : sig,
        "pisano"       : period,
        "v2_pisano"    : v2(period),
        "alpha"        : alpha,
        "pi_over_alpha": (period // alpha) if alpha > 0 else -1,
        "s"            : int(s_val),
        "chi_s"        : int(chi_s),
        "T_alpha"      : int(T_alpha),
        "S_p"          : int(S),
        "abs_S"        : int(abs(S)),
        "plus"         : int(plus),
        "minus"        : int(minus),
        "zeros"        : int(zeros),
        "density_plus" : float(plus) / pm if pm > 0 else float("nan"),
        "is_Z"         : bool(S == 0),
    }


# ============================================================================
# SECTION 4.  Self-test  (Appendix A worked examples)
# ============================================================================

_SELF_TEST_CASES: dict[int, int] = {
    11: +1, 19: -1, 31: +1, 59: -1, 79: -1,
}


def run_self_test(log_fn=print) -> bool:
    """Reproduce the five worked examples of Appendix A.

    For each test prime, FIVE invariants are checked:
        (i)   S(p)        matches Appendix A
        (ii)  alpha(p) = p-1   (full-rank regime)
        (iii) pi(p)    = p-1   (catches off-by-one bugs in the hot loop)
        (iv)  signature = 'cm_only'   (Primitivity Lemma)
        (v)   T(p) = S(p)   (since pi = p-1 here)
    """
    log_fn("\n" + "=" * 72)
    log_fn(" SELF-TEST: Appendix-A worked examples")
    log_fn("=" * 72)
    log_fn(f" {'p':>4}  {'S(p)':>5}  {'exp':>4}  {'alpha':>6}  "
           f"{'pi':>6}  {'T(p)':>5}  {'signature':<10}  status")
    log_fn(" " + "-" * 68)

    all_ok = True
    for p_val, expected in sorted(_SELF_TEST_CASES.items()):
        rec = analyze_prime(p_val)
        check_S    = (rec["S_p"]       == expected)
        check_full = (rec["alpha"]     == p_val - 1)
        check_pi   = (rec["pisano"]    == p_val - 1)
        check_sig  = (rec["signature"] == "cm_only")
        check_TS   = (rec["T_alpha"]   == rec["S_p"])
        ok = check_S and check_full and check_pi and check_sig and check_TS
        all_ok = all_ok and ok

        log_fn(f"  {p_val:>4}  {rec['S_p']:+5d}  {expected:+4d}  "
               f"{rec['alpha']:>6}  {rec['pisano']:>6}  {rec['T_alpha']:+5d}  "
               f"{rec['signature']:<10}  {'OK' if ok else '*** FAIL ***'}")
        if not ok:
            if not check_S:
                log_fn(f"      [!] S(p) mismatch")
            if not check_full:
                log_fn(f"      [!] alpha != p-1   (got {rec['alpha']})")
            if not check_pi:
                log_fn(f"      [!] pi != p-1      (got {rec['pisano']}, expected {p_val - 1})")
            if not check_sig:
                log_fn(f"      [!] signature != cm_only")
            if not check_TS:
                log_fn(f"      [!] T(p) != S(p)")

    log_fn("")
    if all_ok:
        log_fn("[OK] Self-test PASSED  --  all 5 examples * 5 invariants verified.")
    else:
        log_fn("[FAIL] Self-test FAILED.  See diagnostics above.")
    return all_ok


# ============================================================================
# SECTION 5.  Main Theorem verification
# ============================================================================

def verify_corollary_b1(df: pd.DataFrame,
                        log_fn=print) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Machine-verify the paper's Main Theorem.

    In the paper, S(p) = sum_{n=1}^{p-1} chi_p(F_n).
    For candidates with alpha(p)=p-1, this equals T_alpha.
    The column S_p in this program denotes the full Pisano-period sum.

    Four sequential guards:
        Guard 1 (Primitivity Lemma):
            alpha(p) = p-1  ==>  signature = 'cm_only'
        Guard 2 (Main Theorem congruence):
            cm_only + alpha=p-1  ==>  p == 11 or 19 (mod 20)
        Guard 3 (Hot-loop self-consistency):
            full-rank regime  ==>  T_alpha == S_p
        Guard 4 (Main Theorem character sum):
            p == 11 (mod 20)  ==>  T_alpha = +1
            p == 19 (mod 20)  ==>  T_alpha = -1

    The function name is kept for backward compatibility with prior
    versions of the reproducibility archive.
    """
    required = {"p", "alpha", "signature", "mod20", "T_alpha", "S_p", "pisano"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"verify_corollary_b1: missing columns {sorted(missing)}")

    log_fn("\n" + "=" * 70)
    log_fn(" MAIN THEOREM VERIFICATION")
    log_fn("=" * 70)

    mask_full = df["alpha"] == (df["p"] - 1)
    cand = df[mask_full].copy()
    log_fn(f"\n  Primes with alpha(p) = p-1 : {len(cand):,}")
    log_fn(f"  of which signature=cm_only : "
           f"{int((cand['signature'] == 'cm_only').sum()):,}")

    # --- Guard 1: Primitivity Lemma ---
    non_cm = cand[cand["signature"] != "cm_only"]
    if len(non_cm) > 0:
        log_fn(f"\n[!] GUARD 1 VIOLATED: {len(non_cm)} prime(s) with "
               f"alpha=p-1 but signature != cm_only")
        log_fn(non_cm[["p", "mod20", "signature", "alpha"]]
               .head(20).to_string(index=False))
    else:
        log_fn("\n[OK] Guard 1 (Primitivity Lemma): all full-rank primes "
               "have signature 'cm_only'.")

    cm = cand[cand["signature"] == "cm_only"].copy()

    # --- Guard 2: Main Theorem congruence ---
    pred_map = {11: 1, 19: -1}
    cm["_predicted"] = cm["mod20"].map(pred_map)
    out_of_range = cm[cm["_predicted"].isna()]
    if len(out_of_range) > 0:
        log_fn(f"\n[!] GUARD 2 VIOLATED: {len(out_of_range)} cm_only "
               f"prime(s) with alpha=p-1 have p mod 20 not in {{11,19}}")
        log_fn(out_of_range[["p", "mod20", "alpha", "T_alpha"]]
               .head(20).to_string(index=False))
    else:
        log_fn("[OK] Guard 2 (Main Theorem congruence): all full-rank "
               "cm_only primes satisfy p == 11 or 19 (mod 20).")

    cm = cm[cm["_predicted"].notna()].copy()
    cm["_S_paper"] = cm["T_alpha"]

    # --- Guard 3: hot-loop self-consistency ---
    inconsistent = cm[cm["T_alpha"] != cm["S_p"]]
    if len(inconsistent) > 0:
        log_fn(f"\n[WARNING] {len(inconsistent)} full-rank prime(s) have "
               f"T_alpha != S_p.  The paper's theorem is checked against "
               f"T_alpha = sum_{{n=1}}^{{p-1}} chi_p(F_n), while S_p is "
               f"the full Pisano-period sum.")
        log_fn(inconsistent[["p", "alpha", "pisano", "T_alpha", "S_p"]]
               .head(10).to_string(index=False))
    else:
        log_fn(f"[OK] Guard 3 (consistency): T_alpha == S_p for all "
               f"{len(cm):,} full-rank candidates.")

    # --- Guard 4: the Main Theorem itself ---
    cm["_matches"] = cm["_S_paper"] == cm["_predicted"]

    rows = []
    for m in (11, 19):
        sub = cm[cm["mod20"] == m]
        n_sub = len(sub)
        n_match = int(sub["_matches"].sum())
        rows.append({
            "p_mod_20"    : m,
            "predicted_S" : int(pred_map[m]),
            "count"       : n_sub,
            "matches"     : n_match,
            "mismatches"  : n_sub - n_match,
            "verdict"     : "PASS" if n_match == n_sub else "FAIL",
        })
    summary_df = pd.DataFrame(rows)

    log_fn("\n  Verification table:")
    log_fn(summary_df.to_string(index=False))

    failures_df = cm[~cm["_matches"]].drop(
        columns=["_predicted", "_matches", "_S_paper"], errors="ignore"
    ).copy()

    if len(failures_df) > 0:
        log_fn(f"\n[FAIL] {len(failures_df)} counterexamples to Main Theorem:")
        log_fn(failures_df[["p", "mod20", "alpha", "T_alpha", "S_p"]]
               .head(30).to_string(index=False))
    else:
        log_fn(f"\n[OK] Guard 4 (Main Theorem): T_alpha verified for all "
               f"{len(cm):,} candidate prime(s).  No counterexamples.")

    return summary_df, failures_df


# ============================================================================
# SECTION 5b.  Step-by-step proof check  (root / order / sign)
# ============================================================================

def verify_root_order_sign_checks(df: pd.DataFrame,
                                  log_fn=print,
                                  sample_size: int | None = None,
                                  random_state: int = 42,
                                  ) -> pd.DataFrame:
    """Verify the root/order/sign structural lemmas used in the paper.

    For each full-rank prime, independently computes the two roots of
    x^2 - x - 1 over F_p via Tonelli-Shanks, then checks:

      (i)   exactly one root is a QR and the other an NQR;
      (ii)  ord(-r_-^2) = alpha(p)        [Rank-Order Lemma];
      (iii) ord(r_-) = p-1                 [Primitivity Lemma];
      (iv)  chi_p(r_- - r_+) matches the predicted sign of the theorem;
      (v)   T_alpha equals chi_p(r_- - r_+) [Structural Identity];
      (vi)  T_alpha equals the predicted sign [combined check].

    Parameters
    ----------
    sample_size : if not None, randomly sample this many full-rank primes
                  instead of testing all.  Recommended for N >= 5*10^6
                  where exhaustive checks take more than a few minutes.
                  None means "test all" (default).
    random_state : seed for reproducible sampling.
    """
    required = {"p", "alpha", "mod20", "T_alpha"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"verify_root_order_sign_checks: missing columns {sorted(missing)}"
        )

    full = df[
        (~df["p"].isin([2, 5])) &
        (df["alpha"] == df["p"] - 1)
    ].copy()

    if sample_size is not None and len(full) > sample_size:
        log_fn(f"  Sampling {sample_size} of {len(full):,} full-rank primes "
               f"(use sample_size=None for exhaustive)")
        full = full.sample(sample_size, random_state=random_state)

    rows: list[dict[str, Any]] = []

    for _, row in full.iterrows():
        p = int(row["p"])
        alpha = int(row["alpha"])
        mod20 = int(row["mod20"])
        T_alpha = int(row["T_alpha"])

        # Defensive: if mod20 not in {11,19}, Guard 2 has already failed.
        if mod20 not in (11, 19):
            rows.append({
                "p": p, "mod20": mod20, "alpha": alpha, "T_alpha": T_alpha,
                "r1": -1, "r2": -1, "chi_r1": 0, "chi_r2": 0,
                "r_minus": -1, "r_plus": -1,
                "ord_minus_rminus_squared": -1, "ord_r_minus": -1,
                "chi_rminus_minus_rplus": 0, "predicted_sign": 0,
                "ok_roots": False, "ok_ord_minus_rminus_squared": False,
                "ok_ord_r_minus": False, "ok_sign": False,
                "ok_Talpha_equals_sign": False,
                "ok_Talpha_equals_predicted": False,
                "passes": False,
                "error": f"mod20={mod20} not in {{11,19}} (Guard 2 violation)",
            })
            continue

        predicted = 1 if mod20 == 11 else -1

        try:
            r1, r2 = fibonacci_roots_mod_p(p)
            c1 = legendre_symbol(r1, p)
            c2 = legendre_symbol(r2, p)

            exactly_one_nqr = sorted([c1, c2]) == [-1, 1]

            if c1 == -1 and c2 == 1:
                r_minus, r_plus = r1, r2
            elif c2 == -1 and c1 == 1:
                r_minus, r_plus = r2, r1
            else:
                r_minus, r_plus = -1, -1

            if exactly_one_nqr:
                ord_minus_r2 = multiplicative_order_mod(
                    (-r_minus * r_minus) % p, p)
                ord_r_minus = multiplicative_order_mod(r_minus, p)
                sign = legendre_symbol((r_minus - r_plus) % p, p)
            else:
                ord_minus_r2 = -1
                ord_r_minus = -1
                sign = 0

            ok_roots = exactly_one_nqr
            ok_order_minus_r2 = ord_minus_r2 == alpha
            ok_order_rminus = ord_r_minus == p - 1
            ok_sign = sign == predicted
            ok_Talpha_equals_sign = T_alpha == sign
            ok_Talpha_equals_predicted = T_alpha == predicted

            ok = (
                ok_roots and
                ok_order_minus_r2 and
                ok_order_rminus and
                ok_sign and
                ok_Talpha_equals_sign and
                ok_Talpha_equals_predicted
            )

            rows.append({
                "p": p, "mod20": mod20, "alpha": alpha, "T_alpha": T_alpha,
                "r1": r1, "r2": r2, "chi_r1": c1, "chi_r2": c2,
                "r_minus": r_minus, "r_plus": r_plus,
                "ord_minus_rminus_squared": ord_minus_r2,
                "ord_r_minus": ord_r_minus,
                "chi_rminus_minus_rplus": sign,
                "predicted_sign": predicted,
                "ok_roots": ok_roots,
                "ok_ord_minus_rminus_squared": ok_order_minus_r2,
                "ok_ord_r_minus": ok_order_rminus,
                "ok_sign": ok_sign,
                "ok_Talpha_equals_sign": ok_Talpha_equals_sign,
                "ok_Talpha_equals_predicted": ok_Talpha_equals_predicted,
                "passes": ok,
                "error": "",
            })

        except Exception as exc:
            rows.append({
                "p": p, "mod20": mod20, "alpha": alpha, "T_alpha": T_alpha,
                "r1": -1, "r2": -1, "chi_r1": 0, "chi_r2": 0,
                "r_minus": -1, "r_plus": -1,
                "ord_minus_rminus_squared": -1, "ord_r_minus": -1,
                "chi_rminus_minus_rplus": 0, "predicted_sign": predicted,
                "ok_roots": False, "ok_ord_minus_rminus_squared": False,
                "ok_ord_r_minus": False, "ok_sign": False,
                "ok_Talpha_equals_sign": False,
                "ok_Talpha_equals_predicted": False,
                "passes": False,
                "error": repr(exc),
            })

    out = pd.DataFrame(rows)
    n_fail = int((~out["passes"]).sum()) if len(out) else 0

    log_fn("\n" + "=" * 70)
    log_fn(" ROOT / ORDER / SIGN INTERNAL CHECKS")
    log_fn("=" * 70)
    log_fn(f"  full-rank primes tested : {len(out):,}")
    log_fn(f"  failures                : {n_fail:,}")

    if n_fail:
        log_fn("[FAIL] Root/order/sign checks failed for:")
        log_fn(out[~out["passes"]].head(20).to_string(index=False))
    else:
        log_fn("[OK] All root/order/sign checks passed.")

    return out


def _summarize_root_checks(root_df: pd.DataFrame) -> pd.DataFrame:
    """Produce a compact summary of root/order/sign checks for the report.

    The detailed `root_df` (one row per full-rank prime, ~20 columns) is
    saved to CSV for full transparency, but is too wide for the textual
    and LaTeX report.  This function returns a 6+1-row summary suitable
    for both.
    """
    if len(root_df) == 0:
        return pd.DataFrame(
            columns=["check", "n_tested", "n_pass", "n_fail", "verdict"]
        )

    checks = [
        ("Roots: exactly one QR + one NQR",       "ok_roots"),
        ("Order: ord(-r_-^2) == alpha(p)",        "ok_ord_minus_rminus_squared"),
        ("Order: ord(r_-) == p-1 (primitive)",    "ok_ord_r_minus"),
        ("Sign:  chi_p(r_- - r_+) == predicted",  "ok_sign"),
        ("T_alpha == chi_p(r_- - r_+)  [struct]", "ok_Talpha_equals_sign"),
        ("T_alpha == predicted  [main thm]",      "ok_Talpha_equals_predicted"),
    ]

    n_total = len(root_df)
    rows = []
    for desc, col in checks:
        if col not in root_df.columns:
            continue
        n_pass = int(root_df[col].astype(bool).sum())
        rows.append({
            "check"   : desc,
            "n_tested": n_total,
            "n_pass"  : n_pass,
            "n_fail"  : n_total - n_pass,
            "verdict" : "PASS" if n_pass == n_total else "FAIL",
        })

    if "passes" in root_df.columns:
        n_all = int(root_df["passes"].astype(bool).sum())
        rows.append({
            "check"   : "OVERALL (all checks pass per prime)",
            "n_tested": n_total,
            "n_pass"  : n_all,
            "n_fail"  : n_total - n_all,
            "verdict" : "PASS" if n_all == n_total else "FAIL",
        })

    return pd.DataFrame(rows)


# ============================================================================
# SECTION 6.  Verification of empirical claims E1..E10
# ============================================================================

def verify_all_empirical_claims(df: pd.DataFrame,
                                log_fn=print) -> pd.DataFrame:
    """Verify ten empirical claims E1..E10 from the project notes."""
    log_fn("\n" + "=" * 70)
    log_fn(" VERIFICATION OF EMPIRICAL CLAIMS E1..E10")
    log_fn("=" * 70)

    main = df[~df["p"].isin([2, 5])].copy()
    results: list[dict[str, Any]] = []

    def record(name: str, passes: bool, n_tested: int,
               n_violations: int = 0, info: str = "") -> None:
        results.append({
            "claim"       : name,
            "passes"      : bool(passes),
            "n_tested"    : int(n_tested),
            "n_violations": int(n_violations),
            "status"      : "PASS" if passes else ("FAIL" if n_tested else "N/A"),
            "info"        : info,
        })

    # ---- E1 ----  vectorised v_2(p+1)
    DI = main[main["signature"] == "DI"].copy()
    if len(DI):
        DI["_pred"] = v2_array(DI["p"].values + 1).astype(np.int64) + 1
        viol = int((DI["v2_pisano"] != DI["_pred"]).sum())
        record("E1 : v_2(pi) = v_2(p+1) + 1  on DI",
               viol == 0, len(DI), viol)
    else:
        record("E1 : v_2(pi) = v_2(p+1) + 1  on DI", True, 0)

    # ---- E2 ----
    Z = main["is_Z"]
    DI_mask = main["signature"] == "DI"
    ZmD = main[Z & ~DI_mask].copy()
    if len(ZmD):
        cond = (ZmD["pisano"] == 4 * ZmD["alpha"]) & (ZmD["alpha"] % 2 == 1)
        viol = int((~cond).sum())
        record("E2 : pi = 4 alpha AND alpha odd  on Z \\ DI",
               viol == 0, len(ZmD), viol)
    else:
        record("E2 : pi = 4 alpha AND alpha odd  on Z \\ DI", True, 0)

    # ---- E3 ----
    cm = main[main["signature"] == "cm_only"]
    if len(cm):
        viol = int((cm["pisano"] != cm["alpha"]).sum())
        record("E3 : pi = alpha  on cm_only",
               viol == 0, len(cm), viol)
    else:
        record("E3 : pi = alpha  on cm_only", True, 0)

    # ---- E4 ----
    inert = main[main["signature"].isin(["DI", "fib_only"])]
    if len(inert):
        viol = int(((inert["p"] + 1) % inert["alpha"] != 0).sum())
        record("E4 : alpha | (p+1)  for inert primes",
               viol == 0, len(inert), viol)
    else:
        record("E4 : alpha | (p+1)  for inert primes", True, 0)

    # ---- E5 ----
    split = main[main["signature"].isin(["cm_only", "neither"])]
    if len(split):
        viol = int(((split["p"] - 1) % split["alpha"] != 0).sum())
        record("E5 : alpha | (p-1)  for split primes",
               viol == 0, len(split), viol)
    else:
        record("E5 : alpha | (p-1)  for split primes", True, 0)

    # ---- E6 + E7 ----
    main_k = main.copy()
    is_inert = main_k["signature"].isin(["DI", "fib_only"])
    main_k["_k"] = np.where(
        is_inert,
        (main_k["p"] + 1) // main_k["alpha"],
        (main_k["p"] - 1) // main_k["alpha"],
    )

    sub6 = main_k[main_k["chi_minus1"] == -1]
    viol6 = int((sub6["_k"] % 2 != 1).sum())
    record("E6 : chi_p(-1) = -1  ==>  k is odd",
           viol6 == 0, len(sub6), viol6)

    sub7 = main_k[main_k["chi_minus1"] == 1]
    viol7 = int((sub7["_k"] % 2 != 0).sum())
    record("E7 : chi_p(-1) = +1  ==>  k is even",
           viol7 == 0, len(sub7), viol7)

    # ---- E8 : MAIN THEOREM ----
    cm_full = main[(main["signature"] == "cm_only") &
                   (main["alpha"] == main["p"] - 1)].copy()
    if len(cm_full):
        cm_full["_pred"] = cm_full["mod5"].map({1: 1, 4: -1})
        oob = int(cm_full["_pred"].isna().sum())
        if oob > 0:
            record("E8 : full-rank cm_only  ==>  p == 1 or 4 (mod 5)",
                   False, len(cm_full), oob,
                   info=f"{oob} primes outside p mod 5 in {{1,4}}")
        valid = cm_full[cm_full["_pred"].notna()]
        viol8 = int((valid["T_alpha"] != valid["_pred"]).sum())
        record("E8 : paper S(p)=T_alpha is +1 if p==1 mod 5, -1 if p==4 mod 5  [MAIN THEOREM]",
               viol8 == 0, len(valid), viol8)
    else:
        record("E8 : MAIN THEOREM  (no full-rank primes in sample)",
               True, 0, info="sample too small")

    # ---- E9 ----
    cm_k3 = main[(main["signature"] == "cm_only") &
                 ((main["p"] - 1) // main["alpha"] == 3)]
    if len(cm_k3):
        viol9 = int((cm_k3["abs_S"] % 2 != 1).sum())
        record("E9 : |S_p| is odd  on cm_only with k=3",
               viol9 == 0, len(cm_k3), viol9)
    else:
        record("E9 : |S_p| is odd  on cm_only with k=3", True, 0)

    # ---- E10 ----
    fo = main[main["signature"] == "fib_only"].copy()
    if len(fo):
        fo["_k"] = (fo["p"] + 1) // fo["alpha"]
        fo_k2 = fo[fo["_k"] == 2]
        if len(fo_k2):
            viol10 = int((fo_k2["S_p"] % 8 != 0).sum())
            record("E10: 8 | S_p  on fib_only with k=2",
                   viol10 == 0, len(fo_k2), viol10)
        else:
            record("E10: 8 | S_p  on fib_only with k=2", True, 0)
    else:
        record("E10: 8 | S_p  on fib_only with k=2", True, 0)

    df_results = pd.DataFrame(results)
    log_fn("\n" + df_results.to_string(index=False))

    n_pass = int((df_results["status"] == "PASS").sum())
    n_fail = int((df_results["status"] == "FAIL").sum())
    log_fn(f"\nSummary:  {n_pass} PASS  |  {n_fail} FAIL")
    if n_fail > 0:
        log_fn("[!] Some claims failed.  Investigate before submission.")
    else:
        log_fn("[OK] All 10 empirical claims verified on this database.")
    return df_results


# ============================================================================
# SECTION 7.  Checkpointing  (sequential pipeline only)
# ============================================================================

def _ckpt_paths(out_dir: str, N_max: int) -> tuple[str, str, str]:
    base = os.path.join(out_dir, f"checkpoint_N{N_max}")
    return base + ".parquet", base + ".csv", base + ".meta.json"


def save_checkpoint(out_dir: str, N_max: int, rows: dict[str, list],
                    last_index: int, total_primes: int,
                    elapsed: float) -> None:
    """Atomically save a checkpoint (parquet preferred, csv fallback)."""
    os.makedirs(out_dir, exist_ok=True)
    pq_path, csv_path, meta_path = _ckpt_paths(out_dir, N_max)
    df_ckpt = pd.DataFrame(rows)

    saved_data: str
    tmp_pq = pq_path + ".tmp"
    try:
        df_ckpt.to_parquet(tmp_pq, index=False)
        os.replace(tmp_pq, pq_path)
        saved_data = pq_path
    except Exception:
        if os.path.exists(tmp_pq):
            try:
                os.remove(tmp_pq)
            except OSError:
                pass
        tmp_csv = csv_path + ".tmp"
        df_ckpt.to_csv(tmp_csv, index=False)
        os.replace(tmp_csv, csv_path)
        saved_data = csv_path

    meta = {
        "N_max"        : int(N_max),
        "last_index"   : int(last_index),
        "total_primes" : int(total_primes),
        "elapsed_sec"  : float(elapsed),
        "timestamp"    : time.strftime("%Y-%m-%d %H:%M:%S"),
        "saved_data"   : saved_data,
        "version"      : __version__,
    }
    tmp_meta = meta_path + ".tmp"
    with open(tmp_meta, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    os.replace(tmp_meta, meta_path)


def load_checkpoint(out_dir: str,
                    N_max: int) -> tuple[pd.DataFrame, dict] | None:
    pq_path, csv_path, meta_path = _ckpt_paths(out_dir, N_max)
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    if os.path.exists(pq_path):
        try:
            return pd.read_parquet(pq_path), meta
        except Exception:
            pass
    if os.path.exists(csv_path):
        try:
            return pd.read_csv(csv_path), meta
        except Exception:
            pass
    return None


def delete_checkpoint(out_dir: str, N_max: int) -> None:
    for path in _ckpt_paths(out_dir, N_max):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


# ============================================================================
# SECTION 8.  Sequential database builder  (optimised)
# ============================================================================

_COLUMN_DTYPES: dict[str, type] = {
    "p"           : np.int64,
    "mod4"        : np.int8,
    "mod5"        : np.int8,
    "mod8"        : np.int8,
    "mod20"       : np.int8,
    "chi_minus1"  : np.int8,
    "chi_5"       : np.int8,
    "signature"   : object,
    "pisano"      : np.int64,
    "v2_pisano"   : np.int8,
    "alpha"       : np.int64,
    "pi_over_alpha": np.int32,
    "s"           : np.int64,
    "chi_s"       : np.int8,
    "T_alpha"     : np.int64,
    "S_p"         : np.int64,
    "abs_S"       : np.int64,
    "plus"        : np.int64,
    "minus"        : np.int64,
    "zeros"       : np.int64,
    "density_plus": np.float64,
    "is_Z"        : bool,
}


def _allocate_columns(n: int) -> dict[str, np.ndarray]:
    """Pre-allocate a typed dict of NumPy arrays for n primes."""
    return {k: np.empty(n, dtype=dt) for k, dt in _COLUMN_DTYPES.items()}


def _copy_from_resume(cols: dict[str, np.ndarray],
                      resume_df: pd.DataFrame,
                      start_idx: int) -> None:
    """Copy already-computed values from a checkpoint into pre-allocated arrays."""
    for k in cols:
        if k in resume_df.columns:
            src = resume_df[k].values[:start_idx]
            if len(src) == start_idx:
                cols[k][:start_idx] = src


def _save_partial_checkpoint(out_dir: str, N_max: int,
                             cols: dict[str, np.ndarray],
                             last_index: int, total_primes: int,
                             elapsed: float) -> None:
    """Save a checkpoint from the pre-allocated NumPy arrays."""
    partial = {k: cols[k][:last_index] for k in COLUMNS}
    rows_dict = {k: partial[k].tolist() for k in COLUMNS}
    save_checkpoint(out_dir, N_max, rows_dict, last_index,
                    total_primes, elapsed)


def build_database(N_max: int,
                   out_dir: str,
                   log_fn=print,
                   progress_fn=lambda x: None,
                   th_array: int = TH_ARRAY_DEFAULT,
                   th_bitwise: int = TH_BITWISE_DEFAULT,
                   resume_df: pd.DataFrame | None = None,
                   resume_meta: dict | None = None,
                   stop_event: threading.Event | None = None,
                   ) -> pd.DataFrame | None:
    """Build the full prime database sequentially with checkpoint/resume.

    Columns are pre-allocated as typed NumPy arrays (not Python lists),
    avoiding ~30% overhead of `list.append` and dict construction per
    iteration.

    Returns the completed DataFrame, or None if stopped early (in which
    case a checkpoint was saved).
    """
    primes = sieve_primes(N_max)
    n_total = int(len(primes))

    log_fn(f"[+] FibChar v{__version__}  (author: {__author__})")
    log_fn(f"[+] backend       : {'Numba JIT' if HAS_NUMBA else 'pure Python (slow)'}")
    log_fn(f"[+] primes <= {N_max:,} : {n_total:,}")
    log_fn(f"[+] thresholds    : "
           f"array < {th_array:,}  |  bitwise < {th_bitwise:,}  |  "
           f"pow >= {th_bitwise:,}")
    log_fn(f"[+] checkpoint    : every {CHECKPOINT_EVERY:,} primes")

    if HAS_NUMBA:
        log_fn("[+] warming JIT (first call compiles all 3 backends) ...")
        t_jit = time.perf_counter()
        _warmup_jit()
        log_fn(f"[+] JIT warm-up done ({time.perf_counter() - t_jit:.2f}s)")

    cols = _allocate_columns(n_total)
    start_idx: int = 0
    elapsed_prev: float = 0.0

    if resume_df is not None and resume_meta is not None:
        start_idx = int(resume_meta.get("last_index", 0))
        elapsed_prev = float(resume_meta.get("elapsed_sec", 0.0))
        _copy_from_resume(cols, resume_df, start_idx)
        pct = 100.0 * start_idx / max(n_total, 1)
        log_fn(f"[+] RESUMING from index {start_idx:,} "
               f"({pct:.1f}% done, previously elapsed {elapsed_prev:.0f}s)")
        progress_fn(start_idx / max(n_total, 1))

    t0 = time.perf_counter()
    next_log_at = start_idx + LOG_INTERVAL
    next_ckpt_at = start_idx + CHECKPOINT_EVERY

    # Local-name aliasing for hot-loop speed
    _signature_label = signature_label
    _v2 = v2
    _core_walk_local = _core_walk
    _COLS = cols

    for i in range(start_idx, n_total):
        if stop_event is not None and stop_event.is_set():
            elapsed_now = elapsed_prev + (time.perf_counter() - t0)
            log_fn(f"[!] STOP requested at index {i:,}.  Saving checkpoint ...")
            _save_partial_checkpoint(out_dir, N_max, _COLS, i, n_total, elapsed_now)
            log_fn(f"[+] Checkpoint saved (index {i:,}).")
            return None

        p = int(primes[i])
        c1, c5, sig = _signature_label(p)
        (period, S, plus, minus, zeros,
         alpha, s_val, chi_s, T_alpha) = _core_walk_local(p, th_array, th_bitwise)

        if period == _WALK_SENTINEL:
            raise RuntimeError(
                f"build_database: hot loop exceeded LIMIT for p={p}. "
                "This should be impossible for an odd prime p != 5."
            )

        period_i = int(period)
        alpha_i = int(alpha)
        plus_i, minus_i = int(plus), int(minus)
        pm = plus_i + minus_i

        # Direct slot assignment (no dict, no append)
        _COLS["p"][i]             = p
        _COLS["mod4"][i]          = p % 4
        _COLS["mod5"][i]          = p % 5
        _COLS["mod8"][i]          = p % 8
        _COLS["mod20"][i]         = p % 20
        _COLS["chi_minus1"][i]    = c1
        _COLS["chi_5"][i]         = c5
        _COLS["signature"][i]     = sig
        _COLS["pisano"][i]        = period_i
        _COLS["v2_pisano"][i]     = _v2(period_i)
        _COLS["alpha"][i]         = alpha_i
        _COLS["pi_over_alpha"][i] = (period_i // alpha_i) if alpha_i > 0 else -1
        _COLS["s"][i]             = int(s_val)
        _COLS["chi_s"][i]         = int(chi_s)
        _COLS["T_alpha"][i]       = int(T_alpha)
        _COLS["S_p"][i]           = int(S)
        _COLS["abs_S"][i]         = abs(int(S))
        _COLS["plus"][i]          = plus_i
        _COLS["minus"][i]         = minus_i
        _COLS["zeros"][i]         = int(zeros)
        _COLS["density_plus"][i]  = (plus_i / pm) if pm > 0 else float("nan")
        _COLS["is_Z"][i]          = (S == 0)

        done = i + 1
        if done >= next_log_at or done == n_total:
            dt = time.perf_counter() - t0
            elapsed_now = elapsed_prev + dt
            rate = (done - start_idx) / max(dt, 1e-9)
            eta = (n_total - done) / max(rate, 1e-9)
            log_fn(f"    {done:8,}/{n_total:,}  "
                   f"p={p:10,}  "
                   f"rate={rate:8,.0f}/s  "
                   f"ETA={eta:6.0f}s  "
                   f"total={elapsed_now:.0f}s")
            next_log_at = done + LOG_INTERVAL

        if done >= next_ckpt_at and done < n_total:
            elapsed_now = elapsed_prev + (time.perf_counter() - t0)
            _save_partial_checkpoint(out_dir, N_max, _COLS, done, n_total, elapsed_now)
            log_fn(f"    [ckpt] saved at index {done:,}")
            next_ckpt_at = done + CHECKPOINT_EVERY

        progress_fn(done / n_total)

    # Build the final DataFrame from the pre-allocated arrays
    df = pd.DataFrame({k: cols[k] for k in COLUMNS})
    elapsed_now = elapsed_prev + (time.perf_counter() - t0)
    log_fn(f"[+] Compute finished  "
           f"(session {time.perf_counter() - t0:.1f}s, "
           f"total {elapsed_now:.1f}s, {len(df):,} rows)")
    return df


# ============================================================================
# SECTION 9.  Parallel database builder  (no checkpoint/resume)
# ============================================================================

def _parallel_worker_init() -> None:
    """ProcessPoolExecutor initializer: warm up JIT in each worker once."""
    if HAS_NUMBA:
        _warmup_jit()


def _analyze_chunk(args: tuple) -> list[dict]:
    chunk, th_a, th_b = args
    return [analyze_prime(int(p), th_a, th_b) for p in chunk]


def build_database_parallel(primes: np.ndarray,
                            workers: int,
                            chunk_size: int,
                            th_array: int,
                            th_bitwise: int,
                            log_fn=print) -> pd.DataFrame:
    """Build the database using a ProcessPoolExecutor with LPT scheduling.

    Notes
    -----
    * No checkpoint/resume in this path; runs start-to-finish.
    * Each worker warms up Numba's JIT once at startup.
    * Heaviest chunks (largest primes) are submitted first so workers
      remain busy at the end of the run (LPT scheduling).
    * Chunk failures cause a hard RuntimeError (no silent loss).
    * ALWAYS returns a (possibly empty) DataFrame; never None.
    """
    # ---- 1. Build chunks ----
    chunks = [
        primes[i : i + chunk_size]
        for i in range(0, len(primes), chunk_size)
    ]
    n_chunks = len(chunks)

    if n_chunks == 0:
        log_fn("[!] build_database_parallel: no chunks to process.")
        return pd.DataFrame()

    results: list[list[dict]] = [[] for _ in range(n_chunks)]
    n_errors = 0
    first_error: str = ""

    # ---- 2. LPT scheduling: heaviest chunks first ----
    chunk_costs = [
        int(np.sum(c, dtype=np.int64)) if len(c) else 0
        for c in chunks
    ]
    submit_order = sorted(
        range(n_chunks),
        key=lambda i: chunk_costs[i],
        reverse=True,
    )
    log_fn(f"[+] parallel chunks: {n_chunks} "
           f"(LPT scheduling: heaviest submitted first)")

    # ---- 3. Submit and collect ----
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_parallel_worker_init,
    ) as executor:
        future_to_idx = {
            executor.submit(_analyze_chunk,
                            (chunks[idx], th_array, th_bitwise)): idx
            for idx in submit_order
        }
        log_fn(f"[+] {len(future_to_idx)} tasks submitted; waiting ...")

        completed = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                n_errors += 1
                p_start = int(chunks[idx][0]) if len(chunks[idx]) else "?"
                msg = f"chunk {idx} (starting p={p_start}) failed: {exc!r}"
                log_fn(f"[!] {msg}")
                if not first_error:
                    first_error = msg
                results[idx] = []
            completed += 1
            step = max(n_chunks // 20, 1)
            if completed % step == 0 or completed == n_chunks:
                log_fn(f"    chunks done: {completed}/{n_chunks}")

    # ---- 4. Hard-fail on any worker errors ----
    if n_errors > 0:
        raise RuntimeError(
            f"{n_errors} chunk(s) failed in parallel execution; aborting. "
            f"First error: {first_error}"
        )

    # ---- 5. Build final DataFrame ----
    flat = [rec for cr in results for rec in cr]
    log_fn(f"[+] collected {len(flat):,} records from {n_chunks} chunks")
    df = pd.DataFrame(flat)
    if len(df):
        df = df.sort_values("p").reset_index(drop=True)

    return df


# ============================================================================
# SECTION 10.  Diagnostic tables (Tables 1..15)
# ============================================================================

def compute_all_tables(df: pd.DataFrame
                       ) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Compute all diagnostic tables.

    Returns (tables_dict, main_df) where main_df is df restricted to
    p not in {2, 5}.
    """
    tables: dict[str, pd.DataFrame] = {}
    main = df[~df["p"].isin([2, 5])].copy()
    n = len(main)
    if n == 0:
        return tables, main

    Z   = main["is_Z"]
    DI  = main["signature"] == "DI"
    ZmD = Z & ~DI
    ZaD = Z & DI

    # ---- Table 00 : headline densities ----
    tables["00_headline"] = pd.DataFrame([
        {"quantity": "delta(Z)",          "value": float(Z.mean()),
         "count": int(Z.sum()),  "total": n},
        {"quantity": "delta(DI)",         "value": float(DI.mean()),
         "count": int(DI.sum()), "total": n},
        {"quantity": "delta(Z and DI)",   "value": float(ZaD.mean()),
         "count": int(ZaD.sum()),"total": n},
        {"quantity": "delta(Z minus DI)", "value": float(ZmD.mean()),
         "count": int(ZmD.sum()),"total": n},
        {"quantity": "P(Z | DI)",
         "value": float(ZaD.sum() / max(DI.sum(), 1)),
         "count": int(ZaD.sum()),"total": int(DI.sum())},
    ])

    # ---- Table 01 : signature counts ----
    SIGS = ["DI", "fib_only", "cm_only", "neither"]
    sg = main["signature"].value_counts()
    tables["01_signature_counts"] = pd.DataFrame([
        {"signature": s,
         "count"    : int(sg.get(s, 0)),
         "fraction" : sg.get(s, 0) / n}
        for s in SIGS
    ])

    # ---- Table 02 : P(Z | signature) ----
    rows = []
    for s in SIGS:
        sub = main[main["signature"] == s]
        rows.append({
            "signature"    : s,
            "n_sig"        : len(sub),
            "n_Z"          : int(sub["is_Z"].sum()),
            "P_Z_given_sig": float(sub["is_Z"].mean()) if len(sub) else float("nan"),
        })
    tables["02_P_Z_given_signature"] = pd.DataFrame(rows)

    # ---- Table 03 : S_p statistics per signature ----
    rows = []
    for s in SIGS:
        sub = main[main["signature"] == s]
        if len(sub) == 0:
            continue
        rows.append({
            "signature": s,
            "mean_S_p" : float(sub["S_p"].mean()),
            "std_S_p"  : float(sub["S_p"].std()),
            "mean_absS": float(sub["abs_S"].mean()),
            "max_absS" : int(sub["abs_S"].max()),
        })
    tables["03_Sp_stats_by_signature"] = pd.DataFrame(rows)

    # ---- Table 04 : v_2(pi) per class ----
    classes = {
        "all"       : main,
        "Z"         : main[Z],
        "DI"        : main[DI],
        "Z_minus_DI": main[ZmD],
        "Z_and_DI"  : main[ZaD],
    }
    rows = []
    for name, sub in classes.items():
        if len(sub) == 0:
            rows.append({"class": name, "n": 0, "mean_v2": float("nan"),
                         "median_v2": -1, "min_v2": -1, "max_v2": -1})
        else:
            rows.append({"class": name, "n": len(sub),
                         "mean_v2"  : float(sub["v2_pisano"].mean()),
                         "median_v2": int(sub["v2_pisano"].median()),
                         "min_v2"   : int(sub["v2_pisano"].min()),
                         "max_v2"   : int(sub["v2_pisano"].max())})
    tables["04_v2_per_class"] = pd.DataFrame(rows)

    # ---- Table 04b : full distribution of v_2(pi) ----
    v2_vals = sorted(int(x) for x in main["v2_pisano"].unique())
    all_dist = main["v2_pisano"].value_counts(normalize=True)
    Z_dist   = main[Z]["v2_pisano"].value_counts(normalize=True)
    ZmD_dist = (main[ZmD]["v2_pisano"].value_counts(normalize=True)
                if ZmD.sum() else pd.Series(dtype=float))
    DI_dist  = main[DI]["v2_pisano"].value_counts(normalize=True)
    tables["04b_v2_distribution"] = pd.DataFrame([
        {"v2"           : k,
         "freq_all"     : float(all_dist.get(k, 0)),
         "freq_Z"       : float(Z_dist.get(k, 0)),
         "freq_ZminusDI": float(ZmD_dist.get(k, 0)),
         "freq_DI"      : float(DI_dist.get(k, 0))}
        for k in v2_vals
    ])

    # ---- Table 05 : P(Z | p mod 20) ----
    rows = []
    for m in sorted(main["mod20"].unique()):
        sub = main[main["mod20"] == m]
        rows.append({"mod20": int(m), "count": len(sub),
                     "fraction": len(sub) / n,
                     "n_Z": int(sub["is_Z"].sum()),
                     "P_Z_given_mod": float(sub["is_Z"].mean())
                                       if len(sub) else float("nan")})
    tables["05_mod20_distribution"] = pd.DataFrame(rows)

    # ---- Table 06 : P(Z | p mod 8) ----
    rows = []
    for m in sorted(main["mod8"].unique()):
        sub = main[main["mod8"] == m]
        rows.append({"mod8": int(m), "count": len(sub),
                     "fraction": len(sub) / n,
                     "n_Z": int(sub["is_Z"].sum()),
                     "P_Z_given_mod": float(sub["is_Z"].mean())
                                       if len(sub) else float("nan")})
    tables["06_mod8_distribution"] = pd.DataFrame(rows)

    # ---- Table 07 : 2-adic tower ----
    rows = []
    for k in v2_vals:
        sub = main[main["v2_pisano"] == k]
        row: dict[str, Any] = {
            "k": k, "n_k": len(sub),
            "n_Z": int(sub["is_Z"].sum()),
            "P_Z_given_k": float(sub["is_Z"].mean()) if len(sub) else float("nan"),
        }
        for m in (1, 3, 5, 7):
            ss = sub[sub["mod8"] == m]
            row[f"P_Z_k_mod8_{m}"] = float(ss["is_Z"].mean()) if len(ss) else float("nan")
            row[f"n_k_mod8_{m}"]   = len(ss)
        rows.append(row)
    tables["07_2adic_tower"] = pd.DataFrame(rows)

    # ---- Table 08 : cross-table v_2 x signature x is_Z ----
    rows = []
    for sig in SIGS:
        sub_sig = main[main["signature"] == sig]
        for k in sorted(sub_sig["v2_pisano"].unique()):
            ss = sub_sig[sub_sig["v2_pisano"] == k]
            rows.append({"signature": sig, "v2_pisano": int(k),
                         "n": len(ss), "n_Z": int(ss["is_Z"].sum()),
                         "n_not_Z": int((~ss["is_Z"]).sum()),
                         "P_Z": float(ss["is_Z"].mean()) if len(ss) else float("nan")})
    tables["08_v2_signature_isZ"] = pd.DataFrame(rows)

    # ---- Table 08b : DI primes by (mod 8, v_2(pi)) ----
    DI_df = main[DI]
    rows = []
    for m in sorted(DI_df["mod8"].unique()):
        for k in sorted(DI_df[DI_df["mod8"] == m]["v2_pisano"].unique()):
            ss = DI_df[(DI_df["mod8"] == m) & (DI_df["v2_pisano"] == k)]
            rows.append({"mod8": int(m), "v2_pisano": int(k),
                         "count": len(ss),
                         "all_in_Z": bool(ss["is_Z"].all())})
    tables["08b_DI_mod8_v2_split"] = pd.DataFrame(rows)

    # ---- Table 09 : near-cancellation in Z^c ----
    not_Z_df = main[~Z]
    if len(not_Z_df):
        tables["09_near_cancellation"] = pd.DataFrame([
            {"threshold": t,
             "count_below": int((not_Z_df["abs_S"] <= t).sum()),
             "fraction_of_nonZ": float((not_Z_df["abs_S"] <= t).mean())}
            for t in (1, 2, 4, 8, 16, 32, 64)
        ])

    # ---- Tables 10..12 : Z \ DI ----
    ZmD_df = main[ZmD]
    if len(ZmD_df):
        d = ZmD_df["mod8"].value_counts().sort_index()
        tables["10_ZminusDI_mod8"] = pd.DataFrame(
            {"mod8": d.index.astype(int), "count": d.values})
        d = ZmD_df["pi_over_alpha"].value_counts().sort_index()
        tables["11_ZminusDI_pi_over_alpha"] = pd.DataFrame(
            {"pi_over_alpha": d.index.astype(int), "count": d.values})
        tables["12_ZminusDI_mod1_exceptions"] = ZmD_df[
            ZmD_df["mod8"] == 1
        ][["p", "pisano", "alpha", "pi_over_alpha",
           "mod8", "s", "chi_s", "T_alpha", "S_p", "signature"]].copy()

    # ---- Table 13 : T_alpha statistics ----
    cand_13 = main[(main["v2_pisano"] == 2) & (main["mod8"] == 1)]
    if len(cand_13):
        Ta = cand_13["T_alpha"].astype(float)
        alpha_vals = cand_13["alpha"].astype(float)
        tables["13_T_alpha_stats_mod1_v2eq2"] = pd.DataFrame([{
            "n"              : len(cand_13),
            "mean_T_alpha"   : float(Ta.mean()),
            "std_T_alpha"    : float(Ta.std()),
            "min_T_alpha"    : int(Ta.min()),
            "median_T_alpha" : float(Ta.median()),
            "max_T_alpha"    : int(Ta.max()),
            "n_T_alpha_eq_0" : int((Ta == 0).sum()),
            "rw_expected"    : float((1.0 / np.sqrt(alpha_vals)).sum()),
        }])

    # ---- Table 14 : delta(Z) decomposition ----
    cond_auto = (main["v2_pisano"] == 2) & (main["mod8"] == 5) & Z
    cond_rare = (main["v2_pisano"] == 2) & (main["mod8"] == 1) & Z
    tables["14_Z_density_decomposition"] = pd.DataFrame([
        {"component": "DI (doubly-inert, p == 3 or 7 mod 20)",
         "delta": float(DI.mean()), "count": int(DI.sum())},
        {"component": "Z and (v_2=2, p == 5 mod 8)  [auto-cancellation]",
         "delta": float(cond_auto.mean()), "count": int(cond_auto.sum())},
        {"component": "Z and (v_2=2, p == 1 mod 8)  [rare T_alpha=0]",
         "delta": float(cond_rare.mean()), "count": int(cond_rare.sum())},
        {"component": "TOTAL Z",
         "delta": float(Z.mean()), "count": int(Z.sum())},
    ])

    # ---- Table 15 : sanity checks (provable invariants) ----
    sanity: list[tuple[str, bool, int]] = []
    sanity.append((
        "S1: P(Z | DI) = 1   (Main result of the paper)",
        bool(ZaD.sum() == DI.sum()),
        int(DI.sum() - ZaD.sum()),
    ))
    if len(ZmD_df):
        sanity.append((
            "S2: pi/alpha = 4   for all p in Z \\ DI",
            bool((ZmD_df["pi_over_alpha"] == 4).all()),
            int((ZmD_df["pi_over_alpha"] != 4).sum()),
        ))
        sanity.append((
            "S3: v_2(pi) = 2   for all p in Z \\ DI",
            bool((ZmD_df["v2_pisano"] == 2).all()),
            int((ZmD_df["v2_pisano"] != 2).sum()),
        ))
    sanity.append((
        "S4: v_2(pi) >= 3   for all DI primes",
        bool((main[DI]["v2_pisano"] >= 3).all()),
        int((main[DI]["v2_pisano"] < 3).sum()),
    ))
    sub_DI_3 = main[DI & (main["mod8"] == 3)]
    sanity.append((
        "S5: DI and p == 3 (mod 8)  ==>  v_2(pi) = 3",
        bool((sub_DI_3["v2_pisano"] == 3).all()) if len(sub_DI_3) else True,
        int((sub_DI_3["v2_pisano"] != 3).sum()) if len(sub_DI_3) else 0,
    ))
    sub_DI_7 = main[DI & (main["mod8"] == 7)]
    sanity.append((
        "S6: DI and p == 7 (mod 8)  ==>  v_2(pi) >= 4",
        bool((sub_DI_7["v2_pisano"] >= 4).all()) if len(sub_DI_7) else True,
        int((sub_DI_7["v2_pisano"] < 4).sum()) if len(sub_DI_7) else 0,
    ))

    # S7-S8 : Main Theorem spot-check inside the sanity table
    cm_b1 = main[(main["signature"] == "cm_only") &
                 (main["alpha"] == main["p"] - 1)]
    if len(cm_b1):
        bad_11 = int(((cm_b1["mod20"] == 11) & (cm_b1["T_alpha"] != 1)).sum())
        bad_19 = int(((cm_b1["mod20"] == 19) & (cm_b1["T_alpha"] != -1)).sum())
        sanity.append(("S7: Main Thm  --  T_alpha = +1 for p == 11 (mod 20)",
                       bad_11 == 0, bad_11))
        sanity.append(("S8: Main Thm  --  T_alpha = -1 for p == 19 (mod 20)",
                       bad_19 == 0, bad_19))

    # S9 : vectorised sample-based check of s^2 == -1 (mod p) for Z \ DI
    if len(ZmD_df):
        sample = ZmD_df.sample(min(500, len(ZmD_df)), random_state=42)
        s_arr = sample["s"].astype(object).values
        p_arr = sample["p"].astype(object).values
        s_sq_mod_p = np.array(
            [(int(s) * int(s)) % int(pp) for s, pp in zip(s_arr, p_arr)],
            dtype=object,
        )
        expected = np.array([int(pp) - 1 for pp in p_arr], dtype=object)
        bad_s = int((s_sq_mod_p != expected).sum())
        sanity.append((
            f"S9: s^2 == -1 (mod p) on Z \\ DI  [sample n={len(sample)}]",
            bad_s == 0, bad_s,
        ))

    tables["15_sanity_checks"] = pd.DataFrame(
        sanity, columns=["invariant", "passes", "violations"]
    )

    # ---- Table 15b : empirical observations (NOT provable invariants) ----
    obs: list[dict[str, Any]] = []
    cm_Z_count = int(main[main["signature"] == "cm_only"]["is_Z"].sum())
    obs.append({
        "observation": "O1: cm_only never in Z  (so far, up to current N)",
        "holds"      : cm_Z_count == 0,
        "exceptions" : cm_Z_count,
        "note"       : "empirical; not yet proved",
    })
    if cm_Z_count > 0:
        obs.append({
            "observation": "    Counterexample primes:",
            "holds"      : False,
            "exceptions" : cm_Z_count,
            "note"       : ", ".join(
                str(p) for p in main[(main["signature"] == "cm_only") & Z]["p"].head(10)
            ),
        })
    tables["15b_empirical_observations"] = pd.DataFrame(obs)

    return tables, main


# ============================================================================
# SECTION 11.  Report formatting
# ============================================================================

def format_report(tables: dict[str, pd.DataFrame],
                  n_total: int, n_main: int) -> str:
    """Format all tables into a human-readable text report."""
    W = 78
    lines: list[str] = [
        "=" * W,
        f" FibChar v{__version__}  --  UNIFIED DIAGNOSTIC REPORT",
        f" {__paper__}",
        "=" * W,
        f"\n  Total primes in df    : {n_total:,}",
        f"  Main set (p != 2, 5)  : {n_main:,}",
    ]

    _TABLE_TITLES = [
        ("00_headline",                    "[ HEADLINE DENSITIES ]"),
        ("01_signature_counts",            "[ TABLE  1 ] Signature counts"),
        ("02_P_Z_given_signature",         "[ TABLE  2 ] P(Z | signature)"),
        ("03_Sp_stats_by_signature",       "[ TABLE  3 ] S(p) statistics per signature"),
        ("04_v2_per_class",                "[ TABLE  4 ] v_2(pi) per class"),
        ("04b_v2_distribution",            "[ TABLE 4b ] Full distribution of v_2(pi)"),
        ("05_mod20_distribution",          "[ TABLE  5 ] P(Z | p mod 20)"),
        ("06_mod8_distribution",           "[ TABLE  6 ] P(Z | p mod 8)"),
        ("07_2adic_tower",                 "[ TABLE  7 ] 2-adic tower  P(Z | v_2(pi) = k)"),
        ("08_v2_signature_isZ",            "[ TABLE  8 ] Cross-table: v_2 x signature x is_Z"),
        ("08b_DI_mod8_v2_split",           "[ TABLE 8b ] DI primes split by (mod 8, v_2)"),
        ("09_near_cancellation",           "[ TABLE  9 ] Near-cancellation in Z^c"),
        ("10_ZminusDI_mod8",               "[ TABLE 10 ] Z \\ DI  distribution by p mod 8"),
        ("11_ZminusDI_pi_over_alpha",      "[ TABLE 11 ] Z \\ DI  distribution of pi/alpha"),
        ("12_ZminusDI_mod1_exceptions",    "[ TABLE 12 ] Z \\ DI  exceptions (p = 1 mod 8)"),
        ("13_T_alpha_stats_mod1_v2eq2",    "[ TABLE 13 ] T_alpha stats (p=1 mod 8, v_2=2)"),
        ("14_Z_density_decomposition",     "[ TABLE 14 ] delta(Z) decomposition"),
        ("15_sanity_checks",               "[ TABLE 15 ] SANITY CHECKS  (provable; must PASS)"),
        ("15b_empirical_observations",     "[ TABLE 15b] EMPIRICAL OBSERVATIONS  (not yet proved)"),
        ("16_corollary_B1_verification",   "[ TABLE 16 ] Main Theorem verification"),
        ("16b_corollary_B1_failures",      "[ TABLE 16b] Main Theorem FAILURES (if any)"),
        ("17_empirical_claims_E1_to_E10",  "[ TABLE 17 ] All empirical claims E1..E10"),
        ("18_root_order_sign_summary",     "[ TABLE 18 ] Root / order / sign checks (summary)"),
    ]

    for name, title in _TABLE_TITLES:
        t = tables.get(name)
        if t is not None and len(t):
            lines.append("\n" + title)
            lines.append(t.to_string(index=False))

    # GO / NO-GO verdict
    hd = tables.get("00_headline")
    if hd is not None and len(hd):
        row = hd[hd["quantity"] == "delta(Z minus DI)"]
        if len(row):
            delta_ZmD = float(row["value"].iloc[0])
            if delta_ZmD < 0.005:
                verdict = "ESSENTIALLY EMPTY  (DI is the dominant source)"
            elif delta_ZmD < 0.020:
                verdict = "THIN  (small residual; possible finite-prime effect)"
            elif delta_ZmD < 0.050:
                verdict = "MARGINAL  (warrants further investigation)"
            else:
                verdict = "SUBSTANTIAL  --  hidden structure beyond DI!"
            lines.append("\n[ GO / NO-GO VERDICT ]")
            lines.append(f"    delta(Z \\ DI) = {delta_ZmD:.6f}   >>>  {verdict}")

    lines.append("\n" + "=" * W)
    return "\n".join(lines)


# ============================================================================
# SECTION 12.  Output saving (CSV, TXT, XLSX, LaTeX, JSON)
# ============================================================================

def _to_python(obj):
    """Recursively convert numpy/pandas scalars to plain Python types."""
    if isinstance(obj, dict):
        return {str(k): _to_python(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_python(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.ndarray,)):
        return [_to_python(x) for x in obj.tolist()]
    if pd.isna(obj) if not isinstance(obj, (str, bytes)) else False:
        return None
    return obj


def save_outputs(df: pd.DataFrame,
                 tables: dict[str, pd.DataFrame],
                 report_text: str,
                 out_dir: str,
                 N_max: int,
                 log_fn=print) -> None:
    """Save CSV, TXT report, and (optionally) XLSX to out_dir."""
    os.makedirs(out_dir, exist_ok=True)
    stem = f"fib_char_N{N_max}"

    csv_path = os.path.join(out_dir, stem + "_db.csv")
    df.to_csv(csv_path, index=False)
    log_fn(f"[+] saved CSV   -> {csv_path}")

    txt_path = os.path.join(out_dir, stem + "_report.txt")
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(report_text)
    log_fn(f"[+] saved TXT   -> {txt_path}")

    xlsx_path = os.path.join(out_dir, stem + "_report.xlsx")
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            raw = df if len(df) <= 1_000_000 else df.head(1_000_000)
            raw.to_excel(writer, sheet_name="raw_data", index=False)
            for name, t in tables.items():
                if len(t):
                    t.to_excel(writer, sheet_name=name[:31], index=False)
        log_fn(f"[+] saved XLSX  -> {xlsx_path}")
    except Exception as exc:
        log_fn(f"[!] XLSX save skipped ({exc}). CSV and TXT are available.")


def save_json_summary(tables: dict[str, pd.DataFrame],
                      run_meta: dict,
                      out_dir: str,
                      N_max: int,
                      self_test_ok: bool | None = None,
                      log_fn=print) -> None:
    """Write a JSON summary of headline numbers, theorem verifications,
    sanity checks, empirical claims, and root/order/sign checks.

    Keys are kept backward-compatible (both `main_theorem` and the old
    `corollary_b1` are populated with the same data).
    """
    os.makedirs(out_dir, exist_ok=True)
    summary: dict[str, Any] = {
        "fibchar_version": __version__,
        "paper"          : __paper__,
        "github"         : "https://github.com/Majid-Ghandali/"
                           "fibonacci-character-sum-full-rank",
        "zenodo"         : "https://doi.org/10.5281/zenodo.20707467",
        "run_parameters" : _to_python(run_meta),
        "headline"       : {},
        "main_theorem"   : {},
        "corollary_b1"   : {},   # backward-compatible alias
        "empirical_claims_E1_to_E10": [],
        "sanity_checks"  : [],
        "root_order_sign_checks": {},
        "self_test"      : {},
    }

    # Headline
    hd = tables.get("00_headline")
    if hd is not None:
        for _, row in hd.iterrows():
            key = str(row.get("quantity", "")).strip()
            if key:
                summary["headline"][key] = _to_python(row.to_dict())

    # Main Theorem
    b1 = tables.get("16_corollary_B1_verification")
    if b1 is not None:
        for _, row in b1.iterrows():
            key = f"p_mod_20_{_to_python(row.get('p_mod_20', -1))}"
            data = _to_python(row.to_dict())
            summary["main_theorem"][key] = data
            summary["corollary_b1"][key] = data

    # Empirical claims
    ec = tables.get("17_empirical_claims_E1_to_E10")
    if ec is not None:
        summary["empirical_claims_E1_to_E10"] = [
            _to_python(row.to_dict()) for _, row in ec.iterrows()
        ]

    # Sanity checks
    sc = tables.get("15_sanity_checks")
    if sc is not None:
        summary["sanity_checks"] = [
            _to_python(row.to_dict()) for _, row in sc.iterrows()
        ]

    # Root/order/sign checks (summary form)
    rc = tables.get("18_root_order_sign_summary")
    if rc is not None and len(rc):
        n_total_rc = (int(rc["n_tested"].iloc[0])
                      if "n_tested" in rc.columns and len(rc) else 0)
        all_pass = (rc["verdict"] == "PASS").all() if "verdict" in rc.columns else True
        summary["root_order_sign_checks"] = {
            "tested" : n_total_rc,
            "verdict": "PASS" if all_pass else "FAIL",
            "details": [_to_python(row.to_dict()) for _, row in rc.iterrows()],
        }

    if self_test_ok is not None:
        summary["self_test"] = {
            "verdict": "PASS" if self_test_ok else "FAIL",
        }

    json_path = os.path.join(out_dir, f"fib_char_N{N_max}_summary.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    log_fn(f"[+] saved JSON  -> {json_path}")


def export_latex_tables(tables: dict[str, pd.DataFrame],
                        out_dir: str, log_fn=print) -> None:
    """Write each non-empty table as a booktabs-ready .tex file."""
    latex_dir = os.path.join(out_dir, "latex_tables")
    os.makedirs(latex_dir, exist_ok=True)

    def _col_fmt(t: pd.DataFrame) -> str:
        return "".join(
            "r" if pd.api.types.is_numeric_dtype(t[c]) else "l"
            for c in t.columns
        )

    n_written = 0
    for name, t in tables.items():
        if len(t) == 0:
            continue
        path = os.path.join(latex_dir, f"{name}.tex")
        try:
            # Modern API (pandas >= 1.3): Styler.to_latex
            styler = t.style.format(escape="latex")
            try:
                styler = styler.hide(axis="index")
            except (TypeError, AttributeError):
                styler = styler.hide_index()
            latex_str = styler.to_latex(
                column_format=_col_fmt(t),
                hrules=True,
            )
        except (AttributeError, TypeError):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                latex_str = t.to_latex(
                    index=False, escape=True,
                    column_format=_col_fmt(t),
                    bold_rows=False,
                )

        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"% Auto-generated by FibChar v{__version__}\n")
            fh.write(f"% Table: {name}\n")
            fh.write(latex_str)
        n_written += 1
    log_fn(f"[+] LaTeX tables -> {latex_dir}/  ({n_written} files)")


# ============================================================================
# SECTION 13.  GUI  (optional; Tkinter required)
# ============================================================================

if _TKINTER_AVAILABLE:

    class FibCharApp(tk.Tk):
        """Interactive Tkinter GUI for FibChar."""

        def __init__(self) -> None:
            super().__init__()
            self.title(f"FibChar v{__version__}  --  {__author__}")
            self.geometry("1200x860")
            self._queue: queue.Queue = queue.Queue()
            self._worker: threading.Thread | None = None
            self._stop_event: threading.Event = threading.Event()
            self._build_ui()
            self.after(100, self._poll_queue)

        def _build_ui(self) -> None:
            top = ttk.Frame(self, padding=8); top.pack(fill="x")
            ttk.Label(top, text="N_MAX:").pack(side="left")
            self._n_var = tk.StringVar(value="1000000")
            ttk.Entry(top, textvariable=self._n_var, width=12).pack(side="left", padx=4)

            ttk.Label(top, text="Output folder:").pack(side="left", padx=(12, 0))
            self._dir_var = tk.StringVar(value=os.path.abspath("FibChar_Output"))
            ttk.Entry(top, textvariable=self._dir_var, width=36).pack(side="left", padx=4)
            ttk.Button(top, text="Browse...", command=self._pick_dir).pack(side="left")

            self._run_btn = ttk.Button(top, text="Run", command=self._on_run)
            self._run_btn.pack(side="left", padx=(12, 2))
            self._stop_btn = ttk.Button(top, text="Stop & Checkpoint",
                                        command=self._on_stop, state="disabled")
            self._stop_btn.pack(side="left", padx=2)
            ttk.Button(top, text="Self-test",
                       command=self._on_self_test).pack(side="left", padx=(12, 2))

            th = ttk.Frame(self, padding=(8, 0, 8, 4)); th.pack(fill="x")
            ttk.Label(th, text="array <").pack(side="left")
            self._th_arr = tk.StringVar(value=str(TH_ARRAY_DEFAULT))
            ttk.Entry(th, textvariable=self._th_arr, width=12).pack(side="left")
            ttk.Label(th, text="  bitwise <").pack(side="left")
            self._th_bw = tk.StringVar(value=str(TH_BITWISE_DEFAULT))
            ttk.Entry(th, textvariable=self._th_bw, width=12).pack(side="left")
            ttk.Label(th, text="  pow >= (above)").pack(side="left")

            pr = ttk.Frame(self, padding=(8, 0, 8, 4)); pr.pack(fill="x")
            self._prog = ttk.Progressbar(pr, length=200, mode="determinate", maximum=100)
            self._prog.pack(fill="x", side="left", expand=True)
            self._pct_lbl = ttk.Label(pr, text="  0.0%")
            self._pct_lbl.pack(side="left", padx=6)

            tb = ttk.Frame(self, padding=(8, 0, 8, 2)); tb.pack(fill="x")
            ttk.Label(tb, text="Log / Report").pack(side="left")
            ttk.Button(tb, text="Copy all",       command=self._copy_all).pack(side="right", padx=2)
            ttk.Button(tb, text="Copy selection", command=self._copy_sel).pack(side="right", padx=2)
            ttk.Button(tb, text="Save .txt",      command=self._save_log_txt).pack(side="right", padx=2)
            ttk.Button(tb, text="Clear",
                       command=lambda: self._log_widget.delete("1.0", "end")).pack(side="right", padx=2)

            body = ttk.Frame(self, padding=(8, 0, 8, 4)); body.pack(fill="both", expand=True)
            self._log_widget = scrolledtext.ScrolledText(body, font=("Consolas", 10),
                                                        wrap="none", undo=False)
            self._log_widget.pack(fill="both", expand=True)
            self._log_widget.bind("<Control-a>",
                lambda e: (self._log_widget.tag_add("sel", "1.0", "end"), "break"))
            self._install_context_menu()

            bar = ttk.Frame(self, padding=(8, 0, 8, 8)); bar.pack(fill="x")
            numba_txt = "Numba: ON" if HAS_NUMBA else "Numba: OFF"
            ttk.Label(bar, text=numba_txt).pack(side="left")
            ttk.Label(bar, text=f"  v{__version__}").pack(side="left")
            self._status_lbl = ttk.Label(bar, text="idle.")
            self._status_lbl.pack(side="right")

        def _install_context_menu(self) -> None:
            menu = tk.Menu(self._log_widget, tearoff=0)
            menu.add_command(label="Copy selection", command=self._copy_sel)
            menu.add_command(label="Copy all",       command=self._copy_all)
            menu.add_separator()
            menu.add_command(label="Select all",
                command=lambda: self._log_widget.tag_add("sel", "1.0", "end"))
            menu.add_command(label="Save as .txt...", command=self._save_log_txt)
            def _show(e):
                try: menu.tk_popup(e.x_root, e.y_root)
                finally: menu.grab_release()
            for seq in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
                self._log_widget.bind(seq, _show)

        def _append_log(self, msg: str) -> None:
            self._log_widget.insert("end", msg + "\n")
            self._log_widget.see("end")

        def _log(self, msg: str) -> None:
            self._queue.put(("log", msg))

        def _set_progress(self, fraction: float) -> None:
            self._queue.put(("prog", fraction))

        def _poll_queue(self) -> None:
            try:
                while True:
                    kind, payload = self._queue.get_nowait()
                    if kind == "log":
                        self._append_log(str(payload))
                    elif kind == "prog":
                        pct = max(0.0, min(1.0, float(payload))) * 100
                        self._prog["value"] = pct
                        self._pct_lbl.configure(text=f" {pct:5.1f}%")
                    elif kind == "done":
                        self._run_btn.configure(state="normal")
                        self._stop_btn.configure(state="disabled")
                        self._status_lbl.configure(text=str(payload or "idle."))
            except queue.Empty:
                pass
            self.after(100, self._poll_queue)

        def _copy_sel(self) -> None:
            try:
                text = self._log_widget.get("sel.first", "sel.last")
            except tk.TclError:
                self._status_lbl.configure(text="no selection.")
                return
            if text:
                self.clipboard_clear(); self.clipboard_append(text)
                self._status_lbl.configure(text="selection copied.")

        def _copy_all(self) -> None:
            text = self._log_widget.get("1.0", "end-1c")
            self.clipboard_clear(); self.clipboard_append(text)
            self._status_lbl.configure(text=f"copied {len(text):,} chars.")

        def _save_log_txt(self) -> None:
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile="fib_char_log.txt")
            if not path: return
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._log_widget.get("1.0", "end-1c"))
            self._status_lbl.configure(text=f"saved -> {path}")

        def _pick_dir(self) -> None:
            d = filedialog.askdirectory(initialdir=self._dir_var.get())
            if d: self._dir_var.set(d)

        def _on_self_test(self) -> None:
            self._append_log("")
            run_self_test(log_fn=self._append_log)

        def _on_stop(self) -> None:
            if self._worker and self._worker.is_alive():
                self._stop_event.set()
                self._append_log("[!] STOP requested ...")
                self._stop_btn.configure(state="disabled")
                self._status_lbl.configure(text="stopping ...")

        def _on_run(self) -> None:
            try:
                N = int(self._n_var.get())
                if N < 10: raise ValueError
                th_a = int(self._th_arr.get())
                th_b = int(self._th_bw.get())
                if not (0 < th_a <= th_b): raise ValueError
            except ValueError:
                messagebox.showerror("Invalid input",
                    "N_MAX must be >= 10  and  0 < th_array <= th_bitwise.")
                return

            out_dir = self._dir_var.get().strip() or "FibChar_Output"

            resume_payload = None
            ckpt = load_checkpoint(out_dir, N)
            if ckpt is not None:
                cdf, meta = ckpt
                pct = 100.0 * meta["last_index"] / max(meta["total_primes"], 1)
                ans = messagebox.askyesnocancel(
                    "Checkpoint found",
                    f"A checkpoint exists for N_MAX = {N:,}:\n\n"
                    f"  Progress : {meta['last_index']:,} / {meta['total_primes']:,}"
                    f"  ({pct:.1f}%)\n"
                    f"  Saved at : {meta.get('timestamp', '?')}\n"
                    f"  Elapsed  : {meta.get('elapsed_sec', 0):.0f} s\n\n"
                    "Yes = RESUME     No = START FRESH     Cancel = do nothing")
                if ans is None: return
                if ans: resume_payload = (cdf, meta)
                else:   delete_checkpoint(out_dir, N)

            self._stop_event.clear()
            self._run_btn.configure(state="disabled")
            self._stop_btn.configure(state="normal")
            self._status_lbl.configure(text="running ...")
            self._log_widget.delete("1.0", "end")
            self._prog["value"] = 0
            self._pct_lbl.configure(text="  0.0%")

            self._worker = threading.Thread(
                target=self._pipeline,
                args=(N, out_dir, resume_payload, th_a, th_b),
                daemon=True)
            self._worker.start()

        def _pipeline(self, N: int, out_dir: str,
                      resume_payload, th_a: int, th_b: int) -> None:
            try:
                self._log(f"[+] FibChar v{__version__}  N_MAX = {N:,}")
                kwargs = dict(out_dir=out_dir, log_fn=self._log,
                              progress_fn=self._set_progress,
                              th_array=th_a, th_bitwise=th_b,
                              stop_event=self._stop_event)
                if resume_payload is None:
                    df = build_database(N, **kwargs)
                else:
                    cdf, meta = resume_payload
                    df = build_database(N, resume_df=cdf, resume_meta=meta, **kwargs)

                if df is None:
                    self._queue.put(("done", "stopped (checkpoint saved)."))
                    return

                self._log("[+] Computing diagnostic tables ...")
                tables, _ = compute_all_tables(df)

                self._log("[+] Verifying empirical claims E1..E10 ...")
                ec = verify_all_empirical_claims(df, log_fn=self._log)
                tables["17_empirical_claims_E1_to_E10"] = ec

                self._log("[+] Verifying Main Theorem ...")
                b1, b1f = verify_corollary_b1(df, log_fn=self._log)
                tables["16_corollary_B1_verification"] = b1
                if len(b1f):
                    tables["16b_corollary_B1_failures"] = b1f

                self._log("[+] Verifying root/order/sign checks ...")
                root_checks = verify_root_order_sign_checks(df, log_fn=self._log)
                tables["18_root_order_sign_summary"] = _summarize_root_checks(root_checks)

                os.makedirs(out_dir, exist_ok=True)
                root_csv = os.path.join(out_dir,
                    f"fib_char_N{N}_root_order_sign_checks.csv")
                root_checks.to_csv(root_csv, index=False)
                self._log(f"[+] root/order/sign checks (detailed) -> {root_csv}")

                report = format_report(tables, len(df),
                                       len(df[~df["p"].isin([2, 5])]))
                self._log("\n" + report)
                save_outputs(df, tables, report, out_dir, N, self._log)

                b1_csv = os.path.join(out_dir, f"fib_char_N{N}_main_theorem.csv")
                b1.to_csv(b1_csv, index=False)
                self._log(f"[+] saved Main Theorem CSV -> {b1_csv}")

                ec_csv = os.path.join(out_dir,
                    f"fib_char_N{N}_empirical_claims.csv")
                ec.to_csv(ec_csv, index=False)
                self._log(f"[+] saved empirical claims CSV -> {ec_csv}")

                run_meta = {
                    "N_max"     : N,
                    "th_array"  : th_a,
                    "th_bitwise": th_b,
                    "parallel"  : False,
                    "resumed"   : resume_payload is not None,
                }
                save_json_summary(tables, run_meta, out_dir, N, log_fn=self._log)

                export_latex_tables(tables, out_dir, log_fn=self._log)
                delete_checkpoint(out_dir, N)
                self._queue.put(("done", "completed successfully."))

            except Exception as exc:
                import traceback
                self._log(f"\n[ERROR] {exc!r}")
                self._log(traceback.format_exc())
                self._queue.put(("done", f"ERROR: {exc!r}"))


# ============================================================================
# SECTION 14.  CLI pipeline
# ============================================================================

def cli_pipeline(args: argparse.Namespace) -> int:
    """Run the sequential or parallel pipeline from the command line."""
    N       = args.N
    out_dir = args.out_dir
    th_a    = args.th_array
    th_b    = args.th_bitwise

    def log(msg: str) -> None:
        print(msg, flush=True)

    if args.self_test:
        ok = run_self_test(log_fn=log)
        return 0 if ok else 1

    if not (0 < th_a <= th_b):
        log("[!] Require 0 < --th-array <= --th-bitwise.")
        return 1

    if args.parallel and args.workers < 1:
        log("[!] Require --workers >= 1 in parallel mode.")
        return 1

    if args.chunk_size < 1:
        log("[!] Require --chunk-size >= 1.")
        return 1

    resume_df: pd.DataFrame | None = None
    resume_meta: dict | None = None

    if args.resume:
        ckpt = load_checkpoint(out_dir, N)
        if ckpt is not None:
            resume_df, resume_meta = ckpt
            pct = 100.0 * resume_meta["last_index"] / max(resume_meta["total_primes"], 1)
            log(f"[+] Resuming from checkpoint: "
                f"{resume_meta['last_index']:,} / {resume_meta['total_primes']:,} "
                f"({pct:.1f}%)")
        else:
            log("[!] --resume specified but no checkpoint found.  Starting fresh.")
    elif not args.parallel:
        ckpt = load_checkpoint(out_dir, N)
        if ckpt is not None:
            log("[!] Stale checkpoint found; deleting before fresh run.")
            delete_checkpoint(out_dir, N)

    t0 = time.perf_counter()

    if args.parallel:
        # Auto-tune chunk size: ~50 chunks per worker for load balance
        primes_count_est = max(N // (max(int(np.log(N) - 1), 1)), 100) if N > 10 else 100
        target_chunks = args.workers * 50
        auto_chunk = max(500, int(primes_count_est / max(target_chunks, 1)))
        chunk_size_used = max(args.chunk_size, auto_chunk)
        if chunk_size_used != args.chunk_size:
            log(f"[+] Auto-tuned chunk size: {args.chunk_size} -> {chunk_size_used} "
                f"(targeting ~{target_chunks} chunks for {args.workers} workers)")
        log(f"[+] Parallel pipeline: workers={args.workers}, "
            f"chunk_size={chunk_size_used}")
        if HAS_NUMBA:
            log("[+] Warming JIT (main process) ...")
            _warmup_jit()
        primes = sieve_primes(N)
        log(f"[+] Primes <= {N:,}: {len(primes):,}")
        df = build_database_parallel(
            primes, workers=args.workers, chunk_size=chunk_size_used,
            th_array=th_a, th_bitwise=th_b, log_fn=log,
        )
        if df is None:
            log("[!] CRITICAL: build_database_parallel returned None.")
            log("[!] This indicates the function definition is incomplete "
                "(missing 'return df' at end).")
            return 1
        if len(df) == 0:
            log("[!] build_database_parallel produced 0 rows; aborting.")
            return 1
    else:
        df = build_database(
            N, out_dir=out_dir, log_fn=log, progress_fn=lambda x: None,
            th_array=th_a, th_bitwise=th_b,
            resume_df=resume_df, resume_meta=resume_meta, stop_event=None,
        )
        if df is None:
            log("[!] Build returned None (stopped early).")
            return 2

    elapsed = time.perf_counter() - t0
    log(f"[+] Total compute time: {elapsed:.2f}s  ({len(df):,} rows)")

    log("[+] Computing diagnostic tables ...")
    tables, _ = compute_all_tables(df)

    log("[+] Verifying empirical claims E1..E10 ...")
    ec = verify_all_empirical_claims(df, log_fn=log)
    tables["17_empirical_claims_E1_to_E10"] = ec

    if args.verify_b1:
        b1, b1f = verify_corollary_b1(df, log_fn=log)
        tables["16_corollary_B1_verification"] = b1
        if len(b1f):
            tables["16b_corollary_B1_failures"] = b1f

        b1_csv = os.path.join(out_dir, f"fib_char_N{N}_main_theorem.csv")
        b1.to_csv(b1_csv, index=False)
        log(f"[+] Main Theorem CSV -> {b1_csv}")

        root_checks = verify_root_order_sign_checks(df, log_fn=log)
        root_csv = os.path.join(out_dir,
            f"fib_char_N{N}_root_order_sign_checks.csv")
        root_checks.to_csv(root_csv, index=False)
        log(f"[+] root/order/sign checks (detailed) -> {root_csv}")
        tables["18_root_order_sign_summary"] = _summarize_root_checks(root_checks)

    report = format_report(tables, len(df),
                           len(df[~df["p"].isin([2, 5])]))
    print(report, flush=True)

    save_outputs(df, tables, report, out_dir, N, log_fn=log)
    export_latex_tables(tables, out_dir, log_fn=log)

    ec_csv = os.path.join(out_dir, f"fib_char_N{N}_empirical_claims.csv")
    ec.to_csv(ec_csv, index=False)
    log(f"[+] Empirical claims CSV -> {ec_csv}")

    run_meta = {
        "N_max"     : N,
        "th_array"  : th_a,
        "th_bitwise": th_b,
        "parallel"  : args.parallel,
        "workers"   : args.workers if args.parallel else None,
        "chunk_size": args.chunk_size if args.parallel else None,
        "resumed"   : args.resume and resume_df is not None,
    }
    save_json_summary(tables, run_meta, out_dir, N, log_fn=log)

    if not args.parallel:
        delete_checkpoint(out_dir, N)

    log("[+] Done.")
    return 0


# ============================================================================
# SECTION 15.  Argument parser
# ============================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=os.path.basename(sys.argv[0]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"FibChar v{__version__}  --  {__paper__}",
        epilog="""
Examples
--------
  Reproduce the paper's N=10^6 run with full verification:
      %(prog)s --no-gui --N 1000000 --verify-b1

  Larger run (N=2*10^6), faster via multi-process:
      %(prog)s --no-gui --N 2000000 --verify-b1 --parallel --workers 8 --chunk-size 5000

  Quick self-test (5 Appendix-A examples, ~instant):
      %(prog)s --self-test

  Resume an interrupted sequential run:
      %(prog)s --no-gui --N 2000000 --verify-b1 --resume

  Interactive GUI (default if Tkinter is available):
      %(prog)s
""")

    p.add_argument("--N", type=int, default=1_000_000, metavar="N_MAX",
        help="Compute all primes <= N_MAX  (default: 1,000,000)")
    p.add_argument("--out-dir", default="FibChar_Output", metavar="DIR",
        help="Output directory  (default: FibChar_Output)")
    p.add_argument("--no-gui", action="store_true",
        help="Force CLI mode (ignore Tkinter even if available)")
    p.add_argument("--self-test", action="store_true",
        help="Run the five Appendix-A worked examples and exit")
    p.add_argument("--verify-b1", action="store_true",
        help="Run Main Theorem + root/order/sign verifications after compute")
    p.add_argument("--resume", action="store_true",
        help="Resume from the most recent checkpoint (sequential only)")
    p.add_argument("--parallel", action="store_true",
        help="Use the multi-process pipeline (no checkpoint/resume)")
    p.add_argument("--workers", type=int, default=_DEFAULT_WORKERS, metavar="W",
        help=f"Worker processes for --parallel  (default: {_DEFAULT_WORKERS})")
    p.add_argument("--chunk-size", type=int, default=500, metavar="C",
        help="Primes per parallel task  (default: 500).  "
             "Smaller chunks improve load balance on the tail of the run "
             "(where the largest primes are most expensive); larger chunks "
             "reduce IPC overhead but risk long stragglers.")
    p.add_argument("--th-array", type=int, default=TH_ARRAY_DEFAULT, metavar="T",
        help=f"QR-table backend threshold  (default: {TH_ARRAY_DEFAULT:,})")
    p.add_argument("--th-bitwise", type=int, default=TH_BITWISE_DEFAULT, metavar="T",
        help=f"Bitwise-Jacobi backend threshold  (default: {TH_BITWISE_DEFAULT:,})")
    p.add_argument("--version", action="version",
        version=f"FibChar v{__version__}  (author: {__author__})")
    return p


# ============================================================================
# SECTION 16.  Main entry point
# ============================================================================

def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    use_gui = _TKINTER_AVAILABLE and not args.no_gui and not args.self_test
    if use_gui:
        app = FibCharApp()
        app.mainloop()
    else:
        sys.exit(cli_pipeline(args))


if __name__ == "__main__":
    main()

# Fibchar_v1-0-0.py


"""
================================================================================
 FibChar v1.0.0  --  Fibonacci Character-Sum Research Suite
================================================================================

Reproducibility code for:

    "A Fibonacci Character Sum Identity for Primes of Full Rank
     of Apparition"
    Majid Ghandali  --  Journal of Number Theory (submitted)

    GitHub : https://github.com/Majid-Ghandali/fibonacci-character-sum-full-rank
    Zenodo : https://doi.org/10.5281/zenodo.20707467
  
--------------------------------------------------------------------------------
MATHEMATICAL SUMMARY
--------------------------------------------------------------------------------
For an odd prime p != 5, define:

    pi(p)    : Pisano period  (least k > 0 with F_k == 0, F_{k+1} == 1 mod p)
    alpha(p) : rank of apparition (least m >= 1 with p | F_m)
    S(p)     : full Pisano character sum  sum_{n=1}^{pi(p)} chi_p(F_n)
    T(p)     : partial sum               sum_{n=1}^{alpha(p)} chi_p(F_n)

The paper's Main Theorem (Corollary B1) states:

    If alpha(p) = p-1, then p == 11 or 19 (mod 20), and
        S(p) = T(p) = +1   when p == 11 (mod 20)
        S(p) = T(p) = -1   when p == 19 (mod 20)

NOTE: S(p) = sum_{n=1}^{pi(p)} chi_p(F_n) is the FULL Pisano-period sum.
      It equals sum_{n=1}^{p-1} chi_p(F_n) ONLY in the special case
      alpha(p) = p-1 (Corollary B1 regime). In general pi(p) != p-1.

--------------------------------------------------------------------------------
ARITHMETIC REGIMES
--------------------------------------------------------------------------------
Primes are classified by (chi_p(-1), chi_p(5)):

    DI        : chi_p(-1) = -1, chi_p(5) = -1   (doubly-inert)
    fib_only  : chi_p(-1) = +1, chi_p(5) = -1
    cm_only   : chi_p(-1) = -1, chi_p(5) = +1
    neither   : chi_p(-1) = +1, chi_p(5) = +1

The paper proves S(p) = 0 for ALL doubly-inert primes.

--------------------------------------------------------------------------------
WHAT THIS PROGRAM COMPUTES
--------------------------------------------------------------------------------
For every odd prime p < N_max (p != 5), in a single Fibonacci walk mod p:

    * chi_p(-1), chi_p(5), arithmetic regime (signature)
    * pi(p), v_2(pi(p)), alpha(p), pi(p)/alpha(p)
    * s = F_{alpha(p)+1} mod p and chi_p(s)
    * T(p) = sum_{n=1}^{alpha(p)} chi_p(F_n)   [partial sum]
    * S(p) = sum_{n=1}^{pi(p)} chi_p(F_n)      [full Pisano sum]
    * plus, minus, zeros counts over the full Pisano period

It then machine-verifies the Main Theorem / Corollary B1 and produces
diagnostic tables (Tables 1-16 of the working notes).

--------------------------------------------------------------------------------
THREE HOT-LOOP BACKENDS
--------------------------------------------------------------------------------
Backend A (array)   : QR lookup table,   O(p) memory,  fastest
Backend B (bitwise) : bitwise Jacobi,    O(1) memory,  ~2-3x slower
Backend C (pow)     : Euler's criterion, O(1) memory,  most memory-frugal

Dispatch thresholds (tunable):
    p < TH_ARRAY    -> Backend A
    p < TH_BITWISE  -> Backend B
    p >= TH_BITWISE -> Backend C

--------------------------------------------------------------------------------
DEPENDENCIES
--------------------------------------------------------------------------------
    numpy, pandas             (required)
    numba                     (optional; ~50-100x speedup; falls back to
                               pure Python transparently if absent)
    pyarrow or fastparquet    (optional; needed for .parquet checkpoints;
                               falls back to .csv)
    openpyxl                  (optional; needed for .xlsx export)
    tkinter                   (optional; needed for GUI)

--------------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------------
    # Reproduce the paper's N=10^6 run (Tables 1-16 + Corollary B1):
    python fibchar_v1-0-0.py --no-gui --N 1000000 --verify-b1

    # Quick self-test 6 worked examples from Appendix A, ~instant):
    python fibchar_v1-0-0.py --self-test

    # Multi-process run (faster, no checkpointing):
    python fibchar_v6.py --no-gui --N 1000000 --verify-b1 \\
           --parallel --workers 8 --chunk-size 5000

    # Resume an interrupted sequential run:
    python fibchar_v1-0-0.py --no-gui --N 1000000 --verify-b1 --resume

    # Interactive GUI (checkpoint/resume, live log, progress bar):
    python fibchar_v1-0-0.py

--------------------------------------------------------------------------------
REPRODUCIBILITY NOTES
--------------------------------------------------------------------------------
  * Checkpoint/resume is available ONLY for the sequential pipeline
    (default, without --parallel).
  * The --parallel pipeline runs start-to-finish without checkpointing;
    for N = 10^6 on a modern multi-core machine this is fast enough.
  * On first run with Numba, a one-off JIT compilation cost (~a few
    seconds) occurs and is logged explicitly so it does not inflate
    timing measurements.
  * All arithmetic is exact (no floating-point in the hot loop).
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
__version__: str = "V 1.0.0"
__author__: str = "Majid Ghandali"
__paper__: str = (
    "A Fibonacci Character Sum Identity for Primes of Full Rank "
    "of Apparition (Journal of Number Theory, submitted)"
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
CHECKPOINT_EVERY: int = 2_000
LOG_INTERVAL: int = 5_000
TH_ARRAY_DEFAULT: int = 1_000_000
TH_BITWISE_DEFAULT: int = 10_000_000

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

_WALK_SENTINEL: int = -1


# ============================================================================
# SECTION 1.  Pure-Python number-theoretic helpers
# ============================================================================

def sieve_primes(N: int, segment_size: int = 1 << 18) -> np.ndarray:
    """Return all primes <= N as a sorted int64 array (segmented sieve)."""
    if N < 2:
        return np.array([], dtype=np.int64)
    if N < 5_000_000:
        sieve = np.ones(N + 1, dtype=bool)
        sieve[0] = sieve[1] = False
        for i in range(2, int(N ** 0.5) + 1):
            if sieve[i]:
                sieve[i * i :: i] = False
        return np.flatnonzero(sieve).astype(np.int64)

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
    """Jacobi symbol (a/n) for odd positive n."""
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
    """2-adic valuation v_2(n).  v_2(0) = -1 (sentinel)."""
    if n == 0:
        return -1
    k = 0
    while (n & 1) == 0:
        n >>= 1
        k += 1
    return k


def v2_array(arr: np.ndarray) -> np.ndarray:
    """Vectorised 2-adic valuation; ~200x faster than apply(v2)."""
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
    """Classify p by (chi_p(-1), chi_p(5)) using direct modular formulas.

    5x faster than two Jacobi calls; correct for p != 2, 5.
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
# SECTION 2.  Hot-loop backends  (Numba-JIT compiled when available)
# ============================================================================
# The correct structure :
#   1. accumulate chi_p(F_n)          <- contributes to S_p and detects alpha
#   2. advance (f_prev, f_curr)        <- update the Fibonacci pair
#   3. capture s=F_{alpha+1}, T_alpha  <- AFTER advancing past alpha
#   4. check termination               <- fires when new pair = (0,1)
#
# With this order, the termination check at n=pi fires when
#   (f_prev, f_curr) = (F_{pi}, F_{pi+1}) = (0, 1),
# which is correct: n = pi is returned as the Pisano period.
#
#  S = np.int64(0) in core_walk_array.
#   In pure-Python mode (no Numba), chi = qr[f_curr] is np.int8.  Adding
#   it to a Python int or np.int8 S causes int8 overflow for |S| > 127.
#   Initialising S = np.int64(0) ensures accumulation stays in int64 in
#   both pure-Python and Numba-JIT modes.
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
    """Modular exponentiation via repeated squaring (JIT-friendly).

    Safety: int64 arithmetic; safe for mod < 2^31 ~ 2.1e9.
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
    """chi_p(x) via Euler's criterion; chi_p(0) = 0."""
    if x == 0:
        return 0
    r = _modpow_jit(x, half, p)
    return 1 if r == 1 else -1


# ----------------------------------------------------------------------------
# Backend A : QR lookup table  
# ----------------------------------------------------------------------------

@njit(cache=True)
def _core_walk_array(p: int):
    """Backend A:  QR lookup table.  O(p) memory; fastest for p < ~1e6."""
    qr = np.full(p, -1, dtype=np.int8)
    qr[0] = 0
    for x in range(1, p):
        qr[(x * x) % p] = 1

    f_prev, f_curr = 0, 1
    S = np.int64(0)          # explicit int64: avoids np.int8 overflow in pure-Python
    plus = minus = zeros = 0
    alpha = -1
    s_val = -1
    T_alpha = np.int64(0)
    captured_alpha = False

    LIMIT = 6 * p + 10
    for n in range(1, LIMIT):
        # --- 1. Accumulate chi_p(F_n) ---
        chi = qr[f_curr]
        S += chi
        if chi == 1:
            plus += 1
        elif chi == -1:
            minus += 1
        else:
            zeros += 1

        # --- 2. Detect alpha(p) = least n with chi_p(F_n) = 0 ---
        if not captured_alpha and chi == 0:
            alpha = n

        # --- 3. Advance the Fibonacci pair ---
        nxt = (f_prev + f_curr) % p
        f_prev, f_curr = f_curr, nxt

        # --- 4. Capture s = F_{alpha+1} and T_alpha right after the advance ---
        if not captured_alpha and alpha == n:
            s_val = f_curr        # f_curr is now F_{n+1} = F_{alpha+1}
            T_alpha = S
            captured_alpha = True

        # --- 5. Termination: AFTER advance, check (F_n, F_{n+1}) = (0, 1) ---
        if f_prev == 0 and f_curr == 1:
            chi_s = qr[s_val] if s_val >= 0 else np.int8(0)
            return n, S, plus, minus, zeros, alpha, s_val, chi_s, T_alpha

    return _WALK_SENTINEL, np.int64(0), 0, 0, 0, -1, -1, np.int8(0), np.int64(0)


# ----------------------------------------------------------------------------
# Backend B : bitwise Jacobi  
# ----------------------------------------------------------------------------

@njit(cache=True)
def _core_walk_bitwise(p: int):
    """Backend B:  bitwise Jacobi.  O(1) memory; ~2-3x slower than A."""
    f_prev, f_curr = 0, 1
    S = 0
    plus = minus = zeros = 0
    alpha = -1
    s_val = -1
    T_alpha = 0
    captured_alpha = False

    LIMIT = 6 * p + 10
    for n in range(1, LIMIT):
        # --- 1. Accumulate ---
        chi = _jacobi_jit(f_curr, p)
        S += chi
        if chi == 1:
            plus += 1
        elif chi == -1:
            minus += 1
        else:
            zeros += 1

        # --- 2. Detect alpha ---
        if not captured_alpha and chi == 0:
            alpha = n

        # --- 3. Advance ---
        nxt = (f_prev + f_curr) % p
        f_prev, f_curr = f_curr, nxt

        # --- 4. Capture s, T_alpha ---
        if not captured_alpha and alpha == n:
            s_val = f_curr
            T_alpha = S
            captured_alpha = True

        # --- 5. Termination AFTER advance ---
        if f_prev == 0 and f_curr == 1:
            chi_s = _jacobi_jit(s_val, p) if s_val >= 0 else 0
            return n, S, plus, minus, zeros, alpha, s_val, chi_s, T_alpha

    return _WALK_SENTINEL, 0, 0, 0, 0, -1, -1, 0, 0


# ----------------------------------------------------------------------------
# Backend C : Euler criterion via modpow   
# ----------------------------------------------------------------------------

@njit(cache=True)
def _core_walk_pow(p: int):
    """Backend C:  Euler's criterion via modpow.  O(1) memory."""
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
        # --- 1. Accumulate ---
        chi = _chi_zero_safe_pow(f_curr, half, p)
        S += chi
        if chi == 1:
            plus += 1
        elif chi == -1:
            minus += 1
        else:
            zeros += 1

        # --- 2. Detect alpha ---
        if not captured_alpha and chi == 0:
            alpha = n

        # --- 3. Advance ---
        nxt = (f_prev + f_curr) % p
        f_prev, f_curr = f_curr, nxt

        # --- 4. Capture s, T_alpha ---
        if not captured_alpha and alpha == n:
            s_val = f_curr
            T_alpha = S
            captured_alpha = True

        # --- 5. Termination AFTER advance ---
        if f_prev == 0 and f_curr == 1:
            chi_s = _chi_zero_safe_pow(s_val, half, p) if s_val >= 0 else 0
            return n, S, plus, minus, zeros, alpha, s_val, chi_s, T_alpha

    return _WALK_SENTINEL, 0, 0, 0, 0, -1, -1, 0, 0


def _core_walk(p: int,
               th_array: int = TH_ARRAY_DEFAULT,
               th_bitwise: int = TH_BITWISE_DEFAULT) -> tuple:
    if p < th_array:
        return _core_walk_array(p)
    if p < th_bitwise:
        return _core_walk_bitwise(p)
    return _core_walk_pow(p)


def _warmup_jit() -> None:
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
    c1, c5, sig = signature_label(p)
    result = _core_walk(p, th_array, th_bitwise)
    period = int(result[0])

    if period == _WALK_SENTINEL:
        raise RuntimeError(
            f"analyze_prime: hot loop exceeded LIMIT=6*p+10 for p={p}. "
            "Please report as a bug."
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

_SELF_TEST_CASES: dict[int, int] = {11: +1, 19: -1, 31: +1, 59: -1, 79: -1}


def run_self_test(log_fn=print) -> bool:
    """Reproduce the five worked examples of Appendix A.

    Four invariants per prime:
        (i)   S(p) matches Appendix A
        (ii)  alpha(p) = p-1  (full-rank regime)
        (iii) signature = 'cm_only'  (Primitivity Lemma)
        (iv)  T(p) = S(p)  (since pi = p-1 in this regime)
    """
    log_fn("\n" + "=" * 70)
    log_fn(f" SELF-TEST: Appendix-A worked examples  (FibChar v{__version__})")
    log_fn("=" * 70)
    log_fn(f" {'p':>4}  {'S(p)':>5}  {'exp':>4}  {'alpha':>6}  "
           f"{'T(p)':>5}  {'pi':>6}  {'signature':<10}  status")
    log_fn(" " + "-" * 68)

    all_ok = True
    for p_val, expected in sorted(_SELF_TEST_CASES.items()):
        rec = analyze_prime(p_val)
        ok_S   = rec["S_p"]       == expected
        ok_rnk = rec["alpha"]     == p_val - 1
        ok_sig = rec["signature"] == "cm_only"
        ok_T   = rec["T_alpha"]   == rec["S_p"]
        ok = ok_S and ok_rnk and ok_sig and ok_T
        all_ok = all_ok and ok

        status = "OK" if ok else "*** FAIL ***"
        log_fn(f"  {p_val:>4}  {rec['S_p']:+5d}  {expected:+4d}  "
               f"{rec['alpha']:>6}  {rec['T_alpha']:+5d}  {rec['pisano']:>6}  "
               f"{rec['signature']:<10}  {status}")
        if not ok:
            if not ok_S:
                log_fn(f"      [!] S(p) mismatch: got {rec['S_p']}, expected {expected}")
            if not ok_rnk:
                log_fn(f"      [!] alpha != p-1: got {rec['alpha']}, expected {p_val-1}")
            if not ok_sig:
                log_fn(f"      [!] signature != cm_only: got {rec['signature']}")
            if not ok_T:
                log_fn(f"      [!] T(p) != S(p): T={rec['T_alpha']}, S={rec['S_p']}")

    log_fn("")
    if all_ok:
        log_fn("[OK] Self-test PASSED -- all 5 examples x 4 invariants verified.")
    else:
        log_fn("[FAIL] Self-test FAILED.  See diagnostics above.")
    sys.stdout.flush()
    return all_ok


# ============================================================================
# SECTION 5.  Corollary B1 / Main Theorem verification
# ============================================================================

def verify_corollary_b1(df: pd.DataFrame,
                        log_fn=print) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Machine-verify the Main Theorem via four sequential guards."""
    required = {"p", "alpha", "signature", "mod20", "T_alpha", "S_p"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"verify_corollary_b1: missing columns {sorted(missing)}")

    log_fn("\n" + "=" * 70)
    log_fn(" COROLLARY B1 / MAIN THEOREM VERIFICATION")
    log_fn("=" * 70)

    mask_full = df["alpha"] == (df["p"] - 1)
    cand = df[mask_full].copy()
    log_fn(f"\n  Primes with alpha(p) = p-1 : {len(cand):,}")
    log_fn(f"  of which signature=cm_only : {int((cand['signature'] == 'cm_only').sum()):,}")

    # Guard 1: Primitivity Lemma
    non_cm = cand[cand["signature"] != "cm_only"]
    if len(non_cm) > 0:
        log_fn(f"\n[!] GUARD 1 VIOLATED: {len(non_cm)} prime(s) with "
               f"alpha=p-1 but signature != cm_only")
        log_fn(non_cm[["p", "mod20", "signature", "alpha"]].head(20).to_string(index=False))
    else:
        log_fn("\n[OK] Guard 1 (Primitivity Lemma): all full-rank primes "
               "have signature 'cm_only'.")

    cm = cand[cand["signature"] == "cm_only"].copy()

    # Guard 2: Main Theorem congruence
    pred_map = {11: 1, 19: -1}
    cm["_predicted"] = cm["mod20"].map(pred_map)
    out_of_range = cm[cm["_predicted"].isna()]
    if len(out_of_range) > 0:
        log_fn(f"\n[!] GUARD 2 VIOLATED: {len(out_of_range)} cm_only prime(s) "
               f"with alpha=p-1 have p mod 20 not in {{11,19}}")
        log_fn(out_of_range[["p", "mod20", "alpha", "T_alpha"]].head(20).to_string(index=False))
    else:
        log_fn("[OK] Guard 2 (Main Theorem congruence): all such primes "
               "satisfy p == 11 or 19 (mod 20).")

    cm = cm[cm["_predicted"].notna()].copy()

    # Guard 3: hot-loop self-consistency (T_alpha == S_p)
    inconsistent = cm[cm["T_alpha"] != cm["S_p"]]
    if len(inconsistent) > 0:
        log_fn(f"\n[!!! CRITICAL] {len(inconsistent)} full-rank prime(s) "
               f"have T_alpha != S_p (indicates a BUG in core_walk).")
        log_fn(inconsistent[["p", "alpha", "pisano", "T_alpha", "S_p"]]
               .head(10).to_string(index=False))
        return (
            pd.DataFrame([{
                "p_mod_20": -1, "predicted_Sp": 0,
                "count": len(inconsistent), "matches": 0,
                "mismatches": len(inconsistent),
                "verdict": "CRITICAL_BUG_T_alpha_neq_S_p",
            }]),
            inconsistent.drop(columns=["_predicted"], errors="ignore"),
        )
    log_fn(f"[OK] Guard 3 (hot-loop self-consistency): T_alpha == S_p for "
           f"all {len(cm):,} full-rank primes.")

    # Guard 4: the Main Theorem
    cm["_matches"] = cm["T_alpha"] == cm["_predicted"]
    rows = []
    for m in (11, 19):
        sub = cm[cm["mod20"] == m]
        n_sub = len(sub)
        n_match = int(sub["_matches"].sum())
        rows.append({
            "p_mod_20"    : m,
            "predicted_Sp": int(pred_map[m]),
            "count"       : n_sub,
            "matches"     : n_match,
            "mismatches"  : n_sub - n_match,
            "verdict"     : "PASS" if n_match == n_sub else "FAIL",
        })
    summary_df = pd.DataFrame(rows)

    log_fn("\n  Verification table:")
    log_fn(summary_df.to_string(index=False))

    failures_df = cm[~cm["_matches"]].drop(
        columns=["_predicted", "_matches"], errors="ignore"
    ).copy()

    if len(failures_df) > 0:
        log_fn(f"\n[FAIL] {len(failures_df)} counterexamples to Main Theorem:")
        log_fn(failures_df[["p", "mod20", "alpha", "T_alpha", "S_p"]]
               .head(30).to_string(index=False))
    else:
        log_fn(f"\n[OK] Guard 4 (Main Theorem): verified for all "
               f"{len(cm):,} candidate prime(s). No counterexamples.")

    return summary_df, failures_df


# ============================================================================
# SECTION 6.  Verification of empirical claims E1..E10
# ============================================================================

def verify_all_empirical_claims(df: pd.DataFrame, log_fn=print) -> pd.DataFrame:
    """Verify claims E1..E10."""
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

    # ---- E1: v_2(pi) = v_2(p+1) + 1  on DI  ----
    # FIXED: define DI here; remove stray v2_array line from v7.0
    DI = main[main["signature"] == "DI"].copy()
    if len(DI):
        DI["_pred"] = DI["p"].apply(lambda pp: v2(int(pp) + 1)) + 1
        viol = int((DI["v2_pisano"] != DI["_pred"]).sum())
        record("E1 : v_2(pi) = v_2(p+1) + 1  on DI",
               viol == 0, len(DI), viol)
    else:
        record("E1 : v_2(pi) = v_2(p+1) + 1  on DI", True, 0)

    # ---- E2: pi = 4 alpha AND alpha odd  on Z \ DI ----
    Z = main["is_Z"]
    DI_mask = main["signature"] == "DI"
    ZmD = main[Z & ~DI_mask].copy()
    if len(ZmD):
        cond = (ZmD["pisano"] == 4 * ZmD["alpha"]) & (ZmD["alpha"] % 2 == 1)
        viol = int((~cond).sum())
        record("E2 : pi = 4*alpha AND alpha odd  on Z \\ DI",
               viol == 0, len(ZmD), viol)
    else:
        record("E2 : pi = 4*alpha AND alpha odd  on Z \\ DI", True, 0)

    # ---- E3: pi = alpha  on cm_only ----
    cm = main[main["signature"] == "cm_only"]
    if len(cm):
        viol = int((cm["pisano"] != cm["alpha"]).sum())
        record("E3 : pi = alpha  on cm_only", viol == 0, len(cm), viol)
    else:
        record("E3 : pi = alpha  on cm_only", True, 0)

    # ---- E4: alpha | (p+1)  for inert primes ----
    inert = main[main["signature"].isin(["DI", "fib_only"])]
    if len(inert):
        viol = int(((inert["p"] + 1) % inert["alpha"] != 0).sum())
        record("E4 : alpha | (p+1)  for inert primes", viol == 0, len(inert), viol)
    else:
        record("E4 : alpha | (p+1)  for inert primes", True, 0)

    # ---- E5: alpha | (p-1)  for split primes ----
    split = main[main["signature"].isin(["cm_only", "neither"])]
    if len(split):
        viol = int(((split["p"] - 1) % split["alpha"] != 0).sum())
        record("E5 : alpha | (p-1)  for split primes", viol == 0, len(split), viol)
    else:
        record("E5 : alpha | (p-1)  for split primes", True, 0)

    # ---- E6 + E7: parity of k ----
    main_k = main.copy()
    is_inert = main_k["signature"].isin(["DI", "fib_only"])
    main_k["_k"] = np.where(
        is_inert,
        (main_k["p"] + 1) // main_k["alpha"],
        (main_k["p"] - 1) // main_k["alpha"],
    )
    sub6 = main_k[main_k["chi_minus1"] == -1]
    viol6 = int((sub6["_k"] % 2 != 1).sum())
    record("E6 : chi_p(-1) = -1  ==>  k is odd", viol6 == 0, len(sub6), viol6)

    sub7 = main_k[main_k["chi_minus1"] == 1]
    viol7 = int((sub7["_k"] % 2 != 0).sum())
    record("E7 : chi_p(-1) = +1  ==>  k is even", viol7 == 0, len(sub7), viol7)

    # ---- E8: Main Theorem ----
    cm_full = main[(main["signature"] == "cm_only") &
                   (main["alpha"] == main["p"] - 1)].copy()
    if len(cm_full):
        cm_full["_pred"] = cm_full["mod5"].map({1: 1, 4: -1})
        oob = int(cm_full["_pred"].isna().sum())
        if oob > 0:
            record("E8 : full-rank cm_only => p in {1,4} (mod 5)",
                   False, len(cm_full), oob,
                   info=f"{oob} primes outside p mod 5 in {{1,4}}")
        valid = cm_full[cm_full["_pred"].notna()]
        viol8 = int((valid["S_p"] != valid["_pred"]).sum())
        record("E8 : S(p)=+1 if p==1 mod5, -1 if p==4 mod5  [MAIN THEOREM]",
               viol8 == 0, len(valid), viol8)
    else:
        record("E8 : MAIN THEOREM (no full-rank primes in sample)", True, 0,
               info="sample too small")

    # ---- E9: |S_p| odd on cm_only with k=3 ----
    cm_k3 = main[(main["signature"] == "cm_only") &
                 ((main["p"] - 1) // main["alpha"] == 3)]
    if len(cm_k3):
        viol9 = int((cm_k3["abs_S"] % 2 != 1).sum())
        record("E9 : |S_p| is odd  on cm_only with k=3",
               viol9 == 0, len(cm_k3), viol9)
    else:
        record("E9 : |S_p| is odd  on cm_only with k=3", True, 0)

    # ---- E10: 8 | S_p on fib_only with k=2 ----
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
        log_fn("[!] Some claims failed. Investigate before submission.")
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
                    last_index: int, total_primes: int, elapsed: float) -> None:
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
            try: os.remove(tmp_pq)
            except OSError: pass
        tmp_csv = csv_path + ".tmp"
        df_ckpt.to_csv(tmp_csv, index=False)
        os.replace(tmp_csv, csv_path)
        saved_data = csv_path

    meta = {"N_max": int(N_max), "last_index": int(last_index),
            "total_primes": int(total_primes), "elapsed_sec": float(elapsed),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "saved_data": saved_data, "version": __version__}
    tmp_meta = meta_path + ".tmp"
    with open(tmp_meta, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    os.replace(tmp_meta, meta_path)


def load_checkpoint(out_dir: str, N_max: int):
    pq_path, csv_path, meta_path = _ckpt_paths(out_dir, N_max)
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    if os.path.exists(pq_path):
        try: return pd.read_parquet(pq_path), meta
        except Exception: pass
    if os.path.exists(csv_path):
        try: return pd.read_csv(csv_path), meta
        except Exception: pass
    return None


def delete_checkpoint(out_dir: str, N_max: int) -> None:
    for path in _ckpt_paths(out_dir, N_max):
        if os.path.exists(path):
            try: os.remove(path)
            except OSError: pass


# ============================================================================
# SECTION 8.  Sequential database builder
# ============================================================================

_COLUMN_DTYPES: dict[str, type] = {
    "p": np.int64, "mod4": np.int8, "mod5": np.int8, "mod8": np.int8,
    "mod20": np.int8, "chi_minus1": np.int8, "chi_5": np.int8,
    "signature": object, "pisano": np.int64, "v2_pisano": np.int8,
    "alpha": np.int64, "pi_over_alpha": np.int32, "s": np.int64,
    "chi_s": np.int8, "T_alpha": np.int64, "S_p": np.int64,
    "abs_S": np.int64, "plus": np.int64, "minus": np.int64,
    "zeros": np.int64, "density_plus": np.float64, "is_Z": bool,
}


def build_database(N_max: int, out_dir: str, log_fn=print,
                   progress_fn=lambda x: None,
                   th_array: int = TH_ARRAY_DEFAULT,
                   th_bitwise: int = TH_BITWISE_DEFAULT,
                   resume_df=None, resume_meta=None,
                   stop_event=None):
    primes = sieve_primes(N_max)
    n_total = int(len(primes))

    log_fn(f"[+] FibChar v{__version__}  (author: {__author__})")
    log_fn(f"[+] backend       : {'Numba JIT' if HAS_NUMBA else 'pure Python (slow)'}")
    log_fn(f"[+] primes <= {N_max:,} : {n_total:,}")
    log_fn(f"[+] thresholds    : array<{th_array:,}  bitwise<{th_bitwise:,}  pow>=")

    if HAS_NUMBA:
        log_fn("[+] warming JIT ...")
        t_jit = time.perf_counter()
        _warmup_jit()
        log_fn(f"[+] JIT warm-up done ({time.perf_counter()-t_jit:.2f}s)")

    cols = {k: np.empty(n_total, dtype=dt) for k, dt in _COLUMN_DTYPES.items()}
    start_idx, elapsed_prev = 0, 0.0

    if resume_df is not None and resume_meta is not None:
        start_idx = int(resume_meta.get("last_index", 0))
        elapsed_prev = float(resume_meta.get("elapsed_sec", 0.0))
        for k in cols:
            if k in resume_df.columns:
                src = resume_df[k].values[:start_idx]
                if len(src) == start_idx:
                    cols[k][:start_idx] = src
        log_fn(f"[+] RESUMING from index {start_idx:,} "
               f"({100*start_idx/max(n_total,1):.1f}% done)")
        progress_fn(start_idx / max(n_total, 1))

    t0 = time.perf_counter()
    next_log_at = start_idx + LOG_INTERVAL
    next_ckpt_at = start_idx + CHECKPOINT_EVERY
    _sl = signature_label; _v2 = v2; _cw = _core_walk; _C = cols

    for i in range(start_idx, n_total):
        if stop_event is not None and stop_event.is_set():
            elapsed_now = elapsed_prev + (time.perf_counter() - t0)
            log_fn(f"[!] STOP at index {i:,}. Saving checkpoint ...")
            partial = {k: _C[k][:i].tolist() for k in COLUMNS}
            save_checkpoint(out_dir, N_max, partial, i, n_total, elapsed_now)
            log_fn(f"[+] Checkpoint saved.")
            return None

        p = int(primes[i])
        c1, c5, sig = _sl(p)
        (period, S, plus, minus, zeros,
         alpha, s_val, chi_s, T_alpha) = _cw(p, th_array, th_bitwise)

        if period == _WALK_SENTINEL:
            raise RuntimeError(f"hot loop exceeded LIMIT for p={p}.")

        period_i = int(period); alpha_i = int(alpha)
        plus_i = int(plus); minus_i = int(minus); pm = plus_i + minus_i

        _C["p"][i]             = p
        _C["mod4"][i]          = p % 4
        _C["mod5"][i]          = p % 5
        _C["mod8"][i]          = p % 8
        _C["mod20"][i]         = p % 20
        _C["chi_minus1"][i]    = c1
        _C["chi_5"][i]         = c5
        _C["signature"][i]     = sig
        _C["pisano"][i]        = period_i
        _C["v2_pisano"][i]     = _v2(period_i)
        _C["alpha"][i]         = alpha_i
        _C["pi_over_alpha"][i] = (period_i // alpha_i) if alpha_i > 0 else -1
        _C["s"][i]             = int(s_val)
        _C["chi_s"][i]         = int(chi_s)
        _C["T_alpha"][i]       = int(T_alpha)
        _C["S_p"][i]           = int(S)
        _C["abs_S"][i]         = abs(int(S))
        _C["plus"][i]          = plus_i
        _C["minus"][i]         = minus_i
        _C["zeros"][i]         = int(zeros)
        _C["density_plus"][i]  = float(plus_i) / pm if pm > 0 else float("nan")
        _C["is_Z"][i]          = (S == 0)

        done = i + 1
        if done >= next_log_at or done == n_total:
            dt = time.perf_counter() - t0
            elapsed_now = elapsed_prev + dt
            rate = (done - start_idx) / max(dt, 1e-9)
            eta = (n_total - done) / max(rate, 1e-9)
            log_fn(f"    {done:8,}/{n_total:,}  p={p:10,}  "
                   f"rate={rate:8,.0f}/s  ETA={eta:6.0f}s  total={elapsed_now:.0f}s")
            next_log_at = done + LOG_INTERVAL

        if done >= next_ckpt_at and done < n_total:
            elapsed_now = elapsed_prev + (time.perf_counter() - t0)
            partial = {k: _C[k][:done].tolist() for k in COLUMNS}
            save_checkpoint(out_dir, N_max, partial, done, n_total, elapsed_now)
            log_fn(f"    [ckpt] saved at index {done:,}")
            next_ckpt_at = done + CHECKPOINT_EVERY

        progress_fn(done / n_total)

    df = pd.DataFrame({k: cols[k] for k in COLUMNS})
    elapsed_now = elapsed_prev + (time.perf_counter() - t0)
    log_fn(f"[+] Compute finished (session {time.perf_counter()-t0:.1f}s, "
           f"total {elapsed_now:.1f}s, {len(df):,} rows)")
    return df


# ============================================================================
# SECTION 9.  Parallel database builder
# ============================================================================

def _parallel_worker_init() -> None:
    if HAS_NUMBA:
        _warmup_jit()


def _analyze_chunk(args: tuple) -> list[dict]:
    chunk, th_a, th_b = args
    return [analyze_prime(int(p), th_a, th_b) for p in chunk]


def build_database_parallel(primes: np.ndarray, workers: int, chunk_size: int,
                            th_array: int, th_bitwise: int,
                            log_fn=print) -> pd.DataFrame:
    chunks = [primes[i:i+chunk_size] for i in range(0, len(primes), chunk_size)]
    n_chunks = len(chunks)
    results: list[list[dict]] = [[] for _ in range(n_chunks)]
    n_errors = 0

    with ProcessPoolExecutor(max_workers=workers,
                             initializer=_parallel_worker_init) as executor:
        future_to_idx = {
            executor.submit(_analyze_chunk, (c, th_array, th_bitwise)): idx
            for idx, c in enumerate(chunks)
        }
        completed = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                n_errors += 1
                msg = f"chunk {idx} failed: {exc!r}"
                log_fn(f"[!] {msg}")
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
            completed += 1
            step = max(n_chunks // 20, 1)
            if completed % step == 0 or completed == n_chunks:
                log_fn(f"    chunks done: {completed}/{n_chunks}")

    if n_errors > 0:
        log_fn(f"[!] {n_errors} chunk(s) failed.")

    flat = [rec for cr in results for rec in cr]
    df = pd.DataFrame(flat)
    if len(df):
        df = df.sort_values("p").reset_index(drop=True)
    return df


# ============================================================================
# SECTION 10.  Diagnostic tables (Tables 1..15)
# ============================================================================

def compute_all_tables(df: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    main = df[~df["p"].isin([2, 5])].copy()
    n = len(main)
    if n == 0:
        return tables, main

    Z   = main["is_Z"]
    DI  = main["signature"] == "DI"
    ZmD = Z & ~DI
    ZaD = Z & DI

    # Table 00: headline
    tables["00_headline"] = pd.DataFrame([
        {"quantity": "delta(Z)",          "value": float(Z.mean()),
         "count": int(Z.sum()), "total": n},
        {"quantity": "delta(DI)",         "value": float(DI.mean()),
         "count": int(DI.sum()), "total": n},
        {"quantity": "delta(Z and DI)",   "value": float(ZaD.mean()),
         "count": int(ZaD.sum()), "total": n},
        {"quantity": "delta(Z minus DI)", "value": float(ZmD.mean()),
         "count": int(ZmD.sum()), "total": n},
        {"quantity": "P(Z | DI)",
         "value": float(ZaD.sum() / max(DI.sum(), 1)),
         "count": int(ZaD.sum()), "total": int(DI.sum())},
    ])

    # Table 01: signature counts
    SIGS = ["DI", "fib_only", "cm_only", "neither"]
    sg = main["signature"].value_counts()
    tables["01_signature_counts"] = pd.DataFrame([
        {"signature": s, "count": int(sg.get(s, 0)), "fraction": sg.get(s, 0) / n}
        for s in SIGS])

    # Table 02: P(Z | signature)
    tables["02_P_Z_given_signature"] = pd.DataFrame([
        {"signature": s, "n_sig": len(main[main["signature"] == s]),
         "n_Z": int(main[main["signature"] == s]["is_Z"].sum()),
         "P_Z_given_sig": float(main[main["signature"] == s]["is_Z"].mean())
                           if len(main[main["signature"] == s]) else float("nan")}
        for s in SIGS])

    # Table 03: S_p stats per signature
    tables["03_Sp_stats_by_signature"] = pd.DataFrame([
        {"signature": s,
         "mean_S_p": float(main[main["signature"]==s]["S_p"].mean()),
         "std_S_p":  float(main[main["signature"]==s]["S_p"].std()),
         "mean_absS":float(main[main["signature"]==s]["abs_S"].mean()),
         "max_absS": int(main[main["signature"]==s]["abs_S"].max())}
        for s in SIGS if len(main[main["signature"]==s])])

    # Table 04: v2(pi) per class
    classes = {"all": main, "Z": main[Z], "DI": main[DI],
               "Z_minus_DI": main[ZmD], "Z_and_DI": main[ZaD]}
    tables["04_v2_per_class"] = pd.DataFrame([
        {"class": k, "n": len(v), "mean_v2": float(v["v2_pisano"].mean()),
         "median_v2": int(v["v2_pisano"].median()),
         "min_v2": int(v["v2_pisano"].min()), "max_v2": int(v["v2_pisano"].max())}
        if len(v) else
        {"class": k, "n": 0, "mean_v2": float("nan"), "median_v2": -1, "min_v2": -1, "max_v2": -1}
        for k, v in classes.items()])

    # Table 04b: full v2 distribution
    v2_vals = sorted(int(x) for x in main["v2_pisano"].unique())
    all_d = main["v2_pisano"].value_counts(normalize=True)
    Z_d   = main[Z]["v2_pisano"].value_counts(normalize=True)
    ZmD_d = (main[ZmD]["v2_pisano"].value_counts(normalize=True)
             if ZmD.sum() else pd.Series(dtype=float))
    DI_d  = main[DI]["v2_pisano"].value_counts(normalize=True)
    tables["04b_v2_distribution"] = pd.DataFrame([
        {"v2": k, "freq_all": float(all_d.get(k,0)), "freq_Z": float(Z_d.get(k,0)),
         "freq_ZminusDI": float(ZmD_d.get(k,0)), "freq_DI": float(DI_d.get(k,0))}
        for k in v2_vals])

    # Tables 05-06: P(Z | mod)
    for col, tname in [("mod20","05_mod20_distribution"), ("mod8","06_mod8_distribution")]:
        tables[tname] = pd.DataFrame([
            {col: int(m), "count": len(main[main[col]==m]),
             "fraction": len(main[main[col]==m])/n,
             "n_Z": int(main[main[col]==m]["is_Z"].sum()),
             "P_Z_given_mod": float(main[main[col]==m]["is_Z"].mean())
                               if len(main[main[col]==m]) else float("nan")}
            for m in sorted(main[col].unique())])

    # Table 07: 2-adic tower
    rows = []
    for k in v2_vals:
        sub = main[main["v2_pisano"] == k]
        row: dict[str, Any] = {"k": k, "n_k": len(sub),
            "n_Z": int(sub["is_Z"].sum()),
            "P_Z_given_k": float(sub["is_Z"].mean()) if len(sub) else float("nan")}
        for m in (1, 3, 5, 7):
            ss = sub[sub["mod8"] == m]
            row[f"P_Z_k_mod8_{m}"] = float(ss["is_Z"].mean()) if len(ss) else float("nan")
            row[f"n_k_mod8_{m}"] = len(ss)
        rows.append(row)
    tables["07_2adic_tower"] = pd.DataFrame(rows)

    # Table 08: cross-table v2 x signature x is_Z
    rows = []
    for sig in SIGS:
        sub_sig = main[main["signature"] == sig]
        for k in sorted(sub_sig["v2_pisano"].unique()):
            ss = sub_sig[sub_sig["v2_pisano"] == k]
            rows.append({"signature": sig, "v2_pisano": int(k), "n": len(ss),
                         "n_Z": int(ss["is_Z"].sum()), "n_not_Z": int((~ss["is_Z"]).sum()),
                         "P_Z": float(ss["is_Z"].mean()) if len(ss) else float("nan")})
    tables["08_v2_signature_isZ"] = pd.DataFrame(rows)

    # Table 08b: DI by (mod8, v2)
    DI_df = main[DI]
    rows = []
    for m in sorted(DI_df["mod8"].unique()):
        for k in sorted(DI_df[DI_df["mod8"]==m]["v2_pisano"].unique()):
            ss = DI_df[(DI_df["mod8"]==m) & (DI_df["v2_pisano"]==k)]
            rows.append({"mod8": int(m), "v2_pisano": int(k),
                         "count": len(ss), "all_in_Z": bool(ss["is_Z"].all())})
    tables["08b_DI_mod8_v2_split"] = pd.DataFrame(rows)

    # Table 09: near-cancellation
    not_Z_df = main[~Z]
    if len(not_Z_df):
        tables["09_near_cancellation"] = pd.DataFrame([
            {"threshold": t, "count_below": int((not_Z_df["abs_S"]<=t).sum()),
             "fraction_of_nonZ": float((not_Z_df["abs_S"]<=t).mean())}
            for t in (1, 2, 4, 8, 16, 32, 64)])

    # Tables 10-12: Z \ DI
    ZmD_df = main[ZmD]
    if len(ZmD_df):
        d = ZmD_df["mod8"].value_counts().sort_index()
        tables["10_ZminusDI_mod8"] = pd.DataFrame(
            {"mod8": d.index.astype(int), "count": d.values})
        d = ZmD_df["pi_over_alpha"].value_counts().sort_index()
        tables["11_ZminusDI_pi_over_alpha"] = pd.DataFrame(
            {"pi_over_alpha": d.index.astype(int), "count": d.values})
        tables["12_ZminusDI_mod1_exceptions"] = ZmD_df[ZmD_df["mod8"]==1][
            ["p","pisano","alpha","pi_over_alpha","mod8","s","chi_s","T_alpha","S_p","signature"]
        ].copy()

    # Table 13: T_alpha stats
    cand_13 = main[(main["v2_pisano"]==2) & (main["mod8"]==1)]
    if len(cand_13):
        Ta = cand_13["T_alpha"].astype(float)
        av = cand_13["alpha"].astype(float)
        tables["13_T_alpha_stats_mod1_v2eq2"] = pd.DataFrame([{
            "n": len(cand_13), "mean_T_alpha": float(Ta.mean()),
            "std_T_alpha": float(Ta.std()), "min_T_alpha": int(Ta.min()),
            "median_T_alpha": float(Ta.median()), "max_T_alpha": int(Ta.max()),
            "n_T_alpha_eq_0": int((Ta==0).sum()),
            "rw_expected": float((1.0/np.sqrt(av)).sum()),
        }])

    # Table 14: Z density decomposition
    cond_auto = (main["v2_pisano"]==2) & (main["mod8"]==5) & Z
    cond_rare = (main["v2_pisano"]==2) & (main["mod8"]==1) & Z
    tables["14_Z_density_decomposition"] = pd.DataFrame([
        {"component": "DI", "delta": float(DI.mean()), "count": int(DI.sum())},
        {"component": "Z and (v2=2, p=5 mod 8) [auto-cancellation]",
         "delta": float(cond_auto.mean()), "count": int(cond_auto.sum())},
        {"component": "Z and (v2=2, p=1 mod 8) [rare T_alpha=0]",
         "delta": float(cond_rare.mean()), "count": int(cond_rare.sum())},
        {"component": "TOTAL Z", "delta": float(Z.mean()), "count": int(Z.sum())},
    ])

    # Table 15: sanity checks (PROVABLE invariants only)
    sanity: list[tuple[str, bool, int]] = []
    sanity.append(("S1: P(Z|DI) = 1",
                   bool(ZaD.sum() == DI.sum()), int(DI.sum()-ZaD.sum())))
    if len(ZmD_df):
        sanity.append(("S2: pi/alpha = 4  for all p in Z \\ DI",
                       bool((ZmD_df["pi_over_alpha"]==4).all()),
                       int((ZmD_df["pi_over_alpha"]!=4).sum())))
        sanity.append(("S3: v2(pi) = 2  for all p in Z \\ DI",
                       bool((ZmD_df["v2_pisano"]==2).all()),
                       int((ZmD_df["v2_pisano"]!=2).sum())))
    sanity.append(("S4: v2(pi) >= 3  for all DI",
                   bool((main[DI]["v2_pisano"]>=3).all()),
                   int((main[DI]["v2_pisano"]<3).sum())))
    sub_DI_3 = main[DI & (main["mod8"]==3)]
    sanity.append(("S5: DI and p==3 mod 8  => v2(pi) = 3",
                   bool((sub_DI_3["v2_pisano"]==3).all()) if len(sub_DI_3) else True,
                   int((sub_DI_3["v2_pisano"]!=3).sum()) if len(sub_DI_3) else 0))
    sub_DI_7 = main[DI & (main["mod8"]==7)]
    sanity.append(("S6: DI and p==7 mod 8  => v2(pi) >= 4",
                   bool((sub_DI_7["v2_pisano"]>=4).all()) if len(sub_DI_7) else True,
                   int((sub_DI_7["v2_pisano"]<4).sum()) if len(sub_DI_7) else 0))
    cm_b1 = main[(main["signature"]=="cm_only") & (main["alpha"]==main["p"]-1)]
    if len(cm_b1):
        bad_11 = int(((cm_b1["mod20"]==11) & (cm_b1["T_alpha"]!=1)).sum())
        bad_19 = int(((cm_b1["mod20"]==19) & (cm_b1["T_alpha"]!=-1)).sum())
        sanity.append(("S7: T_alpha = +1 for p==11 mod 20 (Cor B1)", bad_11==0, bad_11))
        sanity.append(("S8: T_alpha = -1 for p==19 mod 20 (Cor B1)", bad_19==0, bad_19))
    if len(ZmD_df):
        sample = ZmD_df.sample(min(500, len(ZmD_df)), random_state=42)
        s_arr = sample["s"].astype(object).values
        p_arr = sample["p"].astype(object).values
        bad_s = int(sum(1 for s, pp in zip(s_arr, p_arr)
                        if (int(s)*int(s))%int(pp) != int(pp)-1))
        sanity.append((f"S9: s^2 == -1 (mod p) on Z\\DI [n={len(sample)}]",
                       bad_s==0, bad_s))
    tables["15_sanity_checks"] = pd.DataFrame(
        sanity, columns=["invariant", "passes", "violations"])

    # Table 15b: empirical observations (not yet proved)
    cm_Z_count = int(main[main["signature"]=="cm_only"]["is_Z"].sum())
    tables["15b_empirical_observations"] = pd.DataFrame([{
        "observation": "O1: cm_only never in Z  (up to current N)",
        "holds": cm_Z_count == 0, "exceptions": cm_Z_count,
        "note": "empirical; not yet proved",
    }])

    return tables, main


# ============================================================================
# SECTION 11.  Report formatting
# ============================================================================

def format_report(tables: dict[str, pd.DataFrame],
                  n_total: int, n_main: int) -> str:
    W = 78
    lines: list[str] = [
        "=" * W,
        f" FibChar v{__version__}  --  UNIFIED DIAGNOSTIC REPORT",
        f" {__paper__}",
        "=" * W,
        f"\n  Total primes in df   : {n_total:,}",
        f"  Main set (p != 2,5)  : {n_main:,}",
    ]
    _TITLES = [
        ("00_headline",                   "[ HEADLINE DENSITIES ]"),
        ("01_signature_counts",           "[ TABLE  1 ] Signature counts"),
        ("02_P_Z_given_signature",        "[ TABLE  2 ] P(Z | signature)"),
        ("03_Sp_stats_by_signature",      "[ TABLE  3 ] S(p) statistics per signature"),
        ("04_v2_per_class",               "[ TABLE  4 ] v_2(pi) per class"),
        ("04b_v2_distribution",           "[ TABLE 4b ] Full distribution of v_2(pi)"),
        ("05_mod20_distribution",         "[ TABLE  5 ] P(Z | p mod 20)"),
        ("06_mod8_distribution",          "[ TABLE  6 ] P(Z | p mod 8)"),
        ("07_2adic_tower",                "[ TABLE  7 ] 2-adic tower  P(Z | v_2(pi)=k)"),
        ("08_v2_signature_isZ",           "[ TABLE  8 ] Cross-table: v_2 x signature x is_Z"),
        ("08b_DI_mod8_v2_split",          "[ TABLE 8b ] DI primes split by (mod 8, v_2)"),
        ("09_near_cancellation",          "[ TABLE  9 ] Near-cancellation in Z^c"),
        ("10_ZminusDI_mod8",              "[ TABLE 10 ] Z \\ DI  by p mod 8"),
        ("11_ZminusDI_pi_over_alpha",     "[ TABLE 11 ] Z \\ DI  pi/alpha distribution"),
        ("12_ZminusDI_mod1_exceptions",   "[ TABLE 12 ] Z \\ DI  exceptions (p=1 mod 8)"),
        ("13_T_alpha_stats_mod1_v2eq2",   "[ TABLE 13 ] T_alpha stats (p=1 mod 8, v_2=2)"),
        ("14_Z_density_decomposition",    "[ TABLE 14 ] delta(Z) decomposition"),
        ("15_sanity_checks",              "[ TABLE 15 ] SANITY CHECKS (provable; must PASS)"),
        ("15b_empirical_observations",    "[ TABLE 15b] EMPIRICAL OBSERVATIONS (not yet proved)"),
        ("16_corollary_B1_verification",  "[ TABLE 16 ] Corollary B1 / Main Theorem"),
        ("16b_corollary_B1_failures",     "[ TABLE 16b] Corollary B1 FAILURES (if any)"),
        ("17_empirical_claims_E1_to_E10", "[ TABLE 17 ] All empirical claims E1..E10"),
    ]
    for name, title in _TITLES:
        t = tables.get(name)
        if t is not None and len(t):
            lines.append("\n" + title)
            lines.append(t.to_string(index=False))

    hd = tables.get("00_headline")
    if hd is not None and len(hd):
        row = hd[hd["quantity"] == "delta(Z minus DI)"]
        if len(row):
            d = float(row["value"].iloc[0])
            verdict = ("ESSENTIALLY EMPTY" if d < 0.005 else
                       "THIN" if d < 0.020 else
                       "MARGINAL" if d < 0.050 else
                       "SUBSTANTIAL -- hidden structure beyond DI!")
            lines.append("\n[ GO / NO-GO VERDICT ]")
            lines.append(f"    delta(Z \\ DI) = {d:.6f}   >>>  {verdict}")

    lines.append("\n" + "=" * W)
    return "\n".join(lines)


# ============================================================================
# SECTION 12.  Output saving  (CSV / TXT / XLSX / LaTeX / JSON)
# ============================================================================

def save_outputs(df: pd.DataFrame, tables: dict[str, pd.DataFrame],
                 report_text: str, out_dir: str, N_max: int,
                 log_fn=print) -> None:
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
        log_fn(f"[!] XLSX save skipped ({exc}).")


def export_latex_tables(tables: dict[str, pd.DataFrame],
                        out_dir: str, log_fn=print) -> None:
    """Write each non-empty table as a booktabs-ready .tex file."""
    latex_dir = os.path.join(out_dir, "latex_tables")
    os.makedirs(latex_dir, exist_ok=True)
    n_written = 0
    for name, t in tables.items():
        if len(t) == 0:
            continue
        col_fmt = "".join(
            "r" if pd.api.types.is_numeric_dtype(t[c]) else "l"
            for c in t.columns)
        path = os.path.join(latex_dir, f"{name}.tex")
        try:
            styler = t.style.format(escape="latex")
            try:    styler = styler.hide(axis="index")
            except: styler = styler.hide_index()
            latex_str = styler.to_latex(column_format=col_fmt, hrules=True)
        except Exception:
            import warnings as _w
            with _w.catch_warnings():
                _w.simplefilter("ignore", FutureWarning)
                latex_str = t.to_latex(index=False, escape=True,
                                       column_format=col_fmt)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"% Auto-generated by FibChar v{__version__}\n")
            fh.write(f"% Table: {name}\n")
            fh.write(latex_str)
        n_written += 1
    log_fn(f"[+] LaTeX tables -> {latex_dir}/  ({n_written} files)")


def save_json_summary(tables: dict[str, pd.DataFrame],
                      df: pd.DataFrame,
                      N_max: int,
                      out_dir: str,
                      run_meta: dict[str, Any],
                      log_fn=print) -> str:
    """Save a compact JSON summary for CI / reproducibility pipelines.

    Covers: version, paper metadata, run parameters, headline densities,
    Corollary B1 outcome, empirical claims E1-E10, and sanity checks.
    """
    def _to_python(obj):
        """Recursively convert numpy scalars to native Python types."""
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, dict):
            return {k: _to_python(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_python(x) for x in obj]
        return obj

    summary: dict[str, Any] = {
        "fibchar_version": __version__,
        "paper"          : __paper__,
        "github"         : "https://github.com/Majid-Ghandali/fibonacci-character-sum-full-rank",
        "zenodo"         : "https://doi.org/10.5281/zenodo.20707467",
        "run_parameters" : _to_python(run_meta),
        "headline"       : {},
        "corollary_b1"   : {},
        "empirical_claims_E1_to_E10": [],
        "sanity_checks"  : [],
        "self_test"      : {},
    }

    # Headline
    hd = tables.get("00_headline")
    if hd is not None:
        for _, row in hd.iterrows():
            key = (str(row["quantity"])
                   .replace(" ", "_").replace("(", "").replace(")", "")
                   .replace("|", "given").replace("/", "_over_"))
            summary["headline"][key] = {
                "value": _to_python(row["value"]),
                "count": _to_python(row["count"]),
                "total": _to_python(row["total"]),
            }

    # Corollary B1
    b1 = tables.get("16_corollary_B1_verification")
    if b1 is not None:
        for _, row in b1.iterrows():
            key = f"p_mod_20_{_to_python(row.get('p_mod_20', -1))}"
            summary["corollary_b1"][key] = _to_python(row.to_dict())

    # Empirical claims
    ec = tables.get("17_empirical_claims_E1_to_E10")
    if ec is not None:
        summary["empirical_claims_E1_to_E10"] = _to_python(
            ec.to_dict(orient="records"))

    # Sanity checks
    sc = tables.get("15_sanity_checks")
    if sc is not None:
        summary["sanity_checks"] = _to_python(sc.to_dict(orient="records"))

    # Self-test quick results
    summary["self_test"] = {
        "primes_tested" : list(_SELF_TEST_CASES.keys()),
        "expected_S"    : _to_python(_SELF_TEST_CASES),
    }

    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"fib_char_N{N_max}_summary.json")
    tmp_path  = json_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False, default=str)
    os.replace(tmp_path, json_path)
    log_fn(f"[+] saved JSON  -> {json_path}")
    return json_path


# ============================================================================
# SECTION 13.  GUI  (optional; Tkinter required)
# ============================================================================

if _TKINTER_AVAILABLE:

    class FibCharApp(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.title(f"FibChar v{__version__}  --  {__author__}")
            self.geometry("1200x860")
            self._queue: queue.Queue = queue.Queue()
            self._worker = None
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
            self._run_btn = ttk.Button(top, text="▶ Run", command=self._on_run)
            self._run_btn.pack(side="left", padx=(12, 2))
            self._stop_btn = ttk.Button(top, text="■ Stop & Checkpoint",
                                        command=self._on_stop, state="disabled")
            self._stop_btn.pack(side="left", padx=2)
            ttk.Button(top, text="�� Self-test",
                       command=self._on_self_test).pack(side="left", padx=(12, 2))

            th = ttk.Frame(self, padding=(8,0,8,4)); th.pack(fill="x")
            ttk.Label(th, text="array <").pack(side="left")
            self._th_arr = tk.StringVar(value=str(TH_ARRAY_DEFAULT))
            ttk.Entry(th, textvariable=self._th_arr, width=12).pack(side="left")
            ttk.Label(th, text="  bitwise <").pack(side="left")
            self._th_bw = tk.StringVar(value=str(TH_BITWISE_DEFAULT))
            ttk.Entry(th, textvariable=self._th_bw, width=12).pack(side="left")
            ttk.Label(th, text="  pow ≥ (above)").pack(side="left")

            pr = ttk.Frame(self, padding=(8,0,8,4)); pr.pack(fill="x")
            self._prog = ttk.Progressbar(pr, length=200, mode="determinate", maximum=100)
            self._prog.pack(fill="x", side="left", expand=True)
            self._pct_lbl = ttk.Label(pr, text="  0.0%")
            self._pct_lbl.pack(side="left", padx=6)

            tb = ttk.Frame(self, padding=(8,0,8,2)); tb.pack(fill="x")
            ttk.Label(tb, text="Log / Report").pack(side="left")
            ttk.Button(tb, text="�� Copy all",       command=self._copy_all).pack(side="right", padx=2)
            ttk.Button(tb, text="�� Copy selection", command=self._copy_sel).pack(side="right", padx=2)
            ttk.Button(tb, text="�� Save .txt",      command=self._save_log_txt).pack(side="right", padx=2)
            ttk.Button(tb, text="Clear",
                       command=lambda: self._log_widget.delete("1.0","end")).pack(side="right", padx=2)

            body = ttk.Frame(self, padding=(8,0,8,4)); body.pack(fill="both", expand=True)
            self._log_widget = scrolledtext.ScrolledText(
                body, font=("Consolas",10), wrap="none", undo=False)
            self._log_widget.pack(fill="both", expand=True)
            self._log_widget.bind("<Control-a>",
                lambda e: (self._log_widget.tag_add("sel","1.0","end"), "break"))
            self._install_context_menu()

            bar = ttk.Frame(self, padding=(8,0,8,8)); bar.pack(fill="x")
            ttk.Label(bar, text=("Numba: ON ✓" if HAS_NUMBA else "Numba: OFF")).pack(side="left")
            ttk.Label(bar, text=f"  v{__version__}").pack(side="left")
            self._status_lbl = ttk.Label(bar, text="idle.")
            self._status_lbl.pack(side="right")

        def _install_context_menu(self) -> None:
            menu = tk.Menu(self._log_widget, tearoff=0)
            menu.add_command(label="Copy selection", command=self._copy_sel)
            menu.add_command(label="Copy all",       command=self._copy_all)
            menu.add_separator()
            menu.add_command(label="Select all",
                command=lambda: self._log_widget.tag_add("sel","1.0","end"))
            menu.add_command(label="Save as .txt...", command=self._save_log_txt)
            def _show(e):
                try: menu.tk_popup(e.x_root, e.y_root)
                finally: menu.grab_release()
            for seq in ("<Button-3>","<Button-2>","<Control-Button-1>"):
                self._log_widget.bind(seq, _show)

        def _append_log(self, msg: str) -> None:
            self._log_widget.insert("end", msg + "\n"); self._log_widget.see("end")
        def _log(self, msg: str) -> None: self._queue.put(("log", msg))
        def _set_progress(self, f: float) -> None: self._queue.put(("prog", f))

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
            except queue.Empty: pass
            self.after(100, self._poll_queue)

        def _copy_sel(self) -> None:
            try: text = self._log_widget.get("sel.first", "sel.last")
            except tk.TclError: self._status_lbl.configure(text="no selection."); return
            if text: self.clipboard_clear(); self.clipboard_append(text)
            self._status_lbl.configure(text="selection copied.")

        def _copy_all(self) -> None:
            text = self._log_widget.get("1.0","end-1c")
            self.clipboard_clear(); self.clipboard_append(text)
            self._status_lbl.configure(text=f"copied {len(text):,} chars.")

        def _save_log_txt(self) -> None:
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files","*.txt"),("All files","*.*")],
                initialfile="fib_char_log.txt")
            if not path: return
            with open(path,"w",encoding="utf-8") as fh:
                fh.write(self._log_widget.get("1.0","end-1c"))
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

        def _on_run(self) -> None:
            try:
                N = int(self._n_var.get()); assert N >= 10
                th_a = int(self._th_arr.get()); th_b = int(self._th_bw.get())
                assert 0 < th_a <= th_b
            except (ValueError, AssertionError):
                messagebox.showerror("Invalid input",
                    "N_MAX >= 10  and  0 < th_array <= th_bitwise.")
                return

            out_dir = self._dir_var.get().strip() or "FibChar_Output"
            resume_payload = None
            ckpt = load_checkpoint(out_dir, N)
            if ckpt is not None:
                cdf, meta = ckpt
                pct = 100 * meta["last_index"] / max(meta["total_primes"], 1)
                ans = messagebox.askyesnocancel(
                    "Checkpoint found",
                    f"Checkpoint for N_MAX={N:,}:\n"
                    f"  Progress : {meta['last_index']:,}/{meta['total_primes']:,} ({pct:.1f}%)\n"
                    f"  Saved at : {meta.get('timestamp','?')}\n\n"
                    "Yes = RESUME     No = FRESH     Cancel = abort")
                if ans is None: return
                if ans: resume_payload = (cdf, meta)
                else:   delete_checkpoint(out_dir, N)

            self._stop_event.clear()
            self._run_btn.configure(state="disabled")
            self._stop_btn.configure(state="normal")
            self._log_widget.delete("1.0","end")
            self._prog["value"] = 0; self._pct_lbl.configure(text="  0.0%")

            self._worker = threading.Thread(
                target=self._pipeline,
                args=(N, out_dir, resume_payload, th_a, th_b), daemon=True)
            self._worker.start()

        def _pipeline(self, N, out_dir, resume_payload, th_a, th_b) -> None:
            try:
                t_start = time.perf_counter()
                self._log(f"[+] FibChar v{__version__}  N_MAX={N:,}")
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
                    self._queue.put(("done","stopped (checkpoint saved).")); return

                self._log("[+] Computing tables ...")
                tables, _ = compute_all_tables(df)

                self._log("[+] Verifying E1..E10 ...")
                ec = verify_all_empirical_claims(df, log_fn=self._log)
                tables["17_empirical_claims_E1_to_E10"] = ec

                self._log("[+] Verifying Corollary B1 ...")
                b1, b1f = verify_corollary_b1(df, log_fn=self._log)
                tables["16_corollary_B1_verification"] = b1
                if len(b1f): tables["16b_corollary_B1_failures"] = b1f

                report = format_report(tables, len(df),
                                       len(df[~df["p"].isin([2,5])]))
                self._log("\n" + report)
                save_outputs(df, tables, report, out_dir, N, self._log)

                run_meta = {"N_max": N, "th_array": th_a, "th_bitwise": th_b,
                            "backend": "Numba JIT" if HAS_NUMBA else "pure Python",
                            "elapsed_sec": round(time.perf_counter()-t_start, 2),
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_json_summary(tables, df, N, out_dir, run_meta, self._log)

                b1_csv = os.path.join(out_dir, f"fib_char_N{N}_corollary_b1.csv")
                b1.to_csv(b1_csv, index=False)
                self._log(f"[+] saved Cor-B1 CSV -> {b1_csv}")
                ec_csv = os.path.join(out_dir, f"fib_char_N{N}_empirical_claims.csv")
                ec.to_csv(ec_csv, index=False)
                self._log(f"[+] saved empirical CSV -> {ec_csv}")

                export_latex_tables(tables, out_dir, log_fn=self._log)
                delete_checkpoint(out_dir, N)
                self._queue.put(("done","completed successfully."))
            except Exception as exc:
                import traceback
                self._log(f"\n[ERROR] {exc!r}\n{traceback.format_exc()}")
                self._queue.put(("done", f"ERROR: {exc!r}"))

else:
    FibCharApp = None


# ============================================================================
# SECTION 14.  CLI pipeline
# ============================================================================

def cli_pipeline(args: argparse.Namespace) -> int:
    def log(msg: str) -> None:
        print(msg, flush=True)

    # --- Self-test mode: instant exit ---
    if args.self_test:
        ok = run_self_test(log_fn=log)
        sys.stdout.flush()
        return 0 if ok else 1

    N       = args.N
    out_dir = args.out_dir
    th_a    = args.th_array
    th_b    = args.th_bitwise

    if not (0 < th_a <= th_b):
        log("[!] Require 0 < --th-array <= --th-bitwise.")
        return 1

    os.makedirs(out_dir, exist_ok=True)

    resume_df = resume_meta = None
    if args.resume:
        ckpt = load_checkpoint(out_dir, N)
        if ckpt:
            resume_df, resume_meta = ckpt
            pct = 100*resume_meta["last_index"]/max(resume_meta["total_primes"],1)
            log(f"[+] Resuming from checkpoint: {resume_meta['last_index']:,}/"
                f"{resume_meta['total_primes']:,} ({pct:.1f}%)")
        else:
            log("[!] --resume: no checkpoint found. Starting fresh.")
    elif not args.parallel:
        ckpt = load_checkpoint(out_dir, N)
        if ckpt:
            log("[!] Stale checkpoint found; deleting before fresh run.")
            delete_checkpoint(out_dir, N)

    t0 = time.perf_counter()

    if args.parallel:
        primes = sieve_primes(N)
        log(f"[+] Primes <= {N:,}: {len(primes):,}  "
            f"(parallel workers={args.workers}, chunk={args.chunk_size})")
        if HAS_NUMBA:
            log("[+] Warming JIT (main process) ..."); _warmup_jit()
        df = build_database_parallel(
            primes, workers=args.workers, chunk_size=args.chunk_size,
            th_array=th_a, th_bitwise=th_b, log_fn=log)
    else:
        df = build_database(
            N, out_dir=out_dir, log_fn=log, progress_fn=lambda x: None,
            th_array=th_a, th_bitwise=th_b,
            resume_df=resume_df, resume_meta=resume_meta, stop_event=None)
        if df is None:
            log("[!] Build returned None (stopped early)."); return 2

    elapsed = time.perf_counter() - t0
    log(f"[+] Total compute: {elapsed:.2f}s  ({len(df):,} rows)")

    log("[+] Computing tables ...")
    tables, _ = compute_all_tables(df)

    log("[+] Verifying E1..E10 ...")
    ec = verify_all_empirical_claims(df, log_fn=log)
    tables["17_empirical_claims_E1_to_E10"] = ec

    if args.verify_b1:
        b1, b1f = verify_corollary_b1(df, log_fn=log)
        tables["16_corollary_B1_verification"] = b1
        if len(b1f): tables["16b_corollary_B1_failures"] = b1f
        b1_csv = os.path.join(out_dir, f"fib_char_N{N}_corollary_b1.csv")
        b1.to_csv(b1_csv, index=False)
        log(f"[+] Cor-B1 CSV -> {b1_csv}")

    report = format_report(tables, len(df), len(df[~df["p"].isin([2,5])]))
    print(report, flush=True)

    save_outputs(df, tables, report, out_dir, N, log_fn=log)
    export_latex_tables(tables, out_dir, log_fn=log)

    ec_csv = os.path.join(out_dir, f"fib_char_N{N}_empirical_claims.csv")
    ec.to_csv(ec_csv, index=False)
    log(f"[+] Empirical claims CSV -> {ec_csv}")

    run_meta = {"N_max": N, "th_array": th_a, "th_bitwise": th_b,
                "parallel": args.parallel,
                "backend": "Numba JIT" if HAS_NUMBA else "pure Python",
                "elapsed_sec": round(elapsed, 2),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
    save_json_summary(tables, df, N, out_dir, run_meta, log_fn=log)

    if not args.parallel:
        delete_checkpoint(out_dir, N)

    log("[+] Done.")
    return 0


# ============================================================================
# SECTION 15.  Argument parser
# ============================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="FibChar_Suite_v5_JNT_Paper5.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"FibChar v{__version__}  --  {__paper__}",
        epilog="""
Examples
--------
  Reproduce the paper's N=10^6 run with full verification:
      %(prog)s --no-gui --N 1000000 --verify-b1

  Larger run (N=2*10^6), parallel:
      %(prog)s --no-gui --N 2000000 --verify-b1 --parallel --workers 8

  Quick self-test (~instant):
      %(prog)s --self-test

  Resume an interrupted run:
      %(prog)s --no-gui --N 2000000 --verify-b1 --resume

  Interactive GUI:
      %(prog)s
""")
    p.add_argument("--N", type=int, default=1_000_000, metavar="N_MAX")
    p.add_argument("--out-dir", default="FibChar_Output", metavar="DIR")
    p.add_argument("--no-gui",    action="store_true")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--verify-b1", action="store_true")
    p.add_argument("--resume",    action="store_true")
    p.add_argument("--parallel",  action="store_true")
    p.add_argument("--workers",   type=int, default=os.cpu_count()-2 or 4)
    p.add_argument("--chunk-size",type=int, default=5000, metavar="C")
    p.add_argument("--th-array",  type=int, default=TH_ARRAY_DEFAULT)
    p.add_argument("--th-bitwise",type=int, default=TH_BITWISE_DEFAULT)
    p.add_argument("--version",   action="version",
                   version=f"FibChar v{__version__}  ({__author__})")
    return p


# ============================================================================
# SECTION 16.  Main entry point
# ============================================================================

def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    use_gui = (_TKINTER_AVAILABLE and
               not args.no_gui and
               not args.self_test)
    if use_gui:
        app = FibCharApp()
        app.mainloop()
    else:
        sys.exit(cli_pipeline(args))


if __name__ == "__main__":
    main()

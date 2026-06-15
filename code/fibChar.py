

# fibChar.py

"""
================================================================================
 FibChar __version__ = "5.1"  # added empirical claims verification + critical sanity check
 v5.1  - added verify_all_empirical_claims (E1-E10)
      - added T_alpha == S_p sanity check in verify_corollary_B1
      - clarified S_p vs S(p) notation throughout
      - documented modpow overflow bound (safe for p < 2^31)
================================================================================

Companion reproducibility code for the paper:

    "A Fibonacci Character Sum Identity for Primes of Full Rank
     of Apparition"
    Majid Ghalandali -- submitted to the Journal of Number Theory (JNT)

--------------------------------------------------------------------------
WHAT THIS PROGRAM COMPUTES
--------------------------------------------------------------------------
For every odd prime p (p != 5, p < N_max) it computes, in a single pass
over the Fibonacci recursion mod p:

  * the quadratic-character signature of p w.r.t. -1 and 5
        chi_p(-1), chi_p(5)  ->  signature in {DI, fib_only, cm_only, neither}
  * the Pisano period  pi(p)  and its 2-adic valuation  v2(pi(p))
  * the rank of apparition  alpha(p) = least m > 0 with p | F_m
  * s = F_{alpha(p)+1} mod p   and   chi_p(s)
  * the partial character sum
        T_alpha(p) = sum_{n=1}^{alpha(p)} chi_p(F_n)
  * the full character sum (the central object of the paper)
        S(p) = sum_{n=1}^{p-1} chi_p(F_n)

and in particular machine-verifies the Main Theorem / Corollary B1:

    If alpha(p) = p-1, then p == 11 or 19 (mod 20), and

        S(p) = T_alpha(p) =  +1   if p == 11 (mod 20)
        S(p) = T_alpha(p) =  -1   if p == 19 (mod 20)

--------------------------------------------------------------------------
PROVENANCE OF THIS FILE
--------------------------------------------------------------------------
This script merges and supersedes the two earlier development files in the
project:

  (A) Fibonacci_Character_Sum_Identity_Primes_Full_Rank_Apparition.PY (v4)
        - full Tkinter GUI, checkpoint/resume, 3-backend hot loop,
          multiprocessing pipeline, LaTeX export
  (B) PAPER_5_FINAL_V1.PY
        - compact headless CLI, cleaner (vectorised) Corollary B1 routine

Everything that was numerically validated in (A)'s sample run
(N = 1,000,000 -> 78,498 primes, 13,943 with alpha(p)=p-1, both
Corollary-B1 sub-tables PASS, all 10 sanity checks PASS) is preserved
unchanged. On top of the union of (A) and (B) this edition adds:

  1. A merged, more rigorous `verify_corollary_B1` that combines (A)'s
     diagnostic guard-rails (flagging any non-'cm_only' or non-{11,19 mod
     20} prime with alpha(p)=p-1, which the Main Theorem says cannot
     occur) with (B)'s cleaner vectorised `pandas` implementation.
  2. A new `run_self_test()` that reproduces the five worked examples of
     Appendix A (S(11)=+1, S(19)=-1, S(31)=+1, S(59)=-1, S(79)=-1) as an
     independent, instant sanity check -- useful for referees / CI.
  3. A robust optional Tkinter import, so the SAME file runs headlessly
     (`--no-gui`) on machines/containers without a display or Tk, which
     is the realistic situation for a reproducibility archive / CI runner.
  4. The multiprocessing pipeline from (A) is wired into the CLI
     (`--parallel --workers N --chunk-size K`) as an additional speed
     option (NOTE: this path has no checkpoint/resume -- see remarks at
     the bottom of this header).
  5. Tidied docstrings, a `__version__` string, and an `argparse` epilog
     with ready-to-run example commands for the N = 2*10^6 run reported in
     the paper.

--------------------------------------------------------------------------
DEPENDENCIES
--------------------------------------------------------------------------
    numpy, pandas      (required)
    numba              (optional but strongly recommended; ~50-100x speed-up.
                        Falls back transparently to pure Python if absent.)
    openpyxl           (optional; only needed for the .xlsx report)
    tkinter            (optional; only needed for the GUI)

--------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------
    # Reproduce the paper's N = 10^6 run headlessly, with full diagnostics
    # and Corollary B1 verification (the run that produced Tables 1-16):
    python FibChar_Suite_v5_JNT_Paper5.py --no-gui --N 2000000 --verify-b1

    # Quick self-test of the five Appendix-A examples (instant):
    python FibChar_Suite_v5_JNT_Paper5.py --self-test

    # Same N = 10^6 run, but multi-process for speed (no checkpointing):
    python FibChar_Suite_v5_JNT_Paper5.py --no-gui --N 1000000 --verify-b1 \\
           --parallel --workers 8 --chunk-size 200

    # Interactive GUI (checkpoint/resume, live log, progress bar):
    python FibChar_Suite_v5_JNT_Paper5.py

--------------------------------------------------------------------------
IMPORTANT REPRODUCIBILITY REMARKS (please read before archiving)
--------------------------------------------------------------------------
  * Checkpoint/resume (`--resume` / `--fresh`) is implemented ONLY for the
    sequential pipeline (default, no `--parallel`). The `--parallel`
    pipeline runs start-to-finish in one shot; for N = 2*10^6 this is fast
    enough on a modern multi-core machine that checkpointing is usually
    unnecessary.
  * Backend thresholds `--th-array` / `--th-bitwise` trade memory for
    speed (QR lookup table -> O(p) memory but fastest; bitwise Jacobi ->
    O(1) memory; Euler criterion via modpow -> O(1) memory, most frugal).
    The defaults (1e6 / 1e7) were used for the reported N = 2*10^6 run and
    keep peak memory under ~1 MB per prime.
  * Numba's JIT cache (`cache=True`) writes `__pycache__` artifacts on
    first run; on a fresh machine the first call to `--N` will include a
    one-off compilation cost (a few seconds), which the "warming JIT"
    step performs explicitly so it does not pollute timing logs.
================================================================================
"""

import os
import json
import time
import threading
import queue
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------
# Optional Numba JIT acceleration (falls back to pure Python transparently)
# ------------------------------------------------------------------------
try:
    from numba import njit
    HAS_NUMBA = True
except Exception:
    HAS_NUMBA = False

    def njit(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return lambda f: f

# ------------------------------------------------------------------------
# Optional Tkinter GUI (falls back to headless-only operation if absent)
# ------------------------------------------------------------------------
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    _TKINTER_AVAILABLE = True
except Exception:
    _TKINTER_AVAILABLE = False


__version__ = "5.1"

CHECKPOINT_EVERY = 2000

# Backend-selection thresholds (tunable from GUI / CLI):
#   p < TH_ARRAY    -> QR lookup table   (O(p) memory, fastest)
#   p < TH_BITWISE  -> bitwise Jacobi    (O(1) memory)
#   p >= TH_BITWISE -> Euler criterion via modpow (O(1) memory, most frugal)
TH_ARRAY_DEFAULT = 1_000_000
TH_BITWISE_DEFAULT = 10_000_000

COLUMNS = [
    "p", "mod4", "mod5", "mod8", "mod20", "chi_minus1", "chi_5", "signature",
    "pisano", "v2_pisano", "alpha", "pi_over_alpha", "s", "chi_s", "T_alpha",
    "S_p", "abs_S", "plus", "minus", "zeros", "density_plus", "is_Z",
]


# ============================================================================
#  SECTION 1.  NUMBER-THEORETIC HELPERS
# ============================================================================

def sieve_primes(N):
    """Return a sorted array of all primes <= N (Eratosthenes sieve)."""
    s = np.ones(N + 1, dtype=bool)
    s[:2] = False
    for i in range(2, int(N ** 0.5) + 1):
        if s[i]:
            s[i * i::i] = False
    return np.flatnonzero(s)


def jacobi(a, n):
    """Pure-Python Jacobi symbol (a/n). Used only OUTSIDE the hot loop
    (signature classification), where it is called O(1) times per prime."""
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


def v2(n):
    """2-adic valuation of n (largest k with 2^k | n); v2(0) := -1."""
    if n == 0:
        return -1
    k = 0
    while (n & 1) == 0:
        n >>= 1
        k += 1
    return k


def signature_label(p):
    """Classify p by (chi_p(-1), chi_p(5)) into one of:
         DI       : chi_p(-1) = -1, chi_p(5) = -1
         fib_only : chi_p(-1) = +1, chi_p(5) = -1
         cm_only  : chi_p(-1) = -1, chi_p(5) = +1
         neither  : chi_p(-1) = +1, chi_p(5) = +1
    p in {2, 5} are special-cased.
    """
    if p in (2, 5):
        return 0, 0, "special"
    c1 = jacobi(p - 1, p)
    c5 = jacobi(5 % p, p)
    if c1 == -1 and c5 == -1:
        sig = "DI"
    elif c1 == 1 and c5 == -1:
        sig = "fib_only"
    elif c1 == -1 and c5 == 1:
        sig = "cm_only"
    else:
        sig = "neither"
    return c1, c5, sig


# ============================================================================
#  SECTION 2.  HOT-LOOP BACKENDS (one Fibonacci walk mod p, three flavours)
# ============================================================================
#
# All three backends compute, in ONE pass n = 1 .. (pi(p) - 1 or 6p+9):
#   - the Pisano period pi(p)               (first n with (F_n,F_{n+1})=(0,1))
#   - alpha(p)                              (first n with chi_p(F_n) = 0)
#   - s = F_{alpha(p)+1} mod p  and chi_p(s)
#   - T_alpha(p) = sum_{i=1}^{alpha(p)} chi_p(F_i)
#   - the FULL Pisano-period sum
#         S_p := sum_{n=1}^{pi(p)-1} chi_p(F_n)
#     reported by analyze_prime() as the "S_p" column.
#
# NOTATION VS THE PAPER
# ---------------------
# The paper defines its central object as
#         S(p) := sum_{n=1}^{p-1} chi_p(F_n)             [paper convention]
# whereas the code's S_p sums to pi(p) - 1.  These two quantities coincide
# EXACTLY in the full-rank regime  alpha(p) = p - 1  treated by the Main
# Theorem (cm_only signature, p == 11 or 19 (mod 20)), because then
#         pi(p) = alpha(p) = p - 1     (by E3, verified for all cm_only
#                                       primes p < 10^6, no exceptions)
# so the two sums have identical index ranges; and the term n = p-1 = alpha
# contributes chi_p(F_alpha) = chi_p(0) = 0 in any case.
#
# For DI / fib_only / neither primes, pi(p) > p - 1 in general (often
# pi(p) = 2(p+1) for inert primes), so the code's S_p and the paper's
# S(p) DIFFER.  The diagnostic tables (and Tables 1-15 of the working
# notes) use the code's S_p convention throughout; the Main-Theorem
# verification (`verify_corollary_B1`) restricts to the regime where they
# agree.
#
# Backend A (array)  : O(p) memory QR lookup table -- fastest.
# Backend B (bitwise): bitwise Jacobi symbol -- O(1) memory, ~2-3x slower.
# Backend C (pow)    : Euler's criterion via modpow -- O(1) memory, slowest
#                      but most memory-frugal (needed for very large p).
# ============================================================================

@njit(cache=True, inline='always')
def fast_jacobi_jit(a, p):
    """Bitwise Jacobi symbol (a/p), JIT-friendly (no recursion, no division
    other than '%')."""
    a = a % p
    if a == 0:
        return 0
    res = 1
    while a != 0:
        while (a & 1) == 0:
            a >>= 1
            pm8 = p & 7
            if pm8 == 3 or pm8 == 5:
                res = -res
        a, p = p, a
        if (a & 3) == 3 and (p & 3) == 3:
            res = -res
        a = a % p
    return res if p == 1 else 0

@njit(cache=True)
def core_walk_array(p):
    """Backend A: QR lookup table. Fastest, O(p) memory."""
    qr = np.full(p, -1, dtype=np.int8)
    qr[0] = 0
    for x in range(1, p):
        # تبدیل صریح به 64-بیت برای جلوگیری از سرریز محاسباتی قبل از پیمانه
        val = np.int64(x)
        qr[(val * val) % p] = 1

    f_prev, f_curr = 0, 1
    total = np.int64(0)
    plus = minus = zeros = 0
    alpha = -1
    s_val = -1
    T_alpha = 0
    captured_T = False

    LIMIT = 6 * p + 10
    for n in range(1, LIMIT):
        chi = qr[f_curr]
        total += chi
        if chi == 1:
            plus += 1
        elif chi == -1:
            minus += 1
        else:
            zeros += 1

        if alpha == -1 and chi == 0:
            alpha = n

        nxt = (f_prev + f_curr) % p
        f_prev, f_curr = f_curr, nxt

        # At n == alpha, f_curr is F_{alpha+1}; T_alpha = sum_{i=1}^{alpha} chi_p(F_i).
        if alpha != -1 and not captured_T and n == alpha:
            s_val = f_curr
            T_alpha = total
            captured_T = True

        if f_prev == 0 and f_curr == 1:
            chi_s = qr[s_val] if s_val >= 0 else 0
            return n, total, plus, minus, zeros, alpha, s_val, chi_s, T_alpha

    return -1, 0, 0, 0, 0, -1, -1, 0, 0


@njit(cache=True)
def core_walk_bitwise(p):
    """Backend B: bitwise Jacobi. O(1) memory."""
    f_prev, f_curr = 0, 1
    total = plus = minus = zeros = 0
    alpha = -1
    s_val = -1
    T_alpha = 0
    captured_T = False

    LIMIT = 6 * p + 10
    for n in range(1, LIMIT):
        chi = fast_jacobi_jit(f_curr, p)
        total += chi
        if chi == 1:
            plus += 1
        elif chi == -1:
            minus += 1
        else:
            zeros += 1

        if alpha == -1 and chi == 0:
            alpha = n

        nxt = (f_prev + f_curr) % p
        f_prev, f_curr = f_curr, nxt

        if alpha != -1 and not captured_T and n == alpha:
            s_val = f_curr
            T_alpha = total
            captured_T = True

        if f_prev == 0 and f_curr == 1:
            chi_s = fast_jacobi_jit(s_val, p) if s_val >= 0 else 0
            return n, total, plus, minus, zeros, alpha, s_val, chi_s, T_alpha

    return -1, 0, 0, 0, 0, -1, -1, 0, 0

@njit(cache=True, inline='always')
def modpow(base, exp, mod):
    """Modular exponentiation, JIT-friendly.

    SAFETY NOTE
    -----------
    This implementation uses signed int64 arithmetic.  The product
    `base * base` (and `result * base`) is computed at full int64 width
    before reduction mod `mod`.  This is safe as long as

         mod^2  <  2^63 - 1  ~=  9.22e18,

    i.e. for  mod < 2^31 ~= 2.147e9.  Since this routine is only invoked
    by `core_walk_pow`, which itself is selected by `core_walk(...)` only
    when  p >= TH_BITWISE  (default 10^7), the bound is comfortably
    respected for all practical N considered in the paper (N <= 10^6) and
    for the foreseeable extension range (N up to ~10^9).

    For p >= 2^31, switch to Python's built-in three-arg `pow(base, exp,
    mod)` (which uses arbitrary precision); but in that range the
    sequential Fibonacci walk itself becomes infeasible anyway.
    """
    # Promote to int64 to avoid overflow in successive squarings.
    result = np.int64(1)
    base = np.int64(base) % mod
    mod = np.int64(mod)

    while exp > 0:
        if exp & 1:
            result = (result * base) % mod
        exp >>= 1
        base = (base * base) % mod
    return int(result)

@njit(cache=True)
def core_walk_pow(p):
    """Backend C: Euler criterion via modpow. O(1) memory, most frugal."""
    half = (p - 1) // 2
    f_prev, f_curr = 0, 1
    total = plus = minus = zeros = 0
    alpha = -1
    s_val = -1
    T_alpha = 0
    captured_T = False

    LIMIT = 6 * p + 10
    for n in range(1, LIMIT):
        if f_curr == 0:
            chi = 0
        else:
            r = modpow(f_curr, half, p)
            chi = 1 if r == 1 else -1

        total += chi
        if chi == 1:
            plus += 1
        elif chi == -1:
            minus += 1
        else:
            zeros += 1

        if alpha == -1 and chi == 0:
            alpha = n

        nxt = (f_prev + f_curr) % p
        f_prev, f_curr = f_curr, nxt

        if alpha != -1 and not captured_T and n == alpha:
            s_val = f_curr
            T_alpha = total
            captured_T = True

        if f_prev == 0 and f_curr == 1:
            if s_val > 0:
                rs = modpow(s_val, half, p)
                chi_s = 1 if rs == 1 else -1
            else:
                chi_s = 0
            return n, total, plus, minus, zeros, alpha, s_val, chi_s, T_alpha

    return -1, 0, 0, 0, 0, -1, -1, 0, 0


def core_walk(p, th_array=TH_ARRAY_DEFAULT, th_bitwise=TH_BITWISE_DEFAULT):
    """Dispatch to the appropriate backend based on the size of p."""
    if p < th_array:
        return core_walk_array(p)
    elif p < th_bitwise:
        return core_walk_bitwise(p)
    else:
        return core_walk_pow(p)
        
@njit(cache=True, nogil=True)
def fib_mod_fast_doubling(n, p):
    """
    Returns (F_n, F_{n+1}) modulo p in O(log n) time.
    """
    if n == 0:
        return (0, 1)
    
    # Recursion represented iteratively using bits
    # Find highest bit
    calc_bits = []
    temp_n = n
    while temp_n > 0:
        calc_bits.append(temp_n & 1)
        temp_n >>= 1
        
    a, b = 0, 1
    for bit in calc_bits[::-1]:
        # Fast doubling identities:
        # F_{2k} = F_k * (2*F_{k+1} - F_k)
        # F_{2k+1} = F_{k+1}^2 + F_k^2
        c = (a * ((b << 1) - a)) % p
        d = (a * a + b * b) % p
        
        if bit == 0:
            a, b = c, d
        else:
            a, b = d, (c + d) % p
            
    return a, b


def analyze_prime(p, th_array=TH_ARRAY_DEFAULT, th_bitwise=TH_BITWISE_DEFAULT):
    """Run the full per-prime analysis and return a dict with all COLUMNS."""
    c1, c5, sig = signature_label(p)
    period, S, plus, minus, zeros, alpha, s_val, chi_s, T_alpha = core_walk(p, th_array, th_bitwise)
    pm = plus + minus
    return {
        "p": int(p), "mod4": p % 4, "mod5": p % 5, "mod8": p % 8, "mod20": p % 20,
        "chi_minus1": c1, "chi_5": c5, "signature": sig,
        "pisano": int(period), "v2_pisano": v2(period),
        "alpha": int(alpha),
        "pi_over_alpha": int(period // alpha) if alpha > 0 else -1,
        "s": int(s_val), "chi_s": int(chi_s), "T_alpha": int(T_alpha),
        "S_p": int(S), "abs_S": int(abs(S)),
        "plus": int(plus), "minus": int(minus), "zeros": int(zeros),
        "density_plus": (plus / pm) if pm > 0 else float("nan"),
        "is_Z": bool(S == 0),
    }


# ============================================================================
#  SECTION 3.  MAIN THEOREM / COROLLARY B1 VERIFICATION
# ============================================================================

def verify_corollary_B1(df, log_fn=print):
    """
    Computational verification of the paper's Main Theorem (Corollary B1):

        For primes p with alpha(p) = p-1 (which forces signature ==
        'cm_only' and p == 11 or 19 (mod 20), by Lemma 'Primitivity'):

            T_alpha(p) = S(p) = +1   if p == 11 (mod 20)
            T_alpha(p) = S(p) = -1   if p == 19 (mod 20)

    (T_alpha = S in this regime because alpha(p) = p-1 means the partial
    sum n=1..alpha already covers the entire period n=1..p-1.)

    This routine combines:
      - guard-rail diagnostics (flag any prime that violates the
        structural hypotheses the theorem relies on -- such a prime would
        indicate either a bug or a genuine counterexample), and
      - a concise vectorised pandas check of the +1 / -1 prediction.

    Returns (result_df, failures_df).
    """
    needed = {"p", "alpha", "signature", "mod20", "T_alpha"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns for B1 verification: {sorted(missing)}")

    log_fn("\n" + "=" * 78)
    log_fn(" COROLLARY B1 / MAIN THEOREM VERIFICATION")
    log_fn("=" * 78)

    df = df.copy()
    df["alpha_eq_pm1"] = (df["alpha"] == df["p"] - 1)
    candidates = df[df["alpha_eq_pm1"]].copy()

    log_fn(f"\nTotal primes with alpha(p) = p-1 : {len(candidates)}")
    log_fn(f"  of which cm_only signature     : {(candidates['signature'] == 'cm_only').sum()}")

    # Guard rail 1: Lemma "Primitivity" predicts alpha(p)=p-1 ==> signature
    # must be 'cm_only'. Any exception here would contradict the theory.
    non_cm = candidates[candidates["signature"] != "cm_only"]
    if len(non_cm) > 0:
        log_fn(f"\n[!] UNEXPECTED: {len(non_cm)} non-cm_only primes have alpha = p-1 "
               f"(this would CONTRADICT the Primitivity lemma):")
        log_fn(non_cm[["p", "mod20", "signature", "alpha"]].head(20).to_string(index=False))
    else:
        log_fn("\n[OK] Every prime with alpha(p) = p-1 has signature 'cm_only', "
               "as predicted by the Primitivity lemma.")

    cm = candidates[candidates["signature"] == "cm_only"].copy()

    # Guard rail 2: the Main Theorem predicts alpha(p)=p-1 ==> p == 11 or 19
    # (mod 20). Any other residue would contradict the theorem itself.
    cm["predicted"] = cm["mod20"].map({11: 1, 19: -1})
    out_of_range = cm[cm["predicted"].isna()]
    if len(out_of_range) > 0:
        log_fn(f"\n[!] UNEXPECTED: {len(out_of_range)} cm_only primes with alpha = p-1 "
               f"have p mod 20 not in {{11, 19}} (this would CONTRADICT the Main Theorem):")
        log_fn(out_of_range[["p", "mod20", "alpha", "T_alpha"]].head(20).to_string(index=False))
    else:
        log_fn("[OK] Every such prime satisfies p == 11 or 19 (mod 20), "
               "as predicted by the Main Theorem.")

    cm = cm[cm["predicted"].notna()].copy()
    # ---------------------------------------------------------------
    # CRITICAL SANITY CHECK (added in v5.1):
    # In the full-rank regime alpha(p) = p-1 (which forces pi(p) = p-1
    # by E3 for cm_only), the partial sum T_alpha and the full Pisano
    # sum S_p MUST be numerically identical.  A discrepancy here would
    # indicate a bug in the hot-loop accounting (e.g. an off-by-one in
    # when T_alpha is captured, or a stray zero contribution).
    # This guard-rail catches such bugs BEFORE the +1/-1 check below,
    # which would otherwise mask them.
    # ---------------------------------------------------------------
    inconsistent = cm[cm["T_alpha"] != cm["S_p"]]
    if len(inconsistent) > 0:
        log_fn(f"\n[!!! CRITICAL BUG !!!] {len(inconsistent)} primes in the "
               f"full-rank regime have T_alpha != S_p.")
        log_fn("This contradicts E3 (pi = alpha on cm_only) combined with "
               "alpha = p-1, and indicates a BUG in core_walk's accounting.")
        log_fn("First 10 offending rows:")
        log_fn(inconsistent[["p", "alpha", "pisano", "T_alpha", "S_p"]]
               .head(10).to_string(index=False))
        log_fn("Refusing to continue verification until this is resolved.\n")
        # Return early with the inconsistent rows as "failures" so the
        # caller's downstream code (Excel/LaTeX export, CI exit code)
        # treats this as a hard failure.
        result_df = pd.DataFrame([{
            "p_mod_20": -1,
            "predicted_S(p)": 0,
            "count": len(inconsistent),
            "matches": 0,
            "mismatches": len(inconsistent),
            "verified": "CRITICAL_BUG_T_alpha_neq_S_p",
        }])
        return result_df, inconsistent
    else:
        log_fn("[OK] T_alpha == S_p for all full-rank primes "
               "(internal consistency of the hot loop is sound).")
                 
# ============================================================================
# Final theorem verification
# ============================================================================
    cm["matches"] = (cm["T_alpha"] == cm["predicted"])

    summary_rows = []
    failures = []

    for residue in (11, 19):
        sub = cm[cm["mod20"] == residue]

        summary_rows.append({
            "p_mod_20": residue,
            "predicted_S(p)": 1 if residue == 11 else -1,
            "count": len(sub),
            "matches": int(sub["matches"].sum()),
            "mismatches": int((~sub["matches"]).sum()),
            "verified": bool(sub["matches"].all()) if len(sub) else True,
        })

        if len(sub):
            failures.append(
                sub.loc[
                    ~sub["matches"],
                    ["p", "mod20", "alpha", "pisano",
                     "T_alpha", "S_p", "predicted"]
                ]
            )

    result_df = pd.DataFrame(summary_rows)

    failures_df = (
        pd.concat(failures, ignore_index=True)
        if failures else
        pd.DataFrame()
    )

    return result_df, failures_df
                         
 # ============================================================================
#  SECTION 3b.  VERIFICATION OF ALL EMPIRICAL CLAIMS (E1-E10)
# ============================================================================

def verify_all_empirical_claims(df, log_fn=print):
    """
    Machine-verify each empirical claim E1..E10 reported in the paper's
    project notes, on the supplied database `df`.  Returns a DataFrame
    summarising PASS / FAIL for each claim along with the sample size.

    Claims verified
    ---------------
    E1  : p in DI  ==>  v_2(pi(p)) = v_2(p+1) + 1
    E2  : p in Z \ DI  ==>  pi(p) = 4 alpha(p)  AND  alpha(p) is odd
    E3  : p in cm_only  ==>  pi(p) = alpha(p)
    E4  : p inert (DI or fib_only)  ==>  alpha(p) | (p+1)
    E5  : p split (cm_only or neither)  ==>  alpha(p) | (p-1)
    E6  : chi_p(-1) = -1  ==>  k = (p +/- 1)/pi(p) is odd
          (for inert primes use p+1, for split use p-1)
    E7  : chi_p(-1) = +1  ==>  k = (p +/- 1)/pi(p) is even
    E8  : p in cm_only with alpha(p) = p-1 (full-rank regime):
              S(p) = +1 if p == 1 (mod 5),
              S(p) = -1 if p == 4 (mod 5).
          (This is the Main Theorem proved in the paper.)

    Notes
    -----
    E9 (parity of |S_p| on cm_only k=3) and E10 (8 | S_p on fib_only k=2)
    are diagnostic observations that the paper itself does not depend on;
    they are reported here for completeness but as separate "info" rows
    rather than as hard PASS/FAIL invariants.
    """
    log_fn("\n" + "=" * 78)
    log_fn(" VERIFICATION OF ALL EMPIRICAL CLAIMS (E1-E10)")
    log_fn("=" * 78)

    main = df[~df["p"].isin([2, 5])].copy()
    results = []

    def record(name, passes, n_tested, n_violations=0, info=""):
        results.append({
            "claim": name,
            "passes": bool(passes),
            "n_tested": int(n_tested),
            "n_violations": int(n_violations),
            "status": "PASS" if passes else ("FAIL" if n_tested else "N/A"),
            "info": info,
        })

    # ---- E1 ----
    DI = main[main["signature"] == "DI"].copy()
    if len(DI):
        DI["v2_p_plus_1"] = DI["p"].apply(lambda p: v2(int(p) + 1))
        viol = (DI["v2_pisano"] != DI["v2_p_plus_1"] + 1).sum()
        record("E1: v_2(pi) = v_2(p+1) + 1  on DI",
               viol == 0, len(DI), viol)
    else:
        record("E1: v_2(pi) = v_2(p+1) + 1  on DI", True, 0)

    # ---- E2 ----
    Z = main["is_Z"]
    DI_mask = main["signature"] == "DI"
    ZmD = main[Z & ~DI_mask].copy()
    if len(ZmD):
        cond = (ZmD["pisano"] == 4 * ZmD["alpha"]) & (ZmD["alpha"] % 2 == 1)
        viol = (~cond).sum()
        record("E2: pi = 4 alpha AND alpha odd  on Z \\ DI",
               viol == 0, len(ZmD), viol)
    else:
        record("E2: pi = 4 alpha AND alpha odd  on Z \\ DI", True, 0)

    # ---- E3 ----
    cm = main[main["signature"] == "cm_only"]
    if len(cm):
        viol = (cm["pisano"] != cm["alpha"]).sum()
        record("E3: pi = alpha  on cm_only",
               viol == 0, len(cm), viol)
    else:
        record("E3: pi = alpha  on cm_only", True, 0)

    # ---- E4 ----
    inert = main[main["signature"].isin(["DI", "fib_only"])]
    if len(inert):
        viol = ((inert["p"] + 1) % inert["alpha"] != 0).sum()
        record("E4: alpha | (p+1)  for inert primes (DI U fib_only)",
               viol == 0, len(inert), viol)
    else:
        record("E4: alpha | (p+1)  for inert primes", True, 0)

    # ---- E5 ----
    split = main[main["signature"].isin(["cm_only", "neither"])]
    if len(split):
        viol = ((split["p"] - 1) % split["alpha"] != 0).sum()
        record("E5: alpha | (p-1)  for split primes (cm_only U neither)",
               viol == 0, len(split), viol)
    else:
        record("E5: alpha | (p-1)  for split primes", True, 0)

    # ---- E6 + E7  (parity of k via signature-aware definition) ----
    main_E67 = main.copy()
    is_inert = main_E67["signature"].isin(["DI", "fib_only"])
    main_E67["k_signed"] = np.where(
        is_inert,
        (main_E67["p"] + 1) // main_E67["alpha"],
        (main_E67["p"] - 1) // main_E67["alpha"],
    )

    chi_neg1_minus = (main_E67["chi_minus1"] == -1)  # DI U cm_only
    chi_neg1_plus = (main_E67["chi_minus1"] == 1)    # fib_only U neither

    sub6 = main_E67[chi_neg1_minus]
    viol6 = (sub6["k_signed"] % 2 != 1).sum()
    record("E6: chi_p(-1) = -1  ==>  k is odd",
           viol6 == 0, len(sub6), viol6)

    sub7 = main_E67[chi_neg1_plus]
    viol7 = (sub7["k_signed"] % 2 != 0).sum()
    record("E7: chi_p(-1) = +1  ==>  k is even",
           viol7 == 0, len(sub7), viol7)

    # ---- E8 (Main Theorem) ----
    cm_b1 = main[(main["signature"] == "cm_only") &
                 (main["alpha"] == main["p"] - 1)].copy()
    if len(cm_b1):
        # In this regime S_p == T_alpha (checked in verify_corollary_B1).
        # The Main Theorem says S(p) = +1 if p == 1 mod 5, -1 if p == 4 mod 5.
        cm_b1["predicted"] = cm_b1["mod5"].map({1: 1, 4: -1})
        out_of_range = cm_b1["predicted"].isna().sum()
        if out_of_range > 0:
            record("E8: full-rank cm_only restricted to p == 1 or 4 (mod 5)",
                   False, len(cm_b1), int(out_of_range),
                   info=f"{out_of_range} primes have p mod 5 not in {{1,4}}")
        valid = cm_b1[cm_b1["predicted"].notna()]
        viol8 = (valid["S_p"] != valid["predicted"]).sum()
        record("E8: S(p) = +1 if p == 1 mod 5, -1 if p == 4 mod 5  "
               "(MAIN THEOREM, full-rank cm_only)",
               viol8 == 0, len(valid), int(viol8))
    else:
        record("E8: Main Theorem (no full-rank cm_only primes in sample)",
               True, 0, info="sample too small")

    # ---- E9 (diagnostic, not a hard claim) ----
    cm_k3 = main[(main["signature"] == "cm_only") &
                 ((main["p"] - 1) // main["alpha"] == 3)]
    if len(cm_k3) > 0:
        all_odd = (cm_k3["abs_S"] % 2 == 1).all()
        info = (f"|S_p| is odd for all {len(cm_k3)} cm_only primes with k=3"
                if all_odd else "some |S_p| are even -- diagnostic observation")
        results.append({
            "claim": "E9 (info): |S_p| odd on cm_only with k=3",
            "passes": bool(all_odd),
            "n_tested": len(cm_k3),
            "n_violations": int((cm_k3["abs_S"] % 2 != 1).sum()),
            "status": "INFO",
            "info": info,
        })

    # ---- E10 (diagnostic) ----
    fo = main[main["signature"] == "fib_only"].copy()
    if len(fo) > 0:
        fo["k"] = (fo["p"] + 1) // fo["alpha"]
        fo_k2 = fo[fo["k"] == 2]
        if len(fo_k2) > 0:
            all_div8 = (fo_k2["S_p"] % 8 == 0).all()
            info = (f"8 | S_p for all {len(fo_k2)} fib_only primes with k=2"
                    if all_div8 else
                    f"{(fo_k2['S_p'] % 8 != 0).sum()} violations -- needs investigation")
            results.append({
                "claim": "E10 (info): 8 | S_p on fib_only with k=2",
                "passes": bool(all_div8),
                "n_tested": len(fo_k2),
                "n_violations": int((fo_k2["S_p"] % 8 != 0).sum()),
                "status": "INFO",
                "info": info,
            })

    df_results = pd.DataFrame(results)
    log_fn("\n" + df_results.to_string(index=False))

    n_pass = (df_results["status"] == "PASS").sum()
    n_fail = (df_results["status"] == "FAIL").sum()
    n_info = (df_results["status"] == "INFO").sum()
    log_fn(f"\nSummary: {n_pass} PASS  |  {n_fail} FAIL  |  {n_info} INFO")
    if n_fail > 0:
        log_fn("\n[!] Some hard claims failed.  Investigate before submission.")
    else:
        log_fn("\n[OK] All hard empirical claims (E1-E8) verified.")

    return df_results

# ============================================================================
#  SECTION 4.  CHECKPOINTING (sequential pipeline only)
# ============================================================================

def ckpt_paths(out_dir, N_max):
    base = os.path.join(out_dir, f"checkpoint_N{N_max}")
    return base + ".parquet", base + ".meta.json"


def save_checkpoint(out_dir, N_max, rows_dict, last_index, total_primes, elapsed):
    os.makedirs(out_dir, exist_ok=True)
    pq, meta = ckpt_paths(out_dir, N_max)
    df = pd.DataFrame(rows_dict)
    try:
        df.to_parquet(pq, index=False)
        saved = pq
    except Exception:
        csv = pq.replace(".parquet", ".csv")
        df.to_csv(csv, index=False)
        saved = csv
    with open(meta, "w", encoding="utf-8") as f:
        json.dump({
            "N_max": int(N_max),
            "last_index": int(last_index),
            "total_primes": int(total_primes),
            "elapsed_sec": float(elapsed),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "saved_data": saved,
        }, f, indent=2)


def load_checkpoint(out_dir, N_max):
    pq, meta = ckpt_paths(out_dir, N_max)
    csv_fb = pq.replace(".parquet", ".csv")
    if not os.path.exists(meta):
        return None
    with open(meta, encoding="utf-8") as f:
        m = json.load(f)
    if os.path.exists(pq):
        df = pd.read_parquet(pq)
    elif os.path.exists(csv_fb):
        df = pd.read_csv(csv_fb)
    else:
        return None
    return df, m


def delete_checkpoint(out_dir, N_max):
    pq, meta = ckpt_paths(out_dir, N_max)
    for p in (pq, meta, pq.replace(".parquet", ".csv")):
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


# ============================================================================
#  SECTION 5.  SEQUENTIAL DATABASE BUILDER (with checkpoint/resume/stop)
# ============================================================================

def build_database(N_max, out_dir, log_fn, progress_fn,
                    th_array=TH_ARRAY_DEFAULT, th_bitwise=TH_BITWISE_DEFAULT,
                    resume_df=None, resume_meta=None, stop_event=None):
    primes = sieve_primes(N_max)
    n = int(len(primes))
    log_fn(f"[+] backend       : {'Numba JIT' if HAS_NUMBA else 'pure Python (SLOW)'}")
    log_fn(f"[+] primes <= {N_max} : {n}")
    log_fn(f"[+] thresholds    : array<{th_array:,}  bitwise<{th_bitwise:,}  pow>=")

    if HAS_NUMBA:
        log_fn("[+] warming JIT (all 3 backends) ...")
        _ = core_walk_array(7)
        _ = core_walk_bitwise(7)
        _ = core_walk_pow(7)

    cols = {k: [] for k in COLUMNS}
    start_idx = 0
    elapsed_prev = 0.0

    if resume_df is not None and resume_meta is not None:
        for k in COLUMNS:
            if k in resume_df.columns:
                cols[k] = resume_df[k].tolist()
        start_idx = int(resume_meta.get("last_index", 0))
        elapsed_prev = float(resume_meta.get("elapsed_sec", 0.0))
        log_fn(f"[+] RESUMING from index {start_idx} "
               f"({100*start_idx/n:.1f}% done, prev elapsed {elapsed_prev:.0f}s)")
        progress_fn(start_idx / max(n, 1))

    t0 = time.time()
    next_log_at = start_idx + 500
    next_ckpt_at = start_idx + CHECKPOINT_EVERY

    for i in range(start_idx, n):
        if stop_event is not None and stop_event.is_set():
            elapsed_now = elapsed_prev + (time.time() - t0)
            log_fn(f"[!] STOP at index {i}. Saving checkpoint ...")
            save_checkpoint(out_dir, N_max, cols, i, n, elapsed_now)
            log_fn(f"[+] checkpoint saved at index {i}.")
            return None

        rec = analyze_prime(int(primes[i]), th_array, th_bitwise)
        for k in COLUMNS:
            cols[k].append(rec[k])

        idx1 = i + 1
        if idx1 >= next_log_at or idx1 == n:
            dt = time.time() - t0
            elapsed_now = elapsed_prev + dt
            rate = (idx1 - start_idx) / max(dt, 1e-9)
            eta = (n - idx1) / max(rate, 1e-9)
            log_fn(f"    {idx1:8d}/{n}  p={rec['p']:9d}  rate={rate:9.1f}/s  "
                   f"ETA={eta:7.0f}s  elapsed_total={elapsed_now:.0f}s")
            next_log_at = min(next_log_at * 2, next_log_at + 5000)

        if idx1 >= next_ckpt_at and idx1 < n:
            elapsed_now = elapsed_prev + (time.time() - t0)
            save_checkpoint(out_dir, N_max, cols, idx1, n, elapsed_now)
            log_fn(f"    [ckpt] saved at index {idx1}")
            next_ckpt_at = idx1 + CHECKPOINT_EVERY

        progress_fn(idx1 / n)

    df = pd.DataFrame(cols)
    elapsed_now = elapsed_prev + (time.time() - t0)
    log_fn(f"[+] compute finished (session {time.time()-t0:.1f}s, "
           f"total {elapsed_now:.1f}s, {len(df)} rows)")
    return df


# ============================================================================
#  SECTION 6.  OPTIONAL MULTI-PROCESS PIPELINE (no checkpoint/resume)
# ============================================================================

def analyze_chunk(args):
    chunk, th_a, th_b = args
    return [analyze_prime(int(p), th_a, th_b) for p in chunk]


def build_database_parallel(primes, workers, chunk_size, th_a, th_b):
    """Compute the full database using a process pool.

    NOTE: this path does not support checkpoint/resume or live
    progress/ETA. For N = 10^6 it is normally fast enough on a modern
    multi-core machine that this is not needed; for much larger N prefer
    `build_database` with checkpointing.
    """
    chunks = [primes[i:i + chunk_size] for i in range(0, len(primes), chunk_size)]
    frames = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(analyze_chunk, (c, th_a, th_b)): i for i, c in enumerate(chunks)}
        for fut in as_completed(futures):
            frames.append(pd.DataFrame(fut.result()))
    df =pd.concat(frames, ignore_index=True)
    # restore ascending-p order (ProcessPoolExecutor completion order is
    # not guaranteed) so downstream reports/CSV are deterministic
    return df.sort_values("p").reset_index(drop=True)


# ============================================================================
#  SECTION 7.  DIAGNOSTIC TABLES (Tables 1-15 of the working notes)
# ============================================================================

def compute_all_tables(df):
    out = {}
    main = df[~df["p"].isin([2, 5])].copy()
    n = len(main)
    Z = main["is_Z"]
    DI = main["signature"] == "DI"
    ZmD = Z & ~DI
    ZaD = Z & DI

    out["00_headline"] = pd.DataFrame([
        ["delta(Z)", Z.mean(), int(Z.sum()), n],
        ["delta(DI)", DI.mean(), int(DI.sum()), n],
        ["delta(Z and DI)", ZaD.mean(), int(ZaD.sum()), n],
        ["delta(Z minus DI)", ZmD.mean(), int(ZmD.sum()), n],
        ["P(Z|DI)", ZaD.sum() / max(DI.sum(), 1), int(ZaD.sum()), int(DI.sum())],
    ], columns=["quantity", "value", "numerator", "denominator"])

    SIGS = ["DI", "fib_only", "cm_only", "neither"]
    sg = main["signature"].value_counts()
    out["01_signature_counts"] = pd.DataFrame([
        {"signature": s, "count": int(sg.get(s, 0)), "fraction": sg.get(s, 0) / n}
        for s in SIGS
    ])

    out["02_P_Z_given_signature"] = pd.DataFrame([
        {"signature": s, "n_sig": len(main[main["signature"] == s]),
         "n_Z": int(main[main["signature"] == s]["is_Z"].sum()),
         "P_Z_given_sig": main[main["signature"] == s]["is_Z"].mean()
         if len(main[main["signature"] == s]) else float("nan")}
        for s in SIGS
    ])

    out["03_Sp_stats_by_signature"] = pd.DataFrame([
        {"signature": s,
         "mean(S_p)": main[main["signature"] == s]["S_p"].mean(),
         "std(S_p)": main[main["signature"] == s]["S_p"].std(),
         "mean|S_p|": main[main["signature"] == s]["abs_S"].mean(),
         "max|S_p|": int(main[main["signature"] == s]["abs_S"].max())}
        for s in SIGS if len(main[main["signature"] == s])]
    )

    classes = {"all": main, "Z": main[Z], "DI": main[DI],
               "Z_minus_DI": main[ZmD], "Z_and_DI": main[ZaD]}
    out["04_v2_per_class"] = pd.DataFrame([
        {"class": k, "n": len(v), "mean_v2": v["v2_pisano"].mean(),
         "median_v2": int(v["v2_pisano"].median()),
         "min_v2": int(v["v2_pisano"].min()),
         "max_v2": int(v["v2_pisano"].max())}
        if len(v) else
        {"class": k, "n": 0, "mean_v2": float("nan"),
         "median_v2": -1, "min_v2": -1, "max_v2": -1}
        for k, v in classes.items()
    ])

    keys = sorted(int(x) for x in main["v2_pisano"].unique())
    all_d = main["v2_pisano"].value_counts(normalize=True)
    Z_d = main[Z]["v2_pisano"].value_counts(normalize=True)
    ZD_d = main[ZmD]["v2_pisano"].value_counts(normalize=True) if ZmD.sum() else pd.Series(dtype=float)
    DI_d = main[DI]["v2_pisano"].value_counts(normalize=True)
    out["04b_v2_distribution"] = pd.DataFrame([
        {"v2": k, "freq_all": float(all_d.get(k, 0)), "freq_Z": float(Z_d.get(k, 0)),
         "freq_Z_minus_DI": float(ZD_d.get(k, 0)), "freq_DI": float(DI_d.get(k, 0))}
        for k in keys
    ])

    out["05_mod20_distribution"] = pd.DataFrame([
        {"mod20": int(m), "count": len(main[main["mod20"] == m]),
         "fraction": len(main[main["mod20"] == m]) / n,
         "n_Z": int(main[main["mod20"] == m]["is_Z"].sum()),
         "P_Z_given_mod20": main[main["mod20"] == m]["is_Z"].mean()
         if len(main[main["mod20"] == m]) else float("nan")}
        for m in sorted(main["mod20"].unique())
    ])

    out["06_mod8_distribution"] = pd.DataFrame([
        {"mod8": int(m), "count": len(main[main["mod8"] == m]),
         "fraction": len(main[main["mod8"] == m]) / n,
         "n_Z": int(main[main["mod8"] == m]["is_Z"].sum()),
         "P_Z_given_mod8": main[main["mod8"] == m]["is_Z"].mean()
         if len(main[main["mod8"] == m]) else float("nan")}
        for m in sorted(main["mod8"].unique())
    ])

    rows = []
    for k in sorted(main["v2_pisano"].unique()):
        sub = main[main["v2_pisano"] == int(k)]
        row = {"k": int(k), "n_k": len(sub), "n_Z": int(sub["is_Z"].sum()),
               "P_Z_given_k": sub["is_Z"].mean()}
        for m in [1, 3, 5, 7]:
            ss = sub[sub["mod8"] == m]
            row[f"P_Z_given_k_mod8_{m}"] = ss["is_Z"].mean() if len(ss) else float("nan")
            row[f"n_k_mod8_{m}"] = len(ss)
        rows.append(row)
    out["07_2adic_tower"] = pd.DataFrame(rows)

    rows = []
    for sig in SIGS:
        sub = main[main["signature"] == sig]
        for k in sorted(sub["v2_pisano"].unique()):
            ss = sub[sub["v2_pisano"] == k]
            rows.append({"signature": sig, "v2_pisano": int(k),
                          "n": len(ss), "n_Z": int(ss["is_Z"].sum()),
                          "n_not_Z": int((~ss["is_Z"]).sum()),
                          "P_Z": ss["is_Z"].mean() if len(ss) else float("nan")})
    out["08_v2_signature_isZ"] = pd.DataFrame(rows)

    DI_df = main[DI]
    rows = []
    for m in sorted(DI_df["mod8"].unique()):
        for k in sorted(DI_df[DI_df["mod8"] == m]["v2_pisano"].unique()):
            ss = DI_df[(DI_df["mod8"] == m) & (DI_df["v2_pisano"] == k)]
            rows.append({"mod8": int(m), "v2_pisano": int(k),
                          "count": len(ss), "all_in_Z": bool(ss["is_Z"].all())})
    out["08b_DI_mod8_v2_split"] = pd.DataFrame(rows)

    out_Z = main[~Z]
    out["09_near_cancellation"] = pd.DataFrame([
        {"threshold": t, "count_below": int((out_Z["abs_S"] <= t).sum()),
         "fraction_of_nonZ": int((out_Z["abs_S"] <= t).sum()) / len(out_Z)}
        for t in (1, 2, 4, 8, 16, 32, 64)
    ]) if len(out_Z) else pd.DataFrame()

    ZmD_df = main[ZmD]
    if len(ZmD_df):
        d = ZmD_df["mod8"].value_counts().sort_index()
        out["10_ZminusDI_mod8"] = pd.DataFrame({"mod8": d.index.astype(int), "count": d.values})
        d = ZmD_df["pi_over_alpha"].value_counts().sort_index()
        out["11_ZminusDI_pi_over_alpha"] = pd.DataFrame({"pi_over_alpha": d.index.astype(int), "count": d.values})
        out["12_ZminusDI_mod1_exceptions"] = ZmD_df[ZmD_df["mod8"] == 1][
            ["p", "pisano", "alpha", "pi_over_alpha", "mod8", "s", "chi_s", "T_alpha", "S_p", "signature"]
        ]

    cand = main[(main["v2_pisano"] == 2) & (main["mod8"] == 1)]
    if len(cand):
        Ta = cand["T_alpha"]
        out["13_T_alpha_stats_mod1_v2eq2"] = pd.DataFrame([{
            "n": len(cand), "mean": Ta.mean(), "std": Ta.std(),
            "min": int(Ta.min()), "median": float(Ta.median()), "max": int(Ta.max()),
            "n_T_alpha_eq_0": int((Ta == 0).sum()),
            "expected_by_random_walk": float((1.0 / np.sqrt(cand["alpha"].astype(float))).sum()),
        }])

    out["14_Z_density_decomposition"] = pd.DataFrame([
        {"component": "DI", "delta": DI.mean(), "count": int(DI.sum())},
        {"component": "Z and (v2=2, p=5 mod 8) [auto cancellation]",
         "delta": ((main["v2_pisano"] == 2) & (main["mod8"] == 5) & Z).mean(),
         "count": int(((main["v2_pisano"] == 2) & (main["mod8"] == 5) & Z).sum())},
        {"component": "Z and (v2=2, p=1 mod 8) [rare T_alpha=0]",
         "delta": ((main["v2_pisano"] == 2) & (main["mod8"] == 1) & Z).mean(),
         "count": int(((main["v2_pisano"] == 2) & (main["mod8"] == 1) & Z).sum())},
        {"component": "TOTAL Z", "delta": Z.mean(), "count": int(Z.sum())},
    ])

    sanity = []
    sanity.append(("P(Z|DI) = 1",
                    bool(ZaD.sum() == DI.sum()), int(DI.sum() - ZaD.sum())))
    sanity.append(("pi/alpha = 4 for all Z\\DI",
                    bool((ZmD_df["pi_over_alpha"] == 4).all()) if len(ZmD_df) else True,
                    int((ZmD_df["pi_over_alpha"] != 4).sum()) if len(ZmD_df) else 0))
    sanity.append(("v2(pi) = 2 for all Z\\DI",
                    bool((ZmD_df["v2_pisano"] == 2).all()) if len(ZmD_df) else True,
                    int((ZmD_df["v2_pisano"] != 2).sum()) if len(ZmD_df) else 0))
    sanity.append(("cm_only never in Z",
                    bool(main[main["signature"] == "cm_only"]["is_Z"].sum() == 0),
                    int(main[main["signature"] == "cm_only"]["is_Z"].sum())))
    sanity.append(("v2(pi)>=3 for all DI",
                    bool((main[DI]["v2_pisano"] >= 3).all()),
                    int((main[DI]["v2_pisano"] < 3).sum())))
    sanity.append(("DI mod 8 = 3 ==> v2(pi) = 3",
                    bool((main[DI & (main["mod8"] == 3)]["v2_pisano"] == 3).all()),
                    int((main[DI & (main["mod8"] == 3)]["v2_pisano"] != 3).sum())))
    sanity.append(("DI mod 8 = 7 ==> v2(pi) >= 4",
                    bool((main[DI & (main["mod8"] == 7)]["v2_pisano"] >= 4).all()),
                    int((main[DI & (main["mod8"] == 7)]["v2_pisano"] < 4).sum())))

    cm_b1 = main[(main["signature"] == "cm_only") & (main["alpha"] == main["p"] - 1)]
    if len(cm_b1):
        bad_11 = ((cm_b1["mod20"] == 11) & (cm_b1["T_alpha"] != 1)).sum()
        bad_19 = ((cm_b1["mod20"] == 19) & (cm_b1["T_alpha"] != -1)).sum()
        sanity.append(("Cor B1: T_alpha = +1 for p == 11 (mod 20)",
                        bool(bad_11 == 0), int(bad_11)))
        sanity.append(("Cor B1: T_alpha = -1 for p == 19 (mod 20)",
                        bool(bad_19 == 0), int(bad_19)))

    if len(ZmD_df):
        sample = ZmD_df.sample(min(200, len(ZmD_df)), random_state=0)
        bad = sum(1 for _, r in sample.iterrows()
                  if (int(r["s"]) ** 2) % int(r["p"]) != int(r["p"]) - 1)
        sanity.append((f"s^2 == -1 (mod p)  [sample of {len(sample)}]",
                        bad == 0, bad))

    out["15_sanity_checks"] = pd.DataFrame(sanity, columns=["invariant", "passes", "violations"])

    return out, main, Z, DI, ZmD


# ============================================================================
#  SECTION 8.  REPORT FORMATTING
# ============================================================================

def format_tables_for_log(tables, n_total, n_main):
    L = [
        "=" * 78, " UNIFIED DIAGNOSTIC REPORT (v5)", "=" * 78,
        f"\nTotal primes      : {n_total}",
        f"Main set (p!=2,5) : {n_main}",
    ]
    titles = [
        ("00_headline", "[ HEADLINE ]"),
        ("01_signature_counts", "[ TABLE 1 ] signature counts"),
        ("02_P_Z_given_signature", "[ TABLE 2 ] P(Z | signature)"),
        ("03_Sp_stats_by_signature", "[ TABLE 3 ] S_p statistics per signature"),
        ("04_v2_per_class", "[ TABLE 4 ] v2(pi) per class"),
        ("04b_v2_distribution", "[ TABLE 4b ] full distribution of v2(pi)"),
        ("05_mod20_distribution", "[ TABLE 5 ] P(Z | mod 20)"),
        ("06_mod8_distribution", "[ TABLE 6 ] P(Z | mod 8)"),
        ("07_2adic_tower", "[ TABLE 7 ] THE 2-ADIC TOWER  P(Z | v2(pi)=k)"),
        ("08_v2_signature_isZ", "[ TABLE 8 ] cross-table v2 x signature x is_Z"),
        ("08b_DI_mod8_v2_split", "[ TABLE 8b ] DI primes split by (mod 8, v2(pi))"),
        ("09_near_cancellation", "[ TABLE 9 ] near-cancellation in Z^c"),
        ("10_ZminusDI_mod8", "[ TABLE 10 ] Z\\DI distribution by p mod 8"),
        ("11_ZminusDI_pi_over_alpha", "[ TABLE 11 ] Z\\DI distribution of pi/alpha"),
        ("12_ZminusDI_mod1_exceptions", "[ TABLE 12 ] Z\\DI exceptions (p=1 mod 8)"),
        ("13_T_alpha_stats_mod1_v2eq2", "[ TABLE 13 ] T_alpha stats (p=1 mod 8, v2=2)"),
        ("14_Z_density_decomposition", "[ TABLE 14 ] delta(Z) decomposition"),
        ("15_sanity_checks", "[ TABLE 15 ] SANITY CHECKS (must all pass)"),
        ("16_corollary_B1_verification", "[ TABLE 16 ] Corollary B1 / Main Theorem verification"),
        ("16b_corollary_B1_failures", "[ TABLE 16b ] Corollary B1 / Main Theorem FAILURES (if any)"),
        ("17_empirical_claims_E1_to_E10",
         "[ TABLE 17 ] All empirical claims E1-E10 (PASS/FAIL/INFO)"),
        
    ]
    for name, title in titles:
        if name in tables and len(tables[name]):
            L.append("\n" + title)
            L.append(tables[name].to_string(index=False))

    d = tables["00_headline"]
    delta_ZmD = float(d[d["quantity"] == "delta(Z minus DI)"]["value"].iloc[0])
    L.append("\n[ GO / NO-GO VERDICT ]")
    if delta_ZmD < 0.005:
        v = "ESSENTIALLY EMPTY."
    elif delta_ZmD < 0.020:
        v = "THIN."
    elif delta_ZmD < 0.050:
        v = "MARGINAL."
    else:
        v = "SUBSTANTIAL. Hidden structure!"
    L.append(f"    delta(Z\\DI) = {delta_ZmD:.5f}   >>> {v}")
    L.append("=" * 78)
    return "\n".join(L)


# ============================================================================
#  SECTION 9.  OUTPUT SAVING (CSV / XLSX / TXT / LaTeX)
# ============================================================================

def save_outputs(df, tables, report_text, out_dir, N_max, log_fn):
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, f"fib_char_db_N{N_max}.csv")
    xlsx_path = os.path.join(out_dir, f"fib_char_report_N{N_max}.xlsx")
    txt_path = os.path.join(out_dir, f"fib_char_report_N{N_max}.txt")

    df.to_csv(csv_path, index=False)
    log_fn(f"[+] saved CSV  -> {csv_path}")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    log_fn(f"[+] saved TXT  -> {txt_path}")

    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
            (df if len(df) <= 1_000_000 else df.head(1_000_000)).to_excel(
                w, sheet_name="raw_data", index=False)
            for name, t in tables.items():
                if len(t):
                    t.to_excel(w, sheet_name=name[:31], index=False)
        log_fn(f"[+] saved XLSX -> {xlsx_path}")
    except Exception as e:
        log_fn(f"[!] Excel save failed ({e}). CSV/TXT still available.")


def export_latex_tables(tables, out_dir):
    """Write every non-empty table to its own .tex file (booktabs-ready)
    for direct \\input{} into the LaTeX manuscript."""
    latex_dir = os.path.join(out_dir, "latex_tables")
    os.makedirs(latex_dir, exist_ok=True)
    for name, df in tables.items():
        if len(df) == 0:
            continue
        path = os.path.join(latex_dir, f"{name}.tex")
        with open(path, "w", encoding="utf-8") as f:
            f.write("% Auto-generated from FibChar v5\n")
            f.write(df.to_latex(index=False, escape=False, column_format="l" * len(df.columns)))


# ============================================================================
#  SECTION 10.  SELF-TEST (Appendix A worked examples)
# ============================================================================

def run_self_test(log_fn=print):
    """
    Instant sanity check reproducing the worked examples of Appendix A:

        S(11) = +1,  S(19) = -1,  S(31) = +1,  S(59) = -1,  S(79) = -1

    For p in {11, 19, 59, 79}, alpha(p) = p-1 (full rank), so S(p) is
    additionally checked against T_alpha(p) via Corollary B1. For p = 31,
    alpha(31) = 30 = p-1 as well (p == 11 mod 20), so S(31) = +1 is
    likewise predicted by Corollary B1.

    NOTE ON NOTATION (flagged for the manuscript): in Appendix A the
    symbols "alpha"/"beta" denote the two roots of x^2 - x - 1 in F_p (the
    notation of the structural-identity section), which is a DIFFERENT
    object from the rank of apparition alpha(p) computed by this program.
    E.g. for p=11 the appendix's "alpha=8" is the nonresidue root of
    x^2-x-1 in F_11, whereas the rank of apparition is alpha(11)=10=p-1.
    This self-test checks S(p), which is unambiguous in both notations.
    """
    log_fn("\n" + "=" * 78)
    log_fn(" SELF-TEST: Appendix-A worked examples (values of S(p))")
    log_fn("=" * 78)

    expected_S = {11: 1, 19: -1, 31: 1, 59: -1, 79: -1}
    all_ok = True
    for p, S_exp in expected_S.items():
        rec = analyze_prime(p)
        ok = (rec["S_p"] == S_exp)
        all_ok = all_ok and ok
        rank_note = "alpha(p)=p-1" if rec["alpha"] == p - 1 else f"alpha(p)={rec['alpha']}"
        log_fn(f"  p={p:3d} : S(p)={rec['S_p']:+d} (expected {S_exp:+d})  "
               f"[{rank_note}, signature={rec['signature']}, p mod 20={rec['mod20']}]  "
               f"-> {'OK' if ok else 'MISMATCH'}")

    if all_ok:
        log_fn("\n[OK] self-test PASSED -- all five Appendix-A examples reproduced.")
    else:
        log_fn("\n[!] self-test FAILED.")
    return all_ok


# ============================================================================
#  SECTION 11.  GUI (Tkinter) -- optional, interactive use
# ============================================================================

if _TKINTER_AVAILABLE:

    class FibCharApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title(f"Fibonacci Character-Sum Research Suite v{__version__}")
            self.geometry("1200x840")
            self.msg_queue = queue.Queue()
            self.worker = None
            self.stop_event = threading.Event()
            self._build_ui()
            self.after(100, self._poll_queue)

        def _build_ui(self):
            top = ttk.Frame(self, padding=8)
            top.pack(fill="x")
            ttk.Label(top, text="N_MAX:").pack(side="left")
            self.n_var = tk.StringVar(value="500000")
            ttk.Entry(top, textvariable=self.n_var, width=12).pack(side="left", padx=4)

            ttk.Label(top, text="Output folder:").pack(side="left", padx=(12, 0))
            self.dir_var = tk.StringVar(value=os.path.abspath("FibChar_Output"))
            ttk.Entry(top, textvariable=self.dir_var, width=38).pack(side="left", padx=4)
            ttk.Button(top, text="Browse...", command=self._pick_dir).pack(side="left")

            self.run_btn = ttk.Button(top, text="\u25B6 Run", command=self._on_run)
            self.run_btn.pack(side="left", padx=(12, 2))
            self.stop_btn = ttk.Button(top, text="\u25A0 Stop & Checkpoint", command=self._on_stop, state="disabled")
            self.stop_btn.pack(side="left", padx=2)
            ttk.Button(top, text="\U0001F9EA Self-test", command=self._on_self_test).pack(side="left", padx=(12, 2))

            th = ttk.Frame(self, padding=(8, 0, 8, 4))
            th.pack(fill="x")
            ttk.Label(th, text="Backend thresholds \u2014 array < ").pack(side="left")
            self.th_arr = tk.StringVar(value=str(TH_ARRAY_DEFAULT))
            ttk.Entry(th, textvariable=self.th_arr, width=12).pack(side="left")
            ttk.Label(th, text="  bitwise < ").pack(side="left")
            self.th_bw = tk.StringVar(value=str(TH_BITWISE_DEFAULT))
            ttk.Entry(th, textvariable=self.th_bw, width=12).pack(side="left")
            ttk.Label(th, text="  (pow used above)").pack(side="left")

            pr = ttk.Frame(self, padding=(8, 0, 8, 4))
            pr.pack(fill="x")
            self.prog = ttk.Progressbar(pr, length=200, mode="determinate", maximum=100)
            self.prog.pack(fill="x", side="left", expand=True)
            self.pct_lbl = ttk.Label(pr, text=" 0.0%")
            self.pct_lbl.pack(side="left", padx=6)

            tb = ttk.Frame(self, padding=(8, 0, 8, 2))
            tb.pack(fill="x")
            ttk.Label(tb, text="Log / Report").pack(side="left")
            ttk.Button(tb, text="\U0001F4CB Copy all", command=self._copy_all).pack(side="right", padx=2)
            ttk.Button(tb, text="\U0001F4CB Copy selection", command=self._copy_selection).pack(side="right", padx=2)
            ttk.Button(tb, text="\U0001F4BE Save as .txt", command=self._save_log_txt).pack(side="right", padx=2)
            ttk.Button(tb, text="Clear", command=lambda: self.log.delete("1.0", "end")).pack(side="right", padx=2)

            body = ttk.Frame(self, padding=(8, 0, 8, 4))
            body.pack(fill="both", expand=True)
            self.log = scrolledtext.ScrolledText(body, font=("Consolas", 10), wrap="none", undo=False)
            self.log.pack(fill="both", expand=True)
            self._install_log_context_menu()
            self.log.bind("<Control-a>", lambda e: (self.log.tag_add("sel", "1.0", "end"), "break"))

            bar = ttk.Frame(self, padding=(8, 0, 8, 8))
            bar.pack(fill="x")
            ttk.Label(bar, text=("Numba: " + ("ON \u2713" if HAS_NUMBA else "OFF"))).pack(side="left")
            ttk.Label(bar, text=f"  v{__version__}").pack(side="left")
            self.status_lbl = ttk.Label(bar, text="idle.")
            self.status_lbl.pack(side="right")

        def _install_log_context_menu(self):
            menu = tk.Menu(self.log, tearoff=0)
            menu.add_command(label="Copy selection", command=self._copy_selection)
            menu.add_command(label="Copy all", command=self._copy_all)
            menu.add_separator()
            menu.add_command(label="Select all", command=lambda: self.log.tag_add("sel", "1.0", "end"))
            menu.add_command(label="Save as .txt...", command=self._save_log_txt)

            def show(e):
                try:
                    menu.tk_popup(e.x_root, e.y_root)
                finally:
                    menu.grab_release()

            for seq in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
                self.log.bind(seq, show)

        def _copy_selection(self):
            try:
                text = self.log.get("sel.first", "sel.last")
            except tk.TclError:
                text = ""
            if text:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.status_lbl.configure(text="selection copied.")
            else:
                self.status_lbl.configure(text="no selection.")

        def _copy_all(self):
            text = self.log.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status_lbl.configure(text=f"copied {len(text)} chars.")

        def _save_log_txt(self):
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All", "*.*")],
                initialfile="fib_char_log.txt")
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log.get("1.0", "end-1c"))
            self.status_lbl.configure(text=f"saved -> {path}")

        def _pick_dir(self):
            d = filedialog.askdirectory(initialdir=self.dir_var.get())
            if d:
                self.dir_var.set(d)

        def _log(self, m):
            self.msg_queue.put(("log", m))

        def _progress(self, f):
            self.msg_queue.put(("prog", f))

        def _poll_queue(self):
            try:
                while True:
                    kind, payload = self.msg_queue.get_nowait()
                    if kind == "log":
                        self.log.insert("end", payload + "\n")
                        self.log.see("end")
                    elif kind == "prog":
                        p = max(0.0, min(1.0, float(payload))) * 100
                        self.prog["value"] = p
                        self.pct_lbl.configure(text=f" {p:5.1f}%")
                    elif kind == "done":
                        self.run_btn.configure(state="normal")
                        self.stop_btn.configure(state="disabled")
                        self.status_lbl.configure(text=payload or "idle.")
            except queue.Empty:
                pass
            self.after(100, self._poll_queue)

        def _on_self_test(self):
            self.log.insert("end", "\n")
            run_self_test(log_fn=self._log_sync)
            self.log.see("end")

        def _log_sync(self, m):
            self.log.insert("end", m + "\n")

        def _on_run(self):
            try:
                N = int(self.n_var.get())
                assert N >= 10
                th_a = int(self.th_arr.get())
                th_b = int(self.th_bw.get())
                assert 0 < th_a <= th_b
            except Exception:
                messagebox.showerror("Invalid input", "N_MAX >= 10  and  0 < th_array <= th_bitwise required.")
                return

            out_dir = self.dir_var.get().strip() or "FibChar_Output"
            resume_payload = None
            ckpt = load_checkpoint(out_dir, N)
            if ckpt is not None:
                cdf, meta = ckpt
                ans = messagebox.askyesnocancel(
                    "Checkpoint found",
                    f"Checkpoint for N_MAX = {N}:\n\n"
                    f"  progress : {meta['last_index']}/{meta['total_primes']}"
                    f"  ({100*meta['last_index']/max(meta['total_primes'],1):.1f}%)\n"
                    f"  saved at : {meta.get('timestamp','?')}\n"
                    f"  elapsed  : {meta.get('elapsed_sec',0.0):.0f} s\n\n"
                    "Yes = RESUME   No = FRESH   Cancel = do nothing")
                if ans is None:
                    return
                if ans:
                    resume_payload = (cdf, meta)
                else:
                    delete_checkpoint(out_dir, N)

            self.stop_event.clear()
            self.run_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.status_lbl.configure(text="running ...")
            self.log.delete("1.0", "end")
            self.prog["value"] = 0
            self.pct_lbl.configure(text=" 0.0%")

            self.worker = threading.Thread(
                target=self._run_pipeline,
                args=(N, out_dir, resume_payload, th_a, th_b),
                daemon=True)
            self.worker.start()

        def _on_stop(self):
            if self.worker and self.worker.is_alive():
                self.stop_event.set()
                self._log("[!] STOP requested ...")
                self.stop_btn.configure(state="disabled")
                self.status_lbl.configure(text="stopping ...")

        def _run_pipeline(self, N, out_dir, resume_payload, th_a, th_b):
            try:
                self._log(f"[+] starting FibChar v{__version__}, N_MAX = {N}")
                self._log(f"[+] checkpoint every {CHECKPOINT_EVERY} primes")
                kwargs = dict(out_dir=out_dir, log_fn=self._log,
                               progress_fn=self._progress,
                               th_array=th_a, th_bitwise=th_b,
                               stop_event=self.stop_event)
                if resume_payload is None:
                    df = build_database(N, **kwargs)
                else:
                    cdf, meta = resume_payload
                    df = build_database(N, resume_df=cdf, resume_meta=meta, **kwargs)

                if df is None:
                    self.msg_queue.put(("done", "stopped (checkpoint saved)."))
                    return

                self._log("[+] computing diagnostic tables ...")
                tables, *_ = compute_all_tables(df)
                self._log("[+] verifying all empirical claims E1-E10 ...")
                empirical_results = verify_all_empirical_claims(df, log_fn=self._log)
                tables["17_empirical_claims_E1_to_E10"] = empirical_results

                self._log("[+] verifying Corollary B1 / Main Theorem ...")
                b1_result, b1_failures = verify_corollary_B1(df, log_fn=self._log)
                tables["16_corollary_B1_verification"] = b1_result
                if len(b1_failures):
                    tables["16b_corollary_B1_failures"] = b1_failures

                report = format_tables_for_log(tables, len(df), len(df[~df["p"].isin([2, 5])]))
                self._log("\n" + report)

                save_outputs(df, tables, report, out_dir, N, self._log)

                try:
                    b1_result.to_csv(os.path.join(out_dir, "corollary_B1_verification.csv"), index=False)
                    self._log("[+] saved B1 CSV -> corollary_B1_verification.csv")
                except Exception as e:
                    self._log(f"[!] B1 CSV save failed ({e})")

                export_latex_tables(tables, out_dir)
                delete_checkpoint(out_dir, N)
                self._log("[+] DONE. Checkpoint removed.")
                self.msg_queue.put(("done", "done."))
            except Exception as e:
                import traceback
                self._log(f"[!] ERROR: {e!r}\n" + traceback.format_exc())
                self.msg_queue.put(("done", "error."))

else:
    FibCharApp = None  # GUI unavailable; CLI / --no-gui still fully functional.


# ============================================================================
#  SECTION 12.  CLI ENTRY POINT
# ============================================================================

def main_cli():
    parser = argparse.ArgumentParser(
        description=f"Fibonacci Character-Sum Research Suite v{__version__} "
                     f"-- reproducibility code for the JNT paper "
                     f"'A Fibonacci Character Sum Identity for Primes of Full Rank of Apparition'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples
--------
  # Reproduce the paper's N = 10^6 run (Tables 1-16 + Corollary B1):
      %(prog)s --no-gui --N 1000000 --verify-b1

  # Same, but multi-process (no checkpointing):
      %(prog)s --no-gui --N 1000000 --verify-b1 --parallel --workers 8

  # Instant self-test (Appendix A examples), then exit:
      %(prog)s --self-test

  # Resume a previously interrupted sequential run:
      %(prog)s --no-gui --N 1000000 --verify-b1 --resume

  # Launch the interactive GUI (checkpoint/resume, live log):
      %(prog)s
""")
    parser.add_argument("--N", type=int, default=10 ** 6, help="upper bound for primes (paper uses 10^6)")
    parser.add_argument("--out", type=str, default="FibChar_Output", help="output directory")
    parser.add_argument("--resume", action="store_true", help="resume from latest checkpoint (sequential mode only)")
    parser.add_argument("--fresh", action="store_true", help="ignore checkpoint and start fresh")
    parser.add_argument("--th-array", type=int, default=TH_ARRAY_DEFAULT, help="threshold for QR-table backend")
    parser.add_argument("--th-bitwise", type=int, default=TH_BITWISE_DEFAULT, help="threshold for bitwise-Jacobi backend")
    parser.add_argument("--verify-b1", action="store_true", help="run Corollary B1 / Main Theorem verification")
    parser.add_argument("--self-test", action="store_true", help="run quick self-test (Appendix A examples) and exit")
    parser.add_argument("--parallel", action="store_true", help="use the multi-process pipeline (no checkpoint/resume)")
    parser.add_argument("--workers", type=int, default=max((os.cpu_count() or 2) - 1, 1),
                         help="worker processes for --parallel")
    parser.add_argument("--chunk-size", type=int, default=5000, help="primes per chunk for --parallel")
    parser.add_argument("--no-gui", action="store_true", help="run headless (required where Tkinter is unavailable)")
    parser.add_argument("--version", action="version", version=f"FibChar v{__version__}")
    args = parser.parse_args()

    if args.self_test:
        ok = run_self_test(log_fn=print)
        raise SystemExit(0 if ok else 1)

    if 0 < args.th_array <= args.th_bitwise:
        pass
    else:
        raise SystemExit("error: require 0 < --th-array <= --th-bitwise")

    if args.no_gui or not _TKINTER_AVAILABLE:
        os.makedirs(args.out, exist_ok=True)

        if HAS_NUMBA:
            print("[+] warming JIT (all 3 backends) ...")
            _ = core_walk_array(7)
            _ = core_walk_bitwise(7)
            _ = core_walk_pow(7)

        if args.parallel:
            if args.resume:
                print("[!] --resume is ignored in --parallel mode (no checkpointing for this path).")
            primes = sieve_primes(args.N)
            print(f"[+] primes <= {args.N} : {len(primes)}  "
                  f"(parallel, workers={args.workers}, chunk_size={args.chunk_size})")
            t0 = time.time()
            df = build_database_parallel(primes, args.workers, args.chunk_size,
                                           args.th_array, args.th_bitwise)
            print(f"[+] parallel compute finished ({time.time()-t0:.1f}s, {len(df)} rows)")
        else:
            resume_payload = None
            if args.fresh:
                delete_checkpoint(args.out, args.N)
            elif args.resume:
                ckpt = load_checkpoint(args.out, args.N)
                if ckpt is not None:
                    resume_payload = ckpt
                    print(f"[+] resuming from checkpoint (last_index={ckpt[1].get('last_index')})")
                else:
                    print("[!] --resume requested but no checkpoint found; starting fresh.")

            kwargs = dict(out_dir=args.out, log_fn=print, progress_fn=lambda x: None,
                           th_array=args.th_array, th_bitwise=args.th_bitwise)
            if resume_payload is None:
                df = build_database(args.N, **kwargs)
            else:
                cdf, meta = resume_payload
                df = build_database(args.N, resume_df=cdf, resume_meta=meta, **kwargs)

            if df is None:
                # only reachable if a stop_event were set; not used in headless CLI
                return

        tables, *_ = compute_all_tables(df)
        if args.verify_b1:
            # also verify all E1-E10 claims while we're at it
            empirical_results = verify_all_empirical_claims(df, log_fn=print)
            tables["17_empirical_claims_E1_to_E10"] = empirical_results
            empirical_results.to_csv(
                os.path.join(args.out, "empirical_claims_E1_to_E10.csv"),
                index=False,
            )
            print("[+] saved -> empirical_claims_E1_to_E10.csv")

        if args.verify_b1:
            b1_result, b1_failures = verify_corollary_B1(df, log_fn=print)
            tables["16_corollary_B1_verification"] = b1_result
            if len(b1_failures):
                tables["16b_corollary_B1_failures"] = b1_failures
            b1_result.to_csv(os.path.join(args.out, "corollary_B1_verification.csv"), index=False)
            print("[+] saved B1 CSV -> corollary_B1_verification.csv")

        report = format_tables_for_log(tables, len(df), len(df[~df["p"].isin([2, 5])]))
        print("\n" + report)
        save_outputs(df, tables, report, args.out, args.N, print)
        export_latex_tables(tables, args.out)

        if not args.parallel:
            delete_checkpoint(args.out, args.N)
    else:
        app = FibCharApp()
        app.mainloop()


if __name__ == "__main__":
    main_cli()
  

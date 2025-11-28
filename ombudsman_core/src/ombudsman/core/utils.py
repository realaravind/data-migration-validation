import hashlib
import math

def hash_row(row):
    s = "|".join([str(x) for x in row])
    return hashlib.md5(s.encode()).hexdigest()

def within_tolerance(val1, val2, abs_tol=0, pct_tol=0):
    if val1 is None or val2 is None:
        return False
    if abs(val1 - val2) <= abs_tol:
        return True
    pct = abs(val1 - val2) / max(abs(val1), 1)
    return pct * 100 <= pct_tol

def diff_lists(a, b):
    return list(set(a) - set(b)), list(set(b) - set(a))
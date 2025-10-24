import numpy as np

def sma(arr, n):
    arr = np.asarray(arr, float)
    out = np.full_like(arr, np.nan, dtype=float)
    if n<=0: return out
    cs = np.cumsum(np.insert(arr,0,0))
    out[n-1:] = (cs[n:] - cs[:-n]) / n
    return out

def rsi(arr, n=14):
    arr = np.asarray(arr, float)
    L = len(arr)
    out = np.full(L, np.nan)
    if L<n: return out
    diff = np.diff(arr)
    up = np.where(diff>0, diff, 0)
    dn = np.where(diff<0, -diff, 0)
    avg_up = np.zeros(L-1); avg_dn = np.zeros(L-1)
    avg_up[n-1] = up[:n].mean(); avg_dn[n-1] = dn[:n].mean()
    alpha=1/n
    for i in range(n, L-1):
        avg_up[i] = (1-alpha)*avg_up[i-1] + alpha*up[i]
        avg_dn[i] = (1-alpha)*avg_dn[i-1] + alpha*dn[i]
    rs = avg_up/np.where(avg_dn==0, np.nan, avg_dn)
    out[1:] = 100 - 100/(1+rs)
    return out

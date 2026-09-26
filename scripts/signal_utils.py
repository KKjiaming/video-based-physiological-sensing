"""Numerical signal processing; no neural model dependency."""
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
from scipy import signal, sparse
from scipy.sparse.linalg import spsolve

def detrend(x, lam=100):
    n = len(x)
    d = sparse.diags([np.ones(n-2), -2*np.ones(n-2), np.ones(n-2)], [0,1,2], shape=(n-2,n), format='csc')
    return x - spsolve(sparse.eye(n, format='csc') + lam**2 * (d.T @ d), x)

def postprocess(raw, fs, band, lam, order):
    integrated = np.cumsum(raw, dtype=np.float64)
    det = detrend(integrated, lam)
    b,a = signal.butter(order, band, btype='bandpass', fs=fs)
    return integrated, det, signal.filtfilt(b,a,det)

def spectral_rate(x, fs, band):
    f,p = signal.periodogram(x,fs=fs,window='hann',detrend='constant',nfft=len(x))
    inside = (f>=band[0]) & (f<=band[1])
    if not np.any(inside) or np.max(p[inside])<=0:
        raise ValueError('No nonzero in-band spectral power')
    k = np.flatnonzero(inside)[np.argmax(p[inside])]
    return float(60*f[k]),f,p

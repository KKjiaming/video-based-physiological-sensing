"""Synthetic numerical checks only: these are not physiological experiments."""
import json
import numpy as np
from scipy.sparse import spdiags
from signal_utils import ROOT,detrend,spectral_rate

def main():
    rng=np.random.default_rng(2026)
    x=rng.normal(size=120)
    h=np.eye(len(x));d=spdiags(np.array([np.ones(len(x)),-2*np.ones(len(x)),np.ones(len(x))]),[0,1,2],len(x)-2,len(x)).toarray()
    reference=(h-np.linalg.inv(h+100**2*d.T@d))@x
    error=float(np.max(np.abs(reference-detrend(x))))
    assert error<1e-9,error
    fs=30;t=np.arange(1800)/fs
    checks={}
    for name,hz,band in [('pulse',1.2,[.75,2.5]),('resp',.25,[.08,.5])]:
        rate,_,_=spectral_rate(np.sin(2*np.pi*hz*t),fs,band)
        assert abs(rate-60*hz)<1e-10
        checks[name+'_synthetic_rate_per_min']=rate
    result={'kind':'synthetic_software_check_only','sparse_dense_detrend_max_abs_error':error,**checks,'passed':True}
    (ROOT/'results/signal_math_check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()

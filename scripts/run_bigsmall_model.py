"""Strict CPU-only BigSmall audit/inference. No trainer or optimizer is imported."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
torch.set_num_threads(4)
torch.set_num_interop_threads(2)

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def load_weights(model,path):
    state=torch.load(path,map_location='cpu',weights_only=True)
    if all(k.startswith('module.') for k in state):state={k[7:]:v for k,v in state.items()}
    model.load_state_dict(state,strict=True)
    assert set(state)==set(model.state_dict())
    assert all(torch.equal(v,model.state_dict()[k]) for k,v in state.items())
    return state

def build():
    mod=module(ROOT/'third_party/rPPG-Toolbox/neural_methods/model/BigSmall.py','bigsmall_toolbox')
    model=mod.BigSmall(n_segment=3)
    weight=ROOT/'third_party/rPPG-Toolbox/final_model_release/BP4D_BigSmall_Multitask_Fold1.pth'
    state=load_weights(model,weight);model.eval()
    return model,weight,state

def audit():
    model,weight,state=build()
    torch.manual_seed(2026)
    big=torch.randn(6,3,144,144);small=torch.randn(6,3,9,9)
    with torch.inference_mode():ys=model([big,small])
    assert [list(y.shape) for y in ys]==[[6,12],[6,1],[6,1]]
    assert all(torch.isfinite(y).all() for y in ys)
    report={'kind':'software_check_only','torch':torch.__version__,'device':'cpu','strict_load':'passed',
            'all_named_weights_match':True,'parameters':sum(p.numel() for p in model.parameters()),
            'input_shapes':[list(big.shape),list(small.shape)],'output_shapes':[list(y.shape) for y in ys],
            'outputs':['AU logits (not interpreted)','pulse difference','respiration difference'],
            'weight_sha256':hashlib.sha256(weight.read_bytes()).hexdigest(),'tensor_count':len(state)}
    original_path=ROOT/'third_party/BigSmall/code/pretrained_models/BP4D_BigSmall_Multitask_Clip3_Split1_Epoch4.pth'
    original_mod=module(ROOT/'third_party/BigSmall/code/neural_methods/model/BigSmall_models.py','bigsmall_original')
    original=original_mod.BigSmallSlowFastWTSM(n_segment=3)
    original_state=load_weights(original,original_path);original.eval()
    with torch.inference_mode():oy=original([big,small])
    report['original_repo']={'strict_load':'passed','weight_sha256':hashlib.sha256(original_path.read_bytes()).hexdigest(),
                             'output_shapes':[list(y.shape) for y in oy],
                             'all_finite':all(bool(torch.isfinite(y).all()) for y in oy)}
    report['original_vs_toolbox_tensor_max_abs_difference']=max(float(torch.max(abs(v-state[k]))) for k,v in original_state.items()) if set(original_state)==set(state) else None
    report['original_vs_toolbox_output_max_abs_difference']=max(float(torch.max(abs(a-b))) for a,b in zip(oy,ys))
    (ROOT/'results/bigsmall_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

def infer(inputs,output):
    data=np.load(inputs);model,weight,_=build()
    big=torch.from_numpy(data['big']).float();small=torch.from_numpy(data['small']).float()
    if len(big)%3 or len(big)!=len(small):raise ValueError('Expected equal inputs and complete 3-frame chunks')
    start=time.perf_counter();ys=[]
    with torch.inference_mode():
        for k in range(0,len(big),30):ys.append(model([big[k:k+30],small[k:k+30]]))
    elapsed=time.perf_counter()-start
    arrays=[torch.cat([y[j] for y in ys]).numpy() for j in range(3)]
    if not all(np.isfinite(x).all() for x in arrays):raise ValueError('Nonfinite outputs')
    np.savez_compressed(output,au_logits_uninterpreted=arrays[0],pulse_raw_difference=arrays[1].ravel(),resp_raw_difference=arrays[2].ravel())
    output.with_suffix('.json').write_text(json.dumps({'torch':torch.__version__,'device':'cpu','prediction_time_s':elapsed,'weight_sha256':hashlib.sha256(weight.read_bytes()).hexdigest(),'model_source_sha256':hashlib.sha256((ROOT/'third_party/rPPG-Toolbox/neural_methods/model/BigSmall.py').read_bytes()).hexdigest()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.inputs:
        if not a.output:p.error('--output is required with --inputs')
        infer(a.inputs,a.output)
    else:audit()

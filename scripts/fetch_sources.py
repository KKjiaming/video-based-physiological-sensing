"""Fetch only recorded official repository versions and the small demo video."""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def main():
    sources=json.loads((ROOT/'configs/sources.json').read_text())
    for name,entry in sources.items():
        dest=ROOT/'third_party'/name
        if not dest.exists():
            dest.mkdir(parents=True)
            subprocess.run(['git','init',str(dest)],check=True)
            subprocess.run(['git','-C',str(dest),'remote','add','origin',entry['url']],check=True)
            fetch=['git','-C',str(dest),'fetch','--depth','1']
            if entry.get('sparse_paths'):
                subprocess.run(['git','-C',str(dest),'config','remote.origin.promisor','true'],check=True)
                subprocess.run(['git','-C',str(dest),'config','remote.origin.partialclonefilter','blob:none'],check=True)
                fetch.append('--filter=blob:none')
                subprocess.run(['git','-C',str(dest),'config','core.sparseCheckout','true'],check=True)
                (dest/'.git/info/sparse-checkout').write_text('\n'.join(entry['sparse_paths'])+'\n')
            subprocess.run(fetch+['origin',entry['commit']],check=True)
            subprocess.run(['git','-C',str(dest),'checkout','--detach','FETCH_HEAD'],check=True)
        actual=subprocess.check_output(['git','-C',str(dest),'rev-parse','HEAD'],text=True).strip()
        if actual!=entry['commit']:raise RuntimeError(f'{name}: existing checkout differs; refusing to overwrite')
        if 'weight_sha256' in entry:
            digest=hashlib.sha256((dest/entry['weight']).read_bytes()).hexdigest()
            if digest!=entry['weight_sha256']:raise RuntimeError(f'{name}: weight hash mismatch')
    data=ROOT/'data';data.mkdir(exist_ok=True)
    video=data/'mit_face.mp4'
    if not video.exists():
        url='https://people.csail.mit.edu/mrub/evm/video/face.mp4'
        with urllib.request.urlopen(url,timeout=60) as r:
            payload=r.read(2_000_001)
        if len(payload)!=1_639_646:raise RuntimeError('Unexpected video size; inspect source before proceeding')
        video.write_bytes(payload)
    manifest=ROOT/'configs/data_source.json'
    if manifest.exists():
        expected=json.loads(manifest.read_text())['sha256']
        if hashlib.sha256(video.read_bytes()).hexdigest()!=expected:raise RuntimeError('Video hash mismatch')
    print('Recorded source commits, available weight hashes and video verified.')

if __name__=='__main__':main()

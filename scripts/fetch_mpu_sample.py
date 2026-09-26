"""Download one author-published MPU sample (128MB), not the full dataset."""
from pathlib import Path
import urllib.request,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
FILES=[(55553414,'ppg.csv',700580,'0e9a50efa2ff6500716218171c28ca4e'),(55553417,'video.mp4',127996277,'f179978e6c2d3c10b65920a551977497')]
def main():
    out=ROOT/'data/mpu_sample';out.mkdir(exist_ok=True)
    records=[]
    for fid,name,size,md5 in FILES:
        p=out/name;url=f'https://ndownloader.figshare.com/files/{fid}'
        if not p.exists() or p.stat().st_size!=size:
            response=urllib.request.urlopen(url,timeout=60);partial=p.with_suffix(p.suffix+'.part');total=0
            with partial.open('wb') as f:
                while True:
                    b=response.read(4*1024*1024)
                    if not b:break
                    total+=len(b)
                    if total>size:raise RuntimeError('Declared size exceeded')
                    f.write(b)
            if total!=size:raise RuntimeError('Incomplete download')
            partial.replace(p)
        assert hashlib.md5(p.read_bytes()).hexdigest()==md5
        records.append({'url':url,'path':str(p.relative_to(ROOT)),'bytes':size,'publisher_md5':md5,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (ROOT/'results/gt_search/mpu_download_manifest.json').write_text(json.dumps(records,indent=2));print('MPU files verified')
if __name__=='__main__':main()

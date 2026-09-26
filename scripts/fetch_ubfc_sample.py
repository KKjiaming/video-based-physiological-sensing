"""Fetch only author-hosted UBFC DATASET_2 subject3; no accounts or data application."""
from pathlib import Path
import hashlib,json,urllib.request,urllib.parse,time
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
def open_url(url):
    for attempt in range(4):
        try:return urllib.request.urlopen(url,timeout=60)
        except (OSError,urllib.error.URLError):
            if attempt==3:raise
            time.sleep(2)

class DownloadForm(HTMLParser):
    def __init__(self):super().__init__();self.action=None;self.fields={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='form' and a.get('id')=='download-form':self.action=a['action']
        if tag=='input' and a.get('type')=='hidden':self.fields[a['name']]=a['value']
def fetch(file_id,path,expected_size):
    if path.exists() and path.stat().st_size==expected_size:return
    response=open_url('https://drive.google.com/uc?'+urllib.parse.urlencode({'export':'download','id':file_id}))
    if 'text/html' in response.headers.get('Content-Type',''):
        page=response.read().decode();form=DownloadForm();form.feed(page)
        if not form.action or not form.action.startswith('https://drive.usercontent.google.com/download'):raise RuntimeError('Not a public download form')
        # Google large-file / executable virus-scan notice, not a data licence application.
        response=open_url(form.action+'?'+urllib.parse.urlencode(form.fields))
    if 'text/html' in response.headers.get('Content-Type',''):
        page=response.read().decode();(ROOT/'results/gt_search/last_download_error.html').write_text(page)
        raise RuntimeError('Quota or download error; see last_download_error.html')
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.part');total=0
    with temp.open('wb') as f:
        while True:
            chunk=response.read(4*1024*1024)
            if not chunk:break
            total+=len(chunk)
            if total>expected_size:raise RuntimeError('Exceeded declared size')
            f.write(chunk)
            if total//(100*1024*1024)!=(total-len(chunk))//(100*1024*1024):print(f'{path.name}: {total/1e6:.0f} MB',flush=True)
    if total!=expected_size:raise RuntimeError(f'Size mismatch {total} vs {expected_size}')
    temp.replace(path)
def main():
    entries=[('1tKRzecjw14TGFkizo4XvMEWXeefriiCH','data/ubfc_subject3/ground_truth.txt',86454),('12jym67QYPnXHp3qSRjf1XsQGWRrC284M','results/gt_search/ubfc_official_processor.py',5987),('1tL5EX50qFD8n6VO0wX9x_iOrPKyVR2-W','data/ubfc_subject3/vid.avi',1659925096)]
    records=[]
    for id,name,size in entries:
        p=ROOT/name;fetch(id,p,size)
        digest=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(4*1024*1024),b''):digest.update(block)
        records.append({'official_drive_file_id':id,'path':name,'bytes':size,'sha256':digest.hexdigest()})
    (ROOT/'results/gt_search/ubfc_download_manifest.json').write_text(json.dumps(records,indent=2))
    print('Official subject3 sample downloaded and hashed.',flush=True)
if __name__=='__main__':main()

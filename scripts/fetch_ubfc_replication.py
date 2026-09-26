"""Fetch only the frozen official sample list; preserve originals and record failures."""
from pathlib import Path
import codecs,concurrent.futures,hashlib,json,re,urllib.request,urllib.parse,urllib.error
from fetch_ubfc_sample import DownloadForm
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/ubfc_replication'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def fetch(entry):
    subject,name,ident,size=entry
    dest=ROOT/f'data/ubfc_{subject}'/name
    record={'subject':subject,'name':name,'file_id':ident,'expected_bytes':size,'path':str(dest.relative_to(ROOT)), 'url':f'https://drive.google.com/file/d/{ident}/view'}
    try:
        if dest.exists():
            if dest.stat().st_size!=size:raise ValueError('Existing file size differs; left unchanged')
            record.update(status='present',sha256=sha(dest));return record
        url='https://drive.google.com/uc?'+urllib.parse.urlencode({'export':'download','id':ident})
        response=urllib.request.urlopen(url,timeout=45)
        if 'text/html' in response.headers.get('Content-Type',''):
            page=response.read().decode();form=DownloadForm();form.feed(page)
            (OUT/f'{subject}_{name}_initial.html').write_text(page)
            if not form.action or not form.action.startswith('https://drive.usercontent.google.com/download'):raise RuntimeError('No public download form')
            response=urllib.request.urlopen(form.action+'?'+urllib.parse.urlencode(form.fields),timeout=45)
        if 'text/html' in response.headers.get('Content-Type',''):
            page=response.read().decode();(OUT/f'{subject}_{name}_error.html').write_text(page)
            raise RuntimeError('Google returned HTML instead of file; see saved response')
        temp=dest.with_suffix(dest.suffix+'.part');total=0
        with temp.open('wb') as f:
            while True:
                b=response.read(4*1024*1024)
                if not b:break
                total+=len(b)
                if total>size:raise RuntimeError('Response exceeds declared size')
                f.write(b)
                if total//(100*1024*1024)!=(total-len(b))//(100*1024*1024):print(subject,name,total,flush=True)
        if total!=size:raise RuntimeError(f'Incomplete download: {total}/{size}')
        temp.replace(dest);record.update(status='downloaded',sha256=sha(dest))
    except Exception as e:
        record.update(status='download_failed',error=f'{type(e).__name__}: {e}')
        if isinstance(e,urllib.error.HTTPError):
            page=e.read().decode(errors='replace');(OUT/f'{subject}_{name}_error.html').write_text(page)
            if 'quota' in page.lower():record['reason']='Google download quota exceeded'
    print(json.dumps(record),flush=True)
    return record

def main():
    lock=json.loads((OUT/'protocol_lock.json').read_text());assert sha(ROOT/lock['file'])==lock['sha256']
    cfg=json.loads((ROOT/lock['file']).read_text());entries=[]
    for item in cfg['subjects']:
        page=(OUT/(item['id']+'_folder.html')).read_text()
        raw=re.search(r"window\['_DRIVE_ivd'\] = '(.*?)';",page).group(1)
        # The public folder's serialized array is ASCII JavaScript escape notation.
        decoded=re.sub(r'\\x([0-9a-fA-F]{2})',lambda m:chr(int(m.group(1),16)),raw).replace('\\/','/')
        arr=json.loads(decoded)
        for row in arr[0]:
            if row[2] in ['ground_truth.txt','vid.avi']:entries.append((item['id'],row[2],row[0],row[13]))
    (OUT/'download_plan.json').write_text(json.dumps(entries,indent=2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:records=list(ex.map(fetch,entries))
    (OUT/'download_status.json').write_text(json.dumps(records,indent=2))
    print('Finished download attempts',flush=True)
if __name__=='__main__':main()

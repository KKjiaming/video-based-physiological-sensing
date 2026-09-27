"""Read-only check of the Git publication candidate set; never stage, commit or push."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def candidates():
    return sorted(set(x.decode() for x in git('ls-files','--cached','--others','--exclude-standard','-z').split(b'\0') if x))
def main():
    names=candidates();allowed=set(names);issues=[]
    media=json.loads((ROOT/'configs/publication_media.json').read_text())
    demo_videos={entry['video'] for entry in media['demos']}
    for entry in media['demos']:
        for key in ['video','preview'] + (['animation'] if 'animation' in entry else []):
            if entry[key] not in allowed:issues.append('Selected demo media is ignored: '+entry[key])
    tracked_ignored=git('ls-files','--cached','--ignored','--exclude-standard','-z').split(b'\0')
    issues.extend('Already tracked but now ignored: '+x.decode() for x in tracked_ignored if x)
    patterns=[re.compile(r'gh[pousr]_[A-Za-z0-9]{36,}'),re.compile(r'github_pat_[A-Za-z0-9_]{40,}'),
              re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
              re.compile(r'AKIA[0-9A-Z]{16}')]
    forbidden_suffixes={'.avi','.mp4','.mov','.mkv','.npz','.npy','.pth','.pt','.hdf5','.h5','.ckpt','.safetensors','.response','.xlsx','.log'}
    total=0;largest=[];links=0
    for name in names:
        p=ROOT/name
        if not p.is_file():issues.append('Missing or non-file candidate: '+name);continue
        if p.is_symlink():issues.append('Review symlink before publication: '+name)
        size=p.stat().st_size;total+=size;largest.append((size,name))
        if size>10*1024*1024:issues.append('File exceeds the 10 MiB review threshold: '+name)
        if p.suffix.lower() in forbidden_suffixes and name not in demo_videos:issues.append('Local-artifact file type selected: '+name)
        if p.suffix.lower() in {'.py','.sh','.md','.txt','.json','.csv'} or name=='.gitignore':
            text=p.read_text(errors='replace')
            for pattern in patterns:
                if pattern.search(text):issues.append('Possible credential pattern in: '+name)
            if re.search(r'/(?:data|home)/[a-zA-Z0-9_.-]+/|' + r'file:/' + '/',text):issues.append('Host-specific absolute path in: '+name)
            if p.suffix=='.md':
                for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
                    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):continue
                    target=target.split('#',1)[0]
                    dest=(p.parent/target).resolve()
                    try:rel=str(dest.relative_to(ROOT))
                    except ValueError:issues.append('Link escapes repository in: '+name);continue
                    links+=1
                    if rel not in allowed and not any(x.startswith(rel.rstrip('/')+'/') for x in allowed):
                        issues.append('Non-public Markdown link: '+name+' -> '+rel)
    manifest_path=ROOT/'configs/publication_artifacts.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        for name,record in manifest['artifacts'].items():
            p=ROOT/name
            if name not in allowed:issues.append('Manifest artifact is ignored: '+name)
            elif hashlib.sha256(p.read_bytes()).hexdigest()!=record['sha256']:issues.append('Artifact hash differs: '+name)
    else:issues.append('Missing configs/publication_artifacts.json')
    # Exercise rules without creating sample files or touching the Git index.
    should_ignore=['data/example.csv','results/new_run/ground_truth.csv','results/new_run/preview.jpg',
                   'results/gt_search/video_confirm.response','results/environment_initial.json',
                   'data/ubfc_subject3/vid.avi','results/new_run/video.mp4',
                   'requirements-bigsmall-lock.txt','.venv/lib/example.py','third_party/model/LICENSE',
                   'scripts/.env','scripts/secret.key','configs/credentials.json']
    for name in should_ignore:
        result=subprocess.run(['git','-C',str(ROOT),'check-ignore','--no-index','-v',name],capture_output=True,text=True)
        rule=result.stdout.split('\t',1)[0].split(':',2)[-1] if result.stdout else ''
        if result.returncode!=0 or not rule or rule.startswith('!'):issues.append('Expected ignore rule missing: '+name)
    report={'candidate_files':len(names),'total_bytes':total,'total_mib':round(total/1024**2,3),
            'public_markdown_links_checked':links,'largest_files':[{'bytes':size,'path':name} for size,name in sorted(largest,reverse=True)[:5]],
            'issues':issues,'staged_or_pushed':False}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if issues else 0
if __name__=='__main__':sys.exit(main())

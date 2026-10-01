import json
from test_react_engine import ReactEngine
t=ReactEngine();t.setUp()
def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n.get('children',[]))
for year in (2026,2027):
    for page in ('Fatturato','Costi','Auto','Accantonamenti','Conto economico','Imposte','Detrazioni e deduzioni','Ammortamenti'):
        r=t.render(year,page)
        print(year,page,[n.get('label') for n in walk(r['tree']) if n['kind']=='error'])

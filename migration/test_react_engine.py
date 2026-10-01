import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'web/engine'))
sys.path.insert(0,str(ROOT))
import react_bridge as bridge

class ReactEngine(unittest.TestCase):
    def setUp(self):
        self.tables=json.loads((ROOT/'web/public/demo.json').read_text())
        bridge.state.clear()
    def render(self,year,page,**extra):
        # Browser filesystem has /app; local verification uses same unchanged app.
        original=bridge.__dict__.get('open',open)
        bridge.open=lambda path,*a,**kw: original(ROOT/'app.py' if path=='/app/app.py' else path,*a,**kw)
        return json.loads(bridge.render({'tables':self.tables,'user':{'id':'demo-owner','email':'demo@example.invalid'},'inputs':{'anno_fiscale_selezionato':year,'schede_principali':page},**extra}))
    def test_all_eight_sections_render_for_both_regimes(self):
        for year in (2026,2027):
            for page in ('Fatturato','Costi','Auto','Accantonamenti','Conto economico','Imposte','Detrazioni e deduzioni','Ammortamenti'):
                with self.subTest(year=year,page=page):
                    result=self.render(year,page)
                    self.assertTrue(result['tree'])
                    self.assertEqual(result['mutations'],[])
                    def errors(nodes):
                        return [n['label'] for n in nodes if n['kind']=='error'] + [message for n in nodes for message in errors(n['children'])]
                    self.assertEqual(errors(result['tree']),[])
    def test_residue_reuses_original_decimal_formula(self):
        from decimal import Decimal as D
        from accantonamenti_confronto import ripartisci_residuo
        r=ripartisci_residuo(D('11000'),D('4800'),8)
        self.assertEqual(r['quota_mensile'],D('1550'))
    def test_state_cleared_when_owner_changes(self):
        self.render(2026,'Fatturato')
        bridge.state['private']='sensitive'
        bridge.render({'tables':{**self.tables,'fiscal_years':[]},'user':{'id':'other-owner','email':'other@example.invalid'},'inputs':{}})
        self.assertNotIn('private',bridge.state)

if __name__=='__main__':unittest.main()

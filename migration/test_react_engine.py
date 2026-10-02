import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'web/engine'))
sys.path.insert(0,str(ROOT))
import react_bridge as bridge

class ReactEngine(unittest.TestCase):
    def test_revenue_replacement_zero_and_closed_year(self):
        def flatten(nodes):
            return [item for n in nodes for item in [n, *flatten(n['children'])]]
        initial=self.render(2026,'Fatturato')
        name=self.tables['principals'][0]['name']
        values={**initial['inputs'],'fatturato_mandante':name,'fatturato_mese':'Gennaio'}
        view=self.render(2026,'Fatturato',inputs=values)
        nodes=flatten(view['tree'])
        field=next(n for n in nodes if n.get('label')=='Importo fatturato (IVA esclusa)')
        submit=next(n for n in nodes if n.get('label')=='Salva importo')
        values={**view['inputs'],field['key']:'0'}
        saved=self.render(2026,'Fatturato',inputs=values,event=submit['key'])
        self.assertEqual(len(saved['mutations']),1)
        mutation=saved['mutations'][0]
        self.assertEqual(mutation['operation'],'update')
        self.assertEqual(mutation['payload']['amount'],'0.00')
        self.assertIn(['amount','4500.00'],mutation['filters'])
        fy=next(f for f in self.tables['fiscal_years'] if f['fiscal_year']==2026)
        fy['status']='closed'
        closed=self.render(2026,'Fatturato',inputs=values,event=submit['key'])
        self.assertEqual(closed['mutations'],[])
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
    def test_planned_asset_preserves_payload_and_clears_submitted_form(self):
        def flatten(nodes):
            return [item for n in nodes for item in [n, *flatten(n['children'])]]
        initial=self.render(2027,'Ammortamenti')
        values=initial['inputs']
        radio=next(n for n in flatten(initial['tree']) if n.get('label')=='Tipo di inserimento')
        values[radio['key']]='Previsto'
        planned=self.render(2027,'Ammortamenti',inputs=values)
        nodes=flatten(planned['tree'])
        values=planned['inputs']
        fields={'Descrizione bene':'SYNTHETIC FORM RESET', 'Esborso lordo previsto (€)':'1000', 'Coefficiente ammortamento (%) · solo se costo fiscale > 516,46 €':'20', 'Confermo importi, IVA, classificazione e coefficiente quando necessario':True}
        keys={}
        for label,value in fields.items():
            item=next(n for n in nodes if n.get('label')==label)
            values[item['key']]=value
            keys[label]=item['key']
        submit=next(n for n in nodes if n.get('label')=='Salva bene')['key']
        saved=self.render(2027,'Ammortamenti',inputs=values,event=submit)
        self.assertEqual(len(saved['mutations']),1)
        payload=saved['mutations'][0]['payload']
        self.assertEqual(payload['description'],'SYNTHETIC FORM RESET')
        self.assertEqual(float(payload['gross_amount']),1000)
        self.assertTrue(payload['is_planned'])
        for key in keys.values():
            self.assertNotIn(key,saved['inputs'])
        next_view=self.render(2027,'Ammortamenti',inputs=saved['inputs'])
        self.assertEqual(next_view['mutations'],[])
        next_nodes=flatten(next_view['tree'])
        self.assertEqual(next(n['value'] for n in next_nodes if n.get('label')=='Descrizione bene'),'')
        self.assertFalse(next(n['value'] for n in next_nodes if n.get('label')=='Confermo importi, IVA, classificazione e coefficiente quando necessario'))

    def test_state_cleared_when_owner_changes(self):
        self.render(2026,'Fatturato')
        bridge.state['private']='sensitive'
        bridge.render({'tables':{**self.tables,'fiscal_years':[]},'user':{'id':'other-owner','email':'other@example.invalid'},'inputs':{}})
        self.assertNotIn('private',bridge.state)

if __name__=='__main__':unittest.main()

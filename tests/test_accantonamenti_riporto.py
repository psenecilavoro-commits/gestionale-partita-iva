import unittest
from unittest.mock import patch
from decimal import Decimal as D
import json
from accantonamenti_riporto import riporto, snapshot, MARKER, nota_originale
class RiportoTests(unittest.TestCase):
 def year(self,n,amount,source=None,token=None):
  return {"id":str(n),"fiscal_year":n,"status":"closed","notes":"nota"+MARKER+json.dumps({"token":token or str(n),"source_token":source,"carry_out":str(amount)})}
 def test_chain_reopening_reclosure_and_no_double_count(self):
  a=self.year(2026,'12343.81');b=self.year(2027,'1000','2026');years=[a,b]
  with patch('accantonamenti_riporto.leggi_tutti',return_value=years):
   self.assertEqual(riporto(None,{"fiscal_year":2027})[0],D('12343.81'))
   self.assertEqual(riporto(None,{"fiscal_year":2028})[0],D('1000'))
   a['status']='open';self.assertEqual(riporto(None,{"fiscal_year":2027})[0],0);self.assertEqual(riporto(None,{"fiscal_year":2028})[0],0)
   a.update(self.year(2026,'12000',token='new'))
   self.assertEqual(riporto(None,{"fiscal_year":2027})[0],D('12000'));self.assertEqual(riporto(None,{"fiscal_year":2028})[0],0)
   b.update(self.year(2027,'900',source='new',token='new7'));self.assertEqual(riporto(None,{"fiscal_year":2028})[0],D('900'))
   self.assertEqual(nota_originale(a),'nota')
 def test_no_snapshot_does_not_invent_credit(self):
  with patch('accantonamenti_riporto.leggi_tutti',return_value=[{"fiscal_year":2026,"status":"closed","notes":None}]):
   self.assertEqual(riporto(None,{"fiscal_year":2027})[0],0)
if __name__=='__main__':unittest.main()


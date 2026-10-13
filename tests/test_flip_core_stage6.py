import unittest
from flip_core.category_router import categorize
from flip_core.contracts import RawListing, SourceStatus

def l(title,description='',price=100000):
 return RawListing('OLX','1','https://www.olx.pl/x',title,description,price,'PLN',SourceStatus.UNKNOWN,'','test')

class RouterTests(unittest.TestCase):
 def test_pc(self):
  r=categorize(l('Komputer stacjonarny i5-9400 RTX 2060 16 GB RAM'))
  self.assertEqual(r.category,'DESKTOP_PC');self.assertTrue(r.pc_pricing_input_complete);self.assertEqual(r.attributes['ram_gb'],16)
 def test_pc_ryzen(self):
  r=categorize(l('Ryzen 5 5600 RTX 3060 Ti 2x8 GB RAM'))
  self.assertEqual(r.category,'DESKTOP_PC');self.assertTrue(r.pc_pricing_input_complete)
 def test_phone(self):
  r=categorize(l('iPhone 14 Pro 128GB'))
  self.assertEqual(r.category,'SMARTPHONE');self.assertEqual(r.attributes['storage_gb'],128);self.assertFalse(r.pc_pricing_input_complete)
 def test_laptop(self):
  r=categorize(l('Laptop Lenovo ThinkPad i5-1235U 16 GB RAM'))
  self.assertEqual(r.category,'LAPTOP');self.assertFalse(r.pc_pricing_input_complete)
 def test_gpu(self):
  r=categorize(l('Karta graficzna RTX 5060 Ti 16GB'))
  self.assertEqual(r.category,'GPU');self.assertFalse(r.pc_pricing_input_complete)
 def test_ambiguous(self):
  r=categorize(l('Laptop i komputer stacjonarny w zestawie'))
  self.assertEqual(r.category,'AMBIGUOUS');self.assertFalse(r.pc_pricing_input_complete)
 def test_two_cpus(self):
  r=categorize(l('Komputer i5-9400 i7-9700 RTX 2060 16GB RAM'))
  self.assertEqual(r.category,'AMBIGUOUS')
 def test_unknown(self):
  r=categorize(l('Okazja tanio super cena'))
  self.assertEqual(r.category,'UNKNOWN')
 def test_price_required(self):
  r=categorize(l('Komputer stacjonarny i5-9400 RTX 2060 16 GB RAM',price=None))
  self.assertFalse(r.pc_pricing_input_complete)
 def test_hint(self):
  r=categorize(l('Komputer stacjonarny'),{'cpu':'i5-9600K','gpu':'RTX 3070','ram':'16'})
  self.assertTrue(r.pc_pricing_input_complete)
 def test_hardware_variant(self):
  r=categorize(l('PC gaming Ryzen 7 5800X3D Radeon RX 6650 XT 32GB DDR4'))
  self.assertEqual(r.category,'DESKTOP_PC');self.assertTrue(r.pc_pricing_input_complete)
 def test_gpu_ram_not_pc(self):
  r=categorize(l('RTX 5060 Ti 16GB GDDR7'))
  self.assertEqual(r.category,'GPU')

class AuditTests(unittest.TestCase):
 def test_shadow_read_only(self):
  import json,sqlite3,tempfile
  from pathlib import Path
  from flip_core.category_audit import audit_shadow
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'shadow.db'
   with sqlite3.connect(path) as db:
    db.execute('CREATE TABLE listing_observations (id INTEGER PRIMARY KEY,payload_json TEXT)')
    payload={'platform':'OLX','external_id':'123','title':'PC gaming Ryzen 5 5600 RTX 3060 16GB RAM','description':'','currency':'PLN','price_minor':120000,'status':'UNKNOWN','attributes':{}}
    db.execute('INSERT INTO listing_observations VALUES (?,?)',(1,json.dumps(payload)))
   report=audit_shadow(path)
   self.assertEqual(report['categories']['DESKTOP_PC'],1)
   self.assertEqual(report['pc_pricing_inputs_complete'],1)
   self.assertEqual(report['inspected_observations'],1)

import test from 'node:test';
import assert from 'node:assert/strict';
import {splitGross,grossForRecord} from '../src/revenue-vat.js';
test('gross 22% entry uses cents, rejects invalid inputs and preserves the exact original gross',()=>{
 assert.deepEqual(splitGross('1.220,00'),{gross:'1220.00',net:'1000.00',vat:'220.00'});
 assert.deepEqual(splitGross('0'),{gross:'0.00',net:'0.00',vat:'0.00'});
 for(const raw of ['', '-1','1.001','NaN'])assert.throws(()=>splitGross(raw));
 assert.equal(grossForRecord(null),'');
 assert.equal(grossForRecord({amount:'1000.00'}),'1220.00');
 assert.equal(grossForRecord({amount:'0.02',notes:'old note\n[PIVA_GROSS_22_V1]0.03'}),'0.03');
 assert.equal(grossForRecord({amount:'1000.00',notes:'\n[PIVA_GROSS_22_V1]999.00'}),'1220.00');
});
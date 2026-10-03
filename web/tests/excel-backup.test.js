import {test} from 'node:test';
import assert from 'node:assert/strict';
import ExcelJS from 'exceljs';
import {BACKUP_PAGES,backupBytes,numericValue} from '../src/excel-backup.js';
test('Excel backup preserves blank, zero, exact records and both regimes after reopening',async()=>{
  for(const year of [2026,2027]){
    const tables={fiscal_years:[{id:'year',fiscal_year:year,status:'closed',notes:'snapshot'}],monthly_revenues:[{id:'r',amount:'0.00',notes:'=SUM(A1:A2)',month:1}]};
    const views=Object.fromEntries(BACKUP_PAGES.map(p=>[p,{mutations:[],tree:[{kind:'table',records:[{Mese:'Gennaio',Importo:'0,00 €'},{Mese:'Febbraio',Importo:'—'}],children:[]}]}]));
    const file=await backupBytes({year,tables,views});const reopened=new ExcelJS.Workbook();await reopened.xlsx.load(file);
    assert.equal(reopened.getWorksheet('Backup').getCell('B2').value,year===2026?'Forfettario':'Ordinario');
    assert.equal(reopened.getWorksheet('Fatturato').getCell('B4').value,0);
    assert.equal(reopened.getWorksheet('Fatturato').getCell('B5').value,null);
    assert.equal(reopened.getWorksheet('Dati 02').getCell('B4').value,'0.00');
    assert.equal(reopened.getWorksheet('Dati 02').getCell('C4').value,'=SUM(A1:A2)');
    assert.equal(reopened.getWorksheet('Dati 01').getCell('D4').value,'snapshot');
  }
  assert.equal(numericValue('12.343,81 €'),12343.81);
});


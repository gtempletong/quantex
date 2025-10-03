#!/usr/bin/env node

import Airtable from 'airtable';

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
  console.error('❌ Faltan variables de entorno: defina AIRTABLE_API_KEY y AIRTABLE_BASE_ID');
  process.exit(1);
}

console.log('🔍 Explorando tablas disponibles en Airtable...');

const base = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);

async function exploreTables() {
  try {
    console.log('✅ Iniciando exploración...');
    
    // Intentar diferentes nombres de tabla comunes
    const possibleTables = ['Table 1', 'Contacts', 'Users', 'Tasks', 'Projects', 'Records', 'Data'];
    
    for (const tableName of possibleTables) {
      try {
        console.log(`\n📋 Probando tabla: ${tableName}`);
        
        const records = await base(tableName).select({
          maxRecords: 1,
          fields: []
        }).firstPage();
        
        console.log(`✅ Tabla "${tableName}" encontrada!`);
        console.log(`📊 Tipo: ${records.length > 0 ? 'con datos' : 'vacía'}`);
        
        // Intentar obtener campos
        if (records.length > 0) {
          const fields = Object.keys(records[0].fields);
          console.log(`📋 Campos: ${fields.join(', ')}`);
          break; // Encontramos una que funciona
        }
        
      } catch (error) {
        console.log(`❌ Tabla "${tableName}" no encontrada: ${error.message}`);
      }
    }
    
  } catch (error) {
    console.error('❌ Error general:');
    console.error(error.message);
    
    if (error.message.includes('Invalid API Key')) {
      console.log('💡 Solución: Verifica que el API Key sea correcto');
    } else if (error.message.includes('Base ID')) {
      console.log('💡 Solución: Verifica que el Base ID sea correcto');
    } else if (error.message.includes('not authorized')) {
      console.log('💡 Solución: 1) El API Key no tiene permisos para esta base');
      console.log('💡          2) La base no existe o fue eliminada');
      console.log('💡          3) Verifica acceso en airtable.com');
    }
  }
}

exploreTables();






#!/usr/bin/env node

import Airtable from 'airtable';

const AIRTABLE_API_KEY = process.env.AIRTABLE_API_KEY;
const AIRTABLE_BASE_ID = process.env.AIRTABLE_BASE_ID;

if (!AIRTABLE_API_KEY || !AIRTABLE_BASE_ID) {
  console.error('❌ Faltan variables de entorno: defina AIRTABLE_API_KEY y AIRTABLE_BASE_ID');
  process.exit(1);
}

console.log('🌐 Probando conexión con Airtable...');

const base = new Airtable({ apiKey: AIRTABLE_API_KEY }).base(AIRTABLE_BASE_ID);

async function testConnection() {
  try {
    console.log('✅ Iniciando prueba de conexión...');
    
    // Intentar obtener registros de la tabla
    const records = await base('Table 1').select({
      maxRecords: 3,
      view: 'Grid view'
    }).firstPage();
    
    console.log('✅ Conexión exitosa!');
    console.log(`📊 Registros encontrados: ${records.length}`);
    
    if (records.length > 0) {
      console.log('📋 Primer registro:');
      console.log(JSON.stringify(records[0].fields, null, 2));
    }
    
  } catch (error) {
    console.error('❌ Error de conexión:');
    console.error(error.message);
    
    if (error.message.includes('Invalid API Key')) {
      console.log('💡 Verifica que el API Key sea correcto');
    } else if (error.message.includes('Base ID')) {
      console.log('💡 Verifica que el Base ID sea correcto');
    }
  }
}

testConnection();






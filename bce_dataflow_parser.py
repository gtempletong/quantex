#!/usr/bin/env python3
"""
Parse BCE Dataflows XML para encontrar yield curves
"""

import requests
import xml.etree.ElementTree as ET
import re
import time

def fetch_bce_dataflows():
    """Obtiene lista completa de dataflows del BCE"""
    
    url = "https://data-api.ecb.europa.eu/service/dataflow/ECB"
    headers = {
        'Accept': 'application/xml',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Dataflows request: {response.status_code}")
        
        # Delay para no spamear
        time.sleep(2)
        
        if response.status_code == 200:
            # Parse XML
            root = ET.fromstring(response.text)
            
            # Debug: Ver estructura del XML
            print("DEBUG XML:")
            print("Root tag:", root.tag)
            print("Root children:", len(root))
            for child in root[:3]:  # Mostrar primeros 3 elementos
                print(f"  Child: {child.tag} = {child.text[:100] if child.text else 'None'}")
            
            # Extraer todos los dataflows
            dataflows = []
            ns = {
                'mes': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message',
                'str': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure'
            }
            
            print(f"Looking for dataflows with namespace: {ns['str']}")
            dataflow_elements = root.findall('.//str:Dataflow', ns)
            print(f"Found {len(dataflow_elements)} dataflow elements")
            
            # Si no encontramos con namespace, buscamos sin namespace
            if len(dataflow_elements) == 0:
                print("Trying without namespace...")
                dataflow_elements = root.findall('.//Dataflow')
                print(f"Found {len(dataflow_elements)} dataflow elements without namespace")
            
            for i, dataflow in enumerate(dataflow_elements):  # Todos los dataflows
                # Solo debug para los primeros 5
                if i < 5:
                    print(f"\nDataflow {i+1}:")
                    print(f"  Tag: {dataflow.tag}")
                    print(f"  Attribs: {dataflow.attrib}")
                
                # Buscar ID en atributos
                df_id = dataflow.get('id') or dataflow.get('{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}id')
                
                # Buscar nombre/descripción - buscar en múltiples ubicaciones posibles
                name = 'Sin nombre'
                
                # Namespace completo para names
                ns_fetch = {'str': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure'}
                
                # Buscar en diferentes ubicaciones posibles
                name_paths = [
                    'str:Name',
                    'str:Text', 
                    './/str:Name',
                    './/str:Text',
                    'Name',
                    'Text'
                ]
                
                for path in name_paths:
                    elements = dataflow.findall(path, ns_fetch) if 'str:' in path else dataflow.findall(path)
                    for elem in elements:
                        if elem.text and elem.text.strip() and len(elem.text.strip()) > 3:
                            name = elem.text.strip()
                            break
                    if name != 'Sin nombre':
                        break
                
                print(f"  ID: {df_id}")
                print(f"  Name: {name}")
                
                dataflows.append({
                    'id': df_id,
                    'name': name
                })
            
            return dataflows
            
        else:
            print(f"Error: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

def find_yield_candidates(dataflows):
    """Busca dataflows candidatos para yield curves"""
    
    yield_candidates = []
    yield_keywords = ['yield', 'curve', 'bond', 'interest', 'rate', 'yc', 'government', 'gov', 'treasury', 'gb']
    
    print("\n🔍 Checking yield curve candidates:")
    
    for df in dataflows:
        df_text = f"{df['id']} {df['name']}"
        df_text_lower = df_text.lower()
        
        # Mostrar algunos para debug
        if len(yield_candidates) < 10:  # Solo mostrar algunos candidatos
            print(f"  Checking: {df['id']} - {df['name'][:50]}")
        
        for keyword in yield_keywords:
            if keyword in df_text_lower:
                yield_candidates.append(df)
                print(f"    ✅ FOUND: {df['id']} - {df['name']}")
                break
    
    return yield_candidates

def test_dataflow(dataflow_id, series_key):
    """Prueba un dataflow específico con un series key"""
    
    url = f"https://data-api.ecb.europa.eu/service/data/{dataflow_id}/{series_key}"
    headers = {'Accept': 'application/vnd.sdmx.genericdata+xml;version=2.1'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"  Testing {dataflow_id}/{series_key}: {response.status_code}")
        
        # Delay entre tests para evitar bloqueo
        time.sleep(3)
        
        if response.status_code == 200:
            print(f"    SUCCESS! Found data: {len(response.text)} bytes")
            # Ver el contenido XML
            root = ET.fromstring(response.text)
            ns = {'g': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic'}
            series_count = len(root.findall('.//g:Series', ns))
            print(f"    Data series found: {series_count}")
            return True
        else:
            print(f"    Error: {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"    Exception: {e}")
        return False

def main():
    print("🔍 Search BCE Dataflows for Yield Curves")
    print("=" * 50)
    
    # 1. Obtener todos los dataflows
    print("\n1. Fetching all ECB dataflows...")
    dataflows = fetch_bce_dataflows()
    
    if not dataflows:
        print("❌ Failed to fetch dataflows")
        return
    
    print(f"✅ Found {len(dataflows)} dataflows")
    
    # Mostrar TODOS los dataflows para identificar manualmente
    print("\n📋 ALL ECB DATAFLOWS:")
    for i, df in enumerate(dataflows, 1):
        df_id = df['id'] if df['id'] else 'Sin_id'
        name = df['name'] if df['name'] else 'Sin nombre'
        print(f"{i:2d}. {df_id:<8}: {name}")
        
    # 2. Buscar candidatos para yield curves
    print("\n2. Searching yield curve candidates...")
    yield_candidates = find_yield_candidates(dataflows)
    
    print(f"🎯 Found {len(yield_candidates)} yield curve candidates:")
    for candidate in yield_candidates:
        print(f"  - {candidate['id']}: {candidate['name']}")
    
    # 3. Test candidatos con nuestro series key original
    print("\n3. Testing candidates with our original series key...")
    original_key = "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_20Y"
    
    for candidate in yield_candidates:
        print(f"\nTesting dataflow: {candidate['id']}")
        success = test_dataflow(candidate['id'], original_key)
        if success:
            print(f"🎉 FOUND! Dataflow '{candidate['id']}' works with our series key!")
    
    print("\n📝 Next steps:")
    print("1. If we found a working dataflow, update bce_client.py")
    print("2. If not, explore other series keys or dataflow structures")

if __name__ == "__main__":
    main()

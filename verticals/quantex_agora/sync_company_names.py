#!/usr/bin/env python3
"""
Script de Sincronización: Company Names
Sincroniza apollo_companies.name con apollo_persons.company_name
Establece apollo_companies.name como la única fuente de verdad
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))


def sync_company_names(dry_run: bool = True):
    """
    Sincroniza nombres de empresas:
    1. apollo_companies.name es la fuente de verdad
    2. apollo_persons.company_name debe coincidir
    """
    
    # Inicializar Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Variables de entorno de Supabase no configuradas")
    
    supabase = create_client(supabase_url, supabase_key)
    
    print("=" * 80)
    print("🔄 SINCRONIZACIÓN DE NOMBRES DE EMPRESAS")
    print("=" * 80)
    print(f"Modo: {'DRY RUN (solo lectura)' if dry_run else 'ACTUALIZACIÓN REAL'}")
    print()
    
    # 1. Encontrar todas las empresas
    print("📊 Paso 1: Obteniendo todas las empresas...")
    companies_response = supabase.table('apollo_companies').select('id, name').execute()
    companies = companies_response.data
    print(f"   ✅ {len(companies)} empresas encontradas")
    print()
    
    # 2. Para cada empresa, verificar sincronización
    print("🔍 Paso 2: Verificando sincronización...")
    inconsistencies = []
    total_persons_to_update = 0
    
    for company in companies:
        company_id = company['id']
        company_name = company['name']
        
        # Obtener todas las personas de esta empresa
        persons_response = supabase.table('apollo_persons')\
            .select('id, full_name, company_name')\
            .eq('company_id', company_id)\
            .execute()
        
        persons = persons_response.data
        
        if not persons:
            continue
        
        # Verificar si alguna persona tiene un company_name diferente
        mismatched_persons = [
            p for p in persons 
            if p['company_name'] != company_name
        ]
        
        if mismatched_persons:
            inconsistencies.append({
                'company_id': company_id,
                'company_name_truth': company_name,
                'total_persons': len(persons),
                'mismatched_persons': len(mismatched_persons),
                'examples': mismatched_persons[:3]  # Mostrar primeros 3 ejemplos
            })
            total_persons_to_update += len(mismatched_persons)
    
    print(f"   ⚠️  {len(inconsistencies)} empresas con inconsistencias")
    print(f"   📝 {total_persons_to_update} personas necesitan actualización")
    print()
    
    # 3. Mostrar detalles de inconsistencias
    if inconsistencies:
        print("=" * 80)
        print("📋 INCONSISTENCIAS DETECTADAS:")
        print("=" * 80)
        
        for i, inc in enumerate(inconsistencies, 1):
            print(f"\n{i}. Empresa: '{inc['company_name_truth']}'")
            print(f"   Company ID: {inc['company_id']}")
            print(f"   Total personas: {inc['total_persons']}")
            print(f"   Personas con nombre incorrecto: {inc['mismatched_persons']}")
            print(f"   Ejemplos:")
            for person in inc['examples']:
                print(f"      - {person['full_name']}: '{person['company_name']}' → '{inc['company_name_truth']}'")
        
        print()
        print("=" * 80)
        
        # 4. Realizar actualizaciones si no es dry run
        if not dry_run:
            print("\n🔧 Paso 3: Aplicando correcciones...")
            
            updated_companies = 0
            updated_persons = 0
            errors = []
            
            for inc in inconsistencies:
                company_id = inc['company_id']
                correct_name = inc['company_name_truth']
                
                try:
                    # Actualizar todas las personas de esta empresa
                    update_response = supabase.table('apollo_persons')\
                        .update({'company_name': correct_name})\
                        .eq('company_id', company_id)\
                        .execute()
                    
                    updated_persons += inc['mismatched_persons']
                    updated_companies += 1
                    print(f"   ✅ '{correct_name}': {inc['mismatched_persons']} personas actualizadas")
                    
                except Exception as e:
                    errors.append({
                        'company_id': company_id,
                        'company_name': correct_name,
                        'error': str(e)
                    })
                    print(f"   ❌ Error en '{correct_name}': {e}")
            
            print()
            print("=" * 80)
            print("📊 RESUMEN DE ACTUALIZACIÓN:")
            print("=" * 80)
            print(f"✅ Empresas corregidas: {updated_companies}/{len(inconsistencies)}")
            print(f"✅ Personas actualizadas: {updated_persons}/{total_persons_to_update}")
            if errors:
                print(f"❌ Errores: {len(errors)}")
                for err in errors:
                    print(f"   - {err['company_name']}: {err['error']}")
            print()
        else:
            print("\n💡 Para aplicar estas correcciones, ejecuta:")
            print("   python verticals/quantex_agora/sync_company_names.py --apply")
            print()
    else:
        print("✅ ¡Todos los nombres están sincronizados! No se requieren cambios.")
        print()
    
    print("=" * 80)
    print("🏁 SINCRONIZACIÓN COMPLETADA")
    print("=" * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Sincronizar nombres de empresas')
    parser.add_argument('--apply', action='store_true', help='Aplicar cambios (por defecto solo muestra)')
    parser.add_argument('--dry-run', action='store_true', help='Solo mostrar cambios sin aplicar')
    
    args = parser.parse_args()
    
    # Si --apply está presente, dry_run=False, sino dry_run=True
    dry_run = not args.apply
    
    sync_company_names(dry_run=dry_run)



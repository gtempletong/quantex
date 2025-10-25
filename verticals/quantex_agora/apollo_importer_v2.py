#!/usr/bin/env python3
"""
Apollo.io CSV Importer V2
Importa contactos desde CSV a 2 tablas: apollo_companies, apollo_persons
"""

import os
import sys
import csv
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Cargar variables de entorno
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ApolloImporterV2:
    """Importador de Apollo.io con arquitectura de 2 tablas: apollo_companies, apollo_persons"""
    
    def __init__(self):
        """Inicializar importador"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Variables de entorno de Supabase no configuradas")
        
        self.supabase = create_client(supabase_url, supabase_key)
        logger.info("Apollo Importer V2 inicializado")
    
    def upsert_company(self, apollo_row: Dict) -> Optional[str]:
        """
        Insertar o actualizar empresa
        
        Returns:
            UUID de la empresa
        """
        company_name = apollo_row.get('Company Name', '').strip()
        if not company_name:
            return None
        
        industry = apollo_row.get('Industry', '').strip()
        employees = apollo_row.get('# Employees', '').strip()
        website = apollo_row.get('Website', '').strip()
        company_linkedin = apollo_row.get('Company Linkedin Url', '').strip()
        keywords = apollo_row.get('Keywords', '').strip()
        
        # Revenue anual
        annual_revenue = apollo_row.get('Annual Revenue', '').strip()
        
        # Ubicación de empresa
        company_city = apollo_row.get('Company City', '').strip()
        company_state = apollo_row.get('Company State', '').strip()
        company_country = apollo_row.get('Company Country', '').strip()
        location = f"{company_city}, {company_state}, {company_country}".strip(', ')
        
        company_data = {
            'name': company_name,
            'industry': industry if industry else None,
            'employee_count': int(employees) if employees.isdigit() else None,
            'annual_revenue': int(annual_revenue) if annual_revenue.isdigit() else None,
            'website': website if website else None,
            'linkedin_url': company_linkedin if company_linkedin else None,
            'keywords': keywords if keywords else None,
            'location': location if location else None,
            'city': company_city if company_city else None,
            'state': company_state if company_state else None,
            'country': company_country if company_country else None,
        }
        
        # Upsert (insertar o actualizar)
        result = self.supabase.table('apollo_companies').upsert(
            company_data,
            on_conflict='name'
        ).execute()
        
        if result.data:
            return result.data[0]['id']
        
        return None
    
    def upsert_person(self, apollo_row: Dict, company_id: Optional[str]) -> Optional[str]:
        """
        Insertar o actualizar persona
        
        Returns:
            UUID de la persona
        """
        first_name = apollo_row.get('First Name', '').strip()
        last_name = apollo_row.get('Last Name', '').strip()
        full_name = f"{first_name} {last_name}".strip()
        
        if not full_name:
            return None
        
        email = apollo_row.get('Email', '').strip()
        title = apollo_row.get('Title', '').strip()
        linkedin = apollo_row.get('Person Linkedin Url', '').strip()
        
        # Teléfono
        phone = (
            apollo_row.get('Mobile Phone', '').strip() or
            apollo_row.get('Work Direct Phone', '').strip() or
            apollo_row.get('Corporate Phone', '').strip()
        )
        
        # Obtener nombre de la empresa para auditoría
        company_name = apollo_row.get('Company Name', '').strip()
        
        person_data = {
            'full_name': full_name,
            'email': email if email else None,
            'title': title if title else None,
            'linkedin_url': linkedin if linkedin else None,
            'company_id': company_id,
            'company_name': company_name if company_name else None,
            'phone': phone if phone else None,
        }
        
        # Upsert por email o LinkedIn
        # Primero intentar con email
        if email:
            existing = self.supabase.table('apollo_persons').select('id').eq('email', email).execute()
            if existing.data:
                # Actualizar
                result = self.supabase.table('apollo_persons').update(person_data).eq('id', existing.data[0]['id']).execute()
                return existing.data[0]['id']
        
        # Si no existe por email, intentar con LinkedIn
        if linkedin:
            existing = self.supabase.table('apollo_persons').select('id').eq('linkedin_url', linkedin).execute()
            if existing.data:
                # Actualizar
                result = self.supabase.table('apollo_persons').update(person_data).eq('id', existing.data[0]['id']).execute()
                return existing.data[0]['id']
        
        # Insertar nuevo
        result = self.supabase.table('apollo_persons').insert(person_data).execute()
        if result.data:
            return result.data[0]['id']
        
        return None
    
    def import_csv(self, csv_path: str, dry_run: bool = False) -> Dict:
        """
        Importar CSV completo
        
        Returns:
            Diccionario con estadísticas
        """
        stats = {
            'total_rows': 0,
            'companies_created': 0,
            'persons_created': 0,
            'skipped': 0,
            'errors': []
        }
        
        logger.info(f"Importando CSV: {csv_path}")
        logger.info(f"Dry run: {dry_run}")
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                stats['total_rows'] += 1
                
                try:
                    if dry_run:
                        name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                        email = row.get('Email', '').strip()
                        company = row.get('Company Name', '').strip()
                        logger.info(f"DRY RUN - Importaría: {name} ({email}) @ {company}")
                        continue
                    
                    # 1. Upsert company
                    company_id = self.upsert_company(row)
                    if company_id:
                        stats['companies_created'] += 1
                    
                    # 2. Upsert person
                    person_id = self.upsert_person(row, company_id)
                    if not person_id:
                        logger.warning(f"No se pudo crear persona: {row.get('Email', 'sin email')}")
                        stats['skipped'] += 1
                        continue
                    
                    stats['persons_created'] += 1
                    name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                    logger.info(f"✅ Importado: {name}")
                    
                except Exception as e:
                    error_msg = f"Error en fila {stats['total_rows']}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
        
        return stats
    
    def print_summary(self, stats: Dict):
        """Imprimir resumen"""
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE IMPORTACIÓN")
        print("=" * 60)
        print(f"Total de filas procesadas: {stats['total_rows']}")
        print(f"🏢 Empresas creadas/actualizadas: {stats['companies_created']}")
        print(f"👤 Personas creadas/actualizadas: {stats['persons_created']}")
        print(f"⏭️  Saltados: {stats['skipped']}")
        print(f"❌ Errores: {len(stats['errors'])}")
        
        if stats['errors']:
            print("\n❌ ERRORES:")
            for error in stats['errors'][:10]:
                print(f"   - {error}")
        
        print("=" * 60)


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Importar CSV de Apollo.io a Supabase (2 tablas: companies + persons)')
    parser.add_argument('csv_file', nargs='?', default='exports/apollo-contacts-export.csv', 
                       help='Ruta al archivo CSV de Apollo.io (por defecto: exports/apollo-contacts-export.csv)')
    parser.add_argument('--dry-run', action='store_true', help='Modo de prueba (no inserta)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 APOLLO.IO CSV IMPORTER V2 (2 TABLAS)")
    print("=" * 60)
    
    try:
        importer = ApolloImporterV2()
        
        stats = importer.import_csv(
            csv_path=args.csv_file,
            dry_run=args.dry_run
        )
        
        importer.print_summary(stats)
        
        if args.dry_run:
            print("\n💡 Este fue un DRY RUN. Ejecuta sin --dry-run para importar de verdad.")
        
    except FileNotFoundError:
        print(f"❌ Error: Archivo no encontrado: {args.csv_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


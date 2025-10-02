#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PIPELINE COMPLETO: Phantombuster → Supabase → IA Classification → Airtable
================================================================================

Este script ejecuta el pipeline completo de procesamiento de leads:
1. Extrae datos del agent "Quantex Leads" en Phantombuster
2. Los ingesta a Supabase (tabla linkedin_leads)
3. Clasifica candidatos con IA (Haiku) como INCLUIR/DESCARTAR
4. Sincroniza candidatos clasificados a Airtable

Autor: Quantex AI Assistant
Fecha: 2025-09-11
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from pyairtable import Api

# ID hardcodeado del campo LinkedIn URL en Airtable (Prospectos).
# Si lo dejas vacío, el sistema buscará un campo que contenga "linkedin" en el nombre.
LINKEDIN_FIELD_ID_PROSPECTOS = "fldnQnqKX2wSgiZUg"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quantex_leads_pipeline.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Agregar el directorio raíz al path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

from quantex.core import database_manager as db
from quantex.core.llm_manager import generate_completion

class QuantexLeadsPipeline:
    """Pipeline completo para procesamiento de leads desde Phantombuster hasta Airtable"""
    
    def __init__(self):
        """Inicializar conexiones y configuraciones"""
        load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
        
        # Configuración de APIs
        self.phantombuster_api_key = os.getenv("PHANTOMBUSTER_API_KEY")
        self.airtable_api_key = os.getenv("AIRTABLE_API_KEY")
        self.airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
        
        # Conexiones
        self.supabase = db.supabase
        self.table_name = "linkedin_leads"
        self.airtable_table_name = "Prospectos"
        
        # Validar configuración
        if not self.phantombuster_api_key:
            raise ValueError("PHANTOMBUSTER_API_KEY debe estar configurado en .env")
        if not self.airtable_api_key or not self.airtable_base_id:
            raise ValueError("AIRTABLE_API_KEY y AIRTABLE_BASE_ID deben estar configurados en .env")
        
        logger.info("✅ Pipeline inicializado correctamente")
    
    def step1_extract_phantombuster_data(self):
        """Paso 1: Extraer datos del agent Quantex Leads en Phantombuster"""
        logger.info("🔍 PASO 1: Extrayendo datos de Phantombuster...")
        
        headers = {"X-Phantombuster-Key-1": self.phantombuster_api_key}
        
        try:
            # 1. Encontrar el agent "Quantex Leads" - Usar endpoint correcto
            url = "https://api.phantombuster.com/api/v1/user"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            
            # DEBUG: Mostrar toda la respuesta del usuario
            logger.info(f"🔍 Respuesta completa del usuario:")
            logger.info(f"  Status: {user_data.get('status', 'N/A')}")
            logger.info(f"  Keys disponibles: {list(user_data.keys())}")
            
            # La estructura real es {'status': 'success', 'data': {...}}
            if user_data.get('status') == 'success':
                actual_data = user_data.get('data', {})
                logger.info(f"  Data keys: {list(actual_data.keys())}")
                agents = actual_data.get('agents', [])
            else:
                agents = []
            
            # DEBUG: Mostrar todos los agents disponibles
            logger.info(f"🔍 Agents disponibles ({len(agents)}):")
            for i, agent in enumerate(agents):
                logger.info(f"  {i+1}. '{agent.get('name', 'Sin nombre')}' (ID: {agent.get('id', 'N/A')})")
            
            quantex_agent = None
            for agent in agents:
                if agent.get('name') == "Quantex Leads":
                    quantex_agent = agent
                    break
            
            if not quantex_agent:
                raise Exception("No se encontró el agent 'Quantex Leads'")
            
            agent_id = quantex_agent['id']
            logger.info(f"✅ Agent encontrado: {quantex_agent['name']} (ID: {agent_id})")
            
            # 2. Obtener el último container exitoso
            url = f"https://api.phantombuster.com/api/v1/agent/{agent_id}/containers"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            containers_response = response.json()
            
            # DEBUG: Mostrar estructura de containers
            logger.info(f"🔍 Containers response structure: {list(containers_response.keys())}")
            
            # La estructura real es {'status': 'success', 'data': [...]}
            if containers_response.get('status') == 'success':
                containers = containers_response.get('data', [])
            else:
                containers = []
            
            logger.info(f"🔍 Containers disponibles ({len(containers)}):")
            for i, container in enumerate(containers):
                logger.info(f"  {i+1}. Container completo: {container}")
                logger.info(f"     Status: {container.get('status', 'N/A')} (ID: {container.get('id', 'N/A')})")
            
            # Seleccionar SIEMPRE el container más reciente con success
            def _ts_key(ct):
                return ct.get('lastRunAt') or ct.get('createdAt') or ''

            sorted_cts = sorted(containers, key=_ts_key, reverse=True)
            successful_container = next((ct for ct in sorted_cts if ct.get('lastEndStatus') == 'success'), None)
            if successful_container:
                logger.info(f"🔍 Container elegido (más reciente con success): {successful_container['id']}")
            
            if not successful_container:
                raise Exception("No se encontró un container exitoso")
            
            container_id = successful_container['id']
            logger.info(f"✅ Container exitoso encontrado: {container_id}")
            
            # 3. Obtener los datos del container
            url = "https://api.phantombuster.com/api/v2/containers/fetch-result-object"
            params = {"id": container_id}
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data_response = response.json()
            
            # DEBUG: Mostrar estructura de datos
            logger.info(f"🔍 Data response structure: {list(data_response.keys())}")
            
            # Esta respuesta tiene resultObject directamente
            result_object = data_response.get('resultObject', '')
            
            # DEBUG: Mostrar contenido del resultObject
            logger.info(f"🔍 ResultObject type: {type(result_object)}")
            logger.info(f"🔍 ResultObject content: {result_object}")
            
            if not result_object:
                raise Exception("No se encontraron datos en el container")
            
            # 4. Parsear los datos JSON
            leads_data = json.loads(result_object)
            logger.info(f"✅ Se extrajeron {len(leads_data)} leads de Phantombuster")
            
            return leads_data
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo datos de Phantombuster: {e}")
            return None
    
    def step2_ingest_to_supabase(self, leads_data):
        """Paso 2: Ingestar datos a Supabase con detección de duplicados"""
        logger.info("📊 PASO 2: Ingiriendo datos a Supabase...")
        
        uploaded = 0
        errors = 0
        duplicates = 0
        
        for i, lead in enumerate(leads_data):
            try:
                # Limpiar datos del lead
                clean_record = self._clean_lead_data(lead)
                if not clean_record:
                    continue
                
                # Verificar duplicados por URL normalizada (llave principal) y luego por VMID
                norm_url = (clean_record.get('linkedin_profile_url') or '').strip()
                if norm_url:
                    try:
                        existing_url = self.supabase.table(self.table_name).select('id').eq('linkedin_profile_url', norm_url).execute()
                        if existing_url.data:
                            logger.info(f"Lead duplicado encontrado por URL ({norm_url}) - Saltando")
                            duplicates += 1
                            continue
                    except Exception as _e:
                        logger.warning(f"No se pudo verificar duplicado por URL en Supabase: {_e}")

                vmid = clean_record.get('vmid')
                if vmid:
                    existing_vmid = self.supabase.table(self.table_name).select('id').eq('vmid', vmid).execute()
                    if existing_vmid.data:
                        logger.info(f"Lead duplicado encontrado (VMID: {vmid}) - Saltando")
                        duplicates += 1
                        continue
                
                # Insertar registro
                response = self.supabase.table(self.table_name).insert([clean_record]).execute()
                if response.data:
                    uploaded += 1
                else:
                    errors += 1
                    
            except Exception as e:
                if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                    duplicates += 1
                else:
                    errors += 1
                    logger.error(f"Error procesando lead {i}: {e}")
        
        logger.info(f"✅ Supabase: {uploaded} subidos, {duplicates} duplicados, {errors} errores")
        return uploaded, errors, duplicates
    
    def step3_classify_with_ai(self):
        """Paso 3: Clasificar candidatos con IA"""
        logger.info("🤖 PASO 3: Clasificando candidatos con IA...")
        
        try:
            # Obtener candidatos pendientes
            response = self.supabase.table(self.table_name).select('*').eq('ai_classification', 'PENDIENTE').execute()
            candidates = response.data
            
            if not candidates:
                logger.info("✅ No hay candidatos pendientes de clasificación")
                return 0, 0
            
            logger.info(f"📊 Clasificando {len(candidates)} candidatos...")
            
            included = 0
            discarded = 0
            
            for i, candidate in enumerate(candidates):
                logger.info(f"--- Candidato {i+1}/{len(candidates)} ---")
                logger.info(f"Nombre: {candidate.get('full_name', 'N/A')}")
                logger.info(f"Título: {candidate.get('title', 'N/A')}")
                logger.info(f"Empresa: {candidate.get('company_name', 'N/A')}")
                
                # Analizar con IA
                ai_result = self._analyze_candidate_with_ai(candidate)
                
                if ai_result:
                    classification = ai_result.get('classification', 'DESCARTAR')
                    justification = ai_result.get('justification', 'Sin justificación')
                    score = ai_result.get('score', 0)
                    
                    logger.info(f"Clasificación: {classification}")
                    logger.info(f"Puntuación: {score}/10")
                    logger.info(f"Justificación: {justification}")
                    
                    # Actualizar en Supabase
                    self.supabase.table(self.table_name).update({
                        'ai_classification': classification,
                        'ai_justification': justification,
                        'ai_score': score,
                        'ai_analyzed_at': datetime.now().isoformat()
                    }).eq('id', candidate['id']).execute()
                    
                    if classification == 'INCLUIR':
                        included += 1
                    else:
                        discarded += 1
                
                logger.info("")  # Línea en blanco para separar candidatos
            
            logger.info(f"✅ IA: {included} incluidos, {discarded} descartados")
            return included, discarded
            
        except Exception as e:
            logger.error(f"❌ Error en clasificación con IA: {e}")
            return 0, 0
    
    def step4_sync_to_airtable(self):
        """Paso 4: Sincronizar candidatos clasificados a Airtable"""
        logger.info("☁️ PASO 4: Sincronizando candidatos a Airtable...")
        
        try:
            # Obtener candidatos clasificados como INCLUIR
            response = self.supabase.table(self.table_name).select('*').eq('ai_classification', 'INCLUIR').execute()
            candidates = response.data
            
            if not candidates:
                logger.info("✅ No hay candidatos clasificados para sincronizar")
                return 0
            
            # Obtener contactos existentes de Airtable
            api = Api(self.airtable_api_key)
            airtable_table = api.table(self.airtable_base_id, self.airtable_table_name)
            # Usar IDs de campos cuando sea posible para robustez ante cambios de nombre
            # IDs provistos por el usuario:
            #   Nombre: fldYFIXVUfrYL6aIp
            #   Empresa: fldfACaLZKSqlocAR
            #   Cargo: fldg8vmF11tlilwPK
            #   Email: fldh1zqhQNXJGUzyU
            #   Estado: fldBKjhECLwJib5dG (Multiple select)
            #   Phantom Status: fldo6tefvKlf880qu (Multiple select)
            #   LinkedIn Profile URL: (usaremos nombre textual si no hay ID especificado)
            #   Fecha de Creacion: (nombre textual)

            # Obtener todos los registros (evitar error si el nombre del campo difiere)
            existing_records = airtable_table.all()

            def detect_linkedin_field_key(records: list) -> str:
                """Detecta la clave del campo de URL de LinkedIn.
                Intenta ID hardcodeado; si no aparece en los dicts, cae a detección por nombre."""
                hardcoded = (LINKEDIN_FIELD_ID_PROSPECTOS or '').strip()
                if hardcoded:
                    # Comprobar si los records usan IDs como claves
                    for rec in records[:3]:
                        if hardcoded in rec.get('fields', {}):
                            logger.info(f"Usando ID hardcodeado para LinkedIn: {hardcoded}")
                            return hardcoded
                    # Si no se encontró por ID, caer a nombre
                    logger.info("ID hardcodeado no presente en records; intentando detección por nombre 'linkedin'")
                for rec in records:
                    for key in rec.get('fields', {}).keys():
                        if 'linkedin' in key.lower():
                            logger.info(f"Detectado campo por nombre: {key}")
                            return key
                return 'LinkedIn Profile URL'

            linkedin_field_key = detect_linkedin_field_key(existing_records)

            def _normalize_linkedin_url(url: str) -> str:
                try:
                    if not url:
                        return ''
                    u = str(url).strip()
                    for sep in ['#', '?']:
                        if sep in u:
                            u = u.split(sep, 1)[0]
                    u = u.replace('http://', 'https://')
                    if u.endswith('/'):
                        u = u[:-1]
                    return u.lower()
                except Exception:
                    return ''

            existing_contacts_map = {}
            for record in existing_records:
                fields = record.get('fields', {})
                url_val = fields.get(linkedin_field_key)
                norm = _normalize_linkedin_url(url_val)
                if norm:
                    existing_contacts_map[norm] = record['id']

            logger.info(f"🔎 Prospectos Airtable mapeados por URL: {len(existing_contacts_map)}")
            
            # Preparar registros para crear
            records_to_create = []
            processed_candidate_ids = []
            
            already_exists = 0
            to_create = 0
            for candidate in candidates:
                linkedin_url = candidate.get('linkedin_profile_url')
                if not linkedin_url:
                    continue
                norm_candidate = _normalize_linkedin_url(linkedin_url)
                if not norm_candidate:
                    continue
                # Solo crear si no existe
                if norm_candidate not in existing_contacts_map:
                    to_create += 1
                    # Construcción usando IDs de campos donde están definidos (sin wrapper 'fields')
                    record_fields = {
                        "fldYFIXVUfrYL6aIp": candidate.get('full_name', ''),  # Nombre
                        "fldfACaLZKSqlocAR": candidate.get('company_name', ''),  # Empresa
                        "fldg8vmF11tlilwPK": candidate.get('title', ''),  # Cargo
                        "fldh1zqhQNXJGUzyU": candidate.get('email', ''),  # Email
                        linkedin_field_key: norm_candidate,
                        "fldBKjhECLwJib5dG": ["Listo para conectar"],  # Estado (multiple select)
                        # Phantom Status inicialmente en blanco (no encolado todavía)
                        # "fldo6tefvKlf880qu": [],
                        "Fecha de Creacion": datetime.now().strftime('%Y-%m-%d')
                    }
                    records_to_create.append(record_fields)
                
                processed_candidate_ids.append(candidate.get('id'))
                if norm_candidate in existing_contacts_map:
                    already_exists += 1
            
            # Crear registros en Airtable
            success_count = 0
            if records_to_create:
                logger.info(f"📤 Creando {len(records_to_create)} nuevos registros en Airtable...")
                # typecast=True para crear opciones de multiple select si no existen
                airtable_table.batch_create(records_to_create, typecast=True)
                success_count = len(records_to_create)
                logger.info(f"✅ {success_count} registros creados exitosamente")
            else:
                logger.info(f"✅ No hay nuevos prospectos para crear (ya existentes: {already_exists}, a crear: {to_create})")
            
            # Actualizar estado en Supabase
            if success_count > 0:
                self.supabase.table(self.table_name).update({
                    'airtable_synced': True,
                    'airtable_synced_at': datetime.now().isoformat()
                }).in_('id', processed_candidate_ids).execute()
                logger.info("✅ Estados actualizados en Supabase")
            
            logger.info(f"✅ Airtable: {success_count} candidatos sincronizados")
            return success_count
            
        except Exception as e:
            logger.error(f"❌ Error sincronizando con Airtable: {e}")
            return 0
    
    def _clean_lead_data(self, lead):
        """Limpiar y estructurar datos del lead"""
        try:
            def normalize_linkedin_url(url: str) -> str:
                try:
                    if not url:
                        return ''
                    u = str(url).strip()
                    for sep in ['#', '?']:
                        if sep in u:
                            u = u.split(sep, 1)[0]
                    u = u.replace('http://', 'https://')
                    if u.endswith('/'):
                        u = u[:-1]
                    # Rechazar ofuscadas (ACw...)
                    low = u.lower()
                    if '/in/acw' in low:
                        return ''
                    # Aceptar solo /in/slug
                    if '/in/' in low:
                        return u
                    return ''
                except Exception:
                    return ''

            # Preferir siempre defaultProfileUrl; fallback a linkedInProfileUrl si no es ofuscada
            canonical = normalize_linkedin_url(lead.get('defaultProfileUrl', ''))
            if not canonical:
                canonical = normalize_linkedin_url(lead.get('linkedInProfileUrl', ''))

            return {
                'profile_url': lead.get('profileUrl', ''),
                'linkedin_profile_url': canonical,
                'company_url': lead.get('companyUrl', ''),
                'regular_company_url': lead.get('regularCompanyUrl', ''),
                'company_id': lead.get('companyId', ''),
                'linkedin_id': lead.get('vmid', ''),
                'vmid': lead.get('vmid', ''),
                'full_name': lead.get('fullName', ''),
                'first_name': lead.get('firstName', ''),
                'last_name': lead.get('lastName', ''),
                'name': lead.get('name', ''),
                'company_name': lead.get('companyName', ''),
                'title': lead.get('title', ''),
                'title_description': lead.get('titleDescription', ''),
                'industry': lead.get('industry', ''),
                'summary': lead.get('summary', ''),
                'company_location': lead.get('companyLocation', ''),
                'location': lead.get('location', ''),
                'source': 'phantombuster_api',
                'raw_data': lead,
                'uploaded_at': datetime.now().isoformat(),
                'ai_classification': 'PENDIENTE'
            }
        except Exception as e:
            logger.error(f"Error limpiando datos del lead: {e}")
            return None

    def backfill_canonical_urls(self, limit: int | None = None) -> dict:
        """Actualizar linkedin_profile_url en Supabase usando defaultProfileUrl canónica.

        - Prefiere defaultProfileUrl; si no, linkedInProfileUrl si no está ofuscada
        - Resetea airtable_synced para forzar re-sync posterior
        """
        try:
            def normalize_linkedin_url(url: str) -> str:
                try:
                    if not url:
                        return ''
                    u = str(url).strip()
                    for sep in ['#', '?']:
                        if sep in u:
                            u = u.split(sep, 1)[0]
                    u = u.replace('http://', 'https://')
                    if u.endswith('/'):
                        u = u[:-1]
                    low = u.lower()
                    if '/in/acw' in low:
                        return ''
                    if '/in/' in low:
                        return u
                    return ''
                except Exception:
                    return ''

            logger.info("Iniciando backfill de URLs canónicas en Supabase...")
            resp = self.supabase.table(self.table_name).select('*').execute()
            rows = resp.data or []
            if limit is not None:
                rows = rows[:limit]

            changed = 0
            for row in rows:
                raw = row.get('raw_data') or {}
                current = row.get('linkedin_profile_url') or ''
                canonical = normalize_linkedin_url(raw.get('defaultProfileUrl', ''))
                if not canonical:
                    canonical = normalize_linkedin_url(raw.get('linkedInProfileUrl', ''))

                if canonical and canonical != current:
                    self.supabase.table(self.table_name).update({
                        'linkedin_profile_url': canonical,
                        'airtable_synced': None,
                        'airtable_synced_at': None
                    }).eq('id', row['id']).execute()
                    changed += 1

            logger.info(f"Backfill completado. Registros actualizados: {changed}")
            return {"updated": changed, "scanned": len(rows)}

        except Exception as e:
            logger.error(f"Error en backfill de URLs canónicas: {e}")
            return {"updated": 0, "scanned": 0, "error": str(e)}
    
    def _analyze_candidate_with_ai(self, candidate):
        """Analizar candidato con IA para determinar si es decision maker de alto nivel"""
        prompt = f"""
Analiza el siguiente perfil de LinkedIn para determinar si la persona es un "decision maker de alto nivel" en su empresa.

Un "decision maker de alto nivel" es:
- Dueño, fundador, CEO, Gerente General
- VP/Director que claramente tiene poder de decisión estratégico
- Personas con autoridad para tomar decisiones de inversión/financieras importantes

DESCARTAR:
- Roles operativos (coordinadores, analistas, jefes de sucursal)
- VPs/Directores sin poder de decisión estratégico
- Asistentes, encargados operativos

Datos del candidato:
Título: {candidate.get('title', 'N/A')}
Descripción del puesto: {candidate.get('title_description', 'N/A')}
Resumen profesional: {candidate.get('summary', 'N/A')}
Nombre de la empresa: {candidate.get('company_name', 'N/A')}
Industria: {candidate.get('industry', 'N/A')}

Devuelve un objeto JSON con:
{{
    "clasificacion": "INCLUIR" o "DESCARTAR",
    "justificacion": "Explicación breve de por qué",
    "puntuacion": 1-10
}}
"""
        
        try:
            response = generate_completion(
                task_complexity="simple",
                user_prompt=prompt
            )
            
            # Extraer texto de la respuesta
            if "raw_text" in response:
                response_text = response["raw_text"]
            else:
                response_text = str(response)
            
            # Parsear respuesta JSON
            try:
                result = json.loads(response_text)
                return {
                    "classification": result.get("clasificacion", "DESCARTAR"),
                    "justification": result.get("justificacion", "Sin justificación"),
                    "score": result.get("puntuacion", 0)
                }
            except json.JSONDecodeError:
                # Si no es JSON válido, intentar extraer información
                if "INCLUIR" in response_text.upper():
                    return {
                        "classification": "INCLUIR",
                        "justification": response_text[:200],
                        "score": 7
                    }
                else:
                    return {
                        "classification": "DESCARTAR", 
                        "justification": response_text[:200],
                        "score": 3
                    }
                    
        except Exception as e:
            logger.error(f"Error analizando candidato {candidate.get('full_name', 'N/A')}: {e}")
            return {
                "classification": "DESCARTAR",
                "justification": f"Error en análisis: {e}",
                "score": 0
            }
    
    def run_complete_pipeline(self):
        """Ejecutar el pipeline completo"""
        logger.info("🚀 INICIANDO PIPELINE COMPLETO DE QUANTEX LEADS")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Paso 1: Extraer datos de Phantombuster
            leads_data = self.step1_extract_phantombuster_data()
            if not leads_data:
                logger.error("❌ No se pudieron extraer datos de Phantombuster")
                return
            
            # Paso 2: Ingestar a Supabase
            uploaded, errors, duplicates = self.step2_ingest_to_supabase(leads_data)
            
            # Paso 3: Clasificar con IA
            included, discarded = self.step3_classify_with_ai()
            
            # Paso 4: Sincronizar a Airtable
            synced = self.step4_sync_to_airtable()
            
            # Resumen final
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("=" * 60)
            logger.info("📊 RESUMEN FINAL DEL PIPELINE")
            logger.info("=" * 60)
            logger.info(f"⏱️ Duración total: {duration}")
            logger.info(f"📥 Leads extraídos: {len(leads_data)}")
            logger.info(f"📊 Supabase: {uploaded} subidos, {duplicates} duplicados, {errors} errores")
            logger.info(f"🤖 IA: {included} incluidos, {discarded} descartados")
            logger.info(f"☁️ Airtable: {synced} sincronizados")
            logger.info("=" * 60)
            logger.info("✅ PIPELINE COMPLETADO EXITOSAMENTE")
            
        except Exception as e:
            logger.error(f"❌ Error en el pipeline: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

def main():
    """Función principal"""
    try:
        pipeline = QuantexLeadsPipeline()
        pipeline.run_complete_pipeline()
    except Exception as e:
        logger.error(f"❌ Error inicializando pipeline: {e}")

if __name__ == "__main__":
    main()


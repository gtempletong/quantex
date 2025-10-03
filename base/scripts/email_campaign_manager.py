#!/usr/bin/env python3
"""
Sistema integrado de campañas de email
Combina envío y monitoreo con base de datos
"""

import sys
import os
from datetime import datetime
import logging

# Agregar paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.dirname(__file__))

from quantex.core import database_manager as db
from gmail_sender import GmailSender
from gmail_monitor import GmailMonitor

class EmailCampaignManager:
    def __init__(self):
        self.sender = GmailSender()
        self.monitor = GmailMonitor()
        self.setup_logging()
    
    def setup_logging(self):
        """Configurar logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_campaign(self, nombre, asunto, contenido):
        """Crear nueva campaña en base de datos"""
        try:
            campaign_data = {
                'nombre': nombre,
                'asunto': asunto,
                'contenido': contenido,
                'fecha_creacion': datetime.now().isoformat(),
                'estado': 'DRAFT'
            }
            
            result = db.supabase.table('campañas').insert(campaign_data).execute()
            
            if result.data:
                campaign_id = result.data[0]['id']
                self.logger.info(f"✅ Campaña creada: {nombre} (ID: {campaign_id})")
                return campaign_id
            else:
                self.logger.error("❌ Error creando campaña")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error creando campaña: {e}")
            return None
    
    def get_prospects_for_campaign(self, limit=50):
        """Obtener prospectos para campaña"""
        try:
            # Obtener empresas con contactos que tienen email
            query = """
            SELECT 
                e.rut_empresa,
                e.razon_social,
                e.region,
                p.nombre_contacto,
                p.cargo_contacto,
                p.email_contacto
            FROM empresas e
            JOIN personas p ON e.rut_empresa = p.rut_empresa
            WHERE p.email_contacto IS NOT NULL 
            AND p.email_contacto != ''
            LIMIT {}
            """.format(limit)
            
            # Ejecutar query personalizada
            result = db.supabase.rpc('get_prospects_with_emails', {'limit_count': limit}).execute()
            
            if result.data:
                self.logger.info(f"📋 {len(result.data)} prospectos encontrados")
                return result.data
            else:
                # Fallback: query simple
                empresas = db.supabase.table('empresas').select('rut_empresa, razon_social, region').limit(limit).execute()
                personas = db.supabase.table('personas').select('*').not_.is_('email_contacto', 'null').limit(limit).execute()
                
                prospects = []
                for empresa in empresas.data:
                    for persona in personas.data:
                        if empresa['rut_empresa'] == persona['rut_empresa']:
                            prospects.append({
                                'rut_empresa': empresa['rut_empresa'],
                                'razon_social': empresa['razon_social'],
                                'region': empresa['region'],
                                'nombre_contacto': persona['nombre_contacto'],
                                'cargo_contacto': persona['cargo_contacto'],
                                'email_contacto': persona['email_contacto']
                            })
                            break
                
                self.logger.info(f"📋 {len(prospects)} prospectos encontrados (fallback)")
                return prospects
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo prospectos: {e}")
            return []
    
    def send_campaign(self, campaign_id, prospectos):
        """Enviar campaña a lista de prospectos"""
        try:
            # Obtener datos de la campaña
            campaign = db.supabase.table('campañas').select('*').eq('id', campaign_id).execute()
            
            if not campaign.data:
                self.logger.error(f"❌ Campaña {campaign_id} no encontrada")
                return
            
            campaign_data = campaign.data[0]
            asunto = campaign_data['asunto']
            contenido = campaign_data['contenido']
            
            # Registrar envíos
            envios = []
            for prospecto in prospectos:
                # Personalizar contenido
                email_personalizado = self.personalize_email(contenido, prospecto)
                
                # Enviar email
                message_id = self.sender.send_email(
                    to=prospecto['email_contacto'],
                    subject=asunto,
                    body=email_personalizado
                )
                
                # Registrar envío
                envio_data = {
                    'campaña_id': campaign_id,
                    'rut_empresa': prospecto['rut_empresa'],
                    'email_destino': prospecto['email_contacto'],
                    'fecha_envio': datetime.now().isoformat(),
                    'estado': 'sent' if message_id else 'failed',
                    'gmail_message_id': message_id
                }
                
                result = db.supabase.table('envios').insert(envio_data).execute()
                envios.append(envio_data)
                
                self.logger.info(f"📧 Email enviado a {prospecto['email_contacto']} - {prospecto['razon_social']}")
            
            # Actualizar estado de campaña
            db.supabase.table('campañas').update({'estado': 'SENT'}).eq('id', campaign_id).execute()
            
            self.logger.info(f"✅ Campaña enviada: {len(envios)} emails")
            return envios
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando campaña: {e}")
            return []
    
    def personalize_email(self, template, prospecto):
        """Personalizar email con datos del prospecto"""
        personalizado = template
        
        # Reemplazar variables
        personalizado = personalizado.replace('{nombre_contacto}', prospecto['nombre_contacto'])
        personalizado = personalizado.replace('{cargo_contacto}', prospecto['cargo_contacto'])
        personalizado = personalizado.replace('{razon_social}', prospecto['razon_social'])
        personalizado = personalizado.replace('{region}', prospecto['region'])
        
        return personalizado
    
    def monitor_campaign_responses(self, campaign_id):
        """Monitorear respuestas de una campaña"""
        try:
            # Obtener asunto de la campaña
            campaign = db.supabase.table('campañas').select('asunto').eq('id', campaign_id).execute()
            
            if not campaign.data:
                self.logger.error(f"❌ Campaña {campaign_id} no encontrada")
                return
            
            campaign_subject = campaign.data[0]['asunto']
            
            # Buscar respuestas
            replies = self.monitor.get_campaign_replies(campaign_subject, days_back=30)
            
            # Registrar respuestas
            for reply in replies:
                # Extraer email del remitente
                from_email = self.extract_email_from_header(reply['from'])
                
                # Buscar envío correspondiente
                envio = db.supabase.table('envios').select('*').eq('email_destino', from_email).eq('campaña_id', campaign_id).execute()
                
                if envio.data:
                    envio_id = envio.data[0]['id']
                    
                    # Registrar respuesta
                    respuesta_data = {
                        'envio_id': envio_id,
                        'tipo_respuesta': 'REPLY',
                        'fecha_respuesta': datetime.now().isoformat(),
                        'contenido': reply['body'][:500],  # Primeros 500 caracteres
                        'asunto_respuesta': reply['subject']
                    }
                    
                    db.supabase.table('respuestas').insert(respuesta_data).execute()
                    self.logger.info(f"📬 Respuesta registrada de {from_email}")
            
            self.logger.info(f"✅ Monitoreo completado: {len(replies)} respuestas encontradas")
            return replies
            
        except Exception as e:
            self.logger.error(f"❌ Error monitoreando respuestas: {e}")
            return []
    
    def extract_email_from_header(self, header):
        """Extraer email del header 'From'"""
        import re
        email_match = re.search(r'<(.+?)>', header)
        if email_match:
            return email_match.group(1)
        return header

# Ejemplo de uso
if __name__ == "__main__":
    manager = EmailCampaignManager()
    
    # Crear campaña de prueba
    campaign_id = manager.create_campaign(
        nombre="Test Campaign",
        asunto="Oportunidad de negocio - {razon_social}",
        contenido="""
        <h2>Hola {nombre_contacto},</h2>
        <p>Espero que esté bien.</p>
        <p>Me pongo en contacto con usted en representación de <strong>{razon_social}</strong> 
        en la región de <strong>{region}</strong>.</p>
        <p>¿Le interesaría una conversación sobre oportunidades de crecimiento?</p>
        <p>Saludos,<br>Gavin Templeton</p>
        """
    )
    
    if campaign_id:
        # Obtener prospectos
        prospectos = manager.get_prospects_for_campaign(limit=5)
        
        if prospectos:
            # Enviar campaña
            envios = manager.send_campaign(campaign_id, prospectos)
            
            # Monitorear respuestas (después de un tiempo)
            # replies = manager.monitor_campaign_responses(campaign_id)





































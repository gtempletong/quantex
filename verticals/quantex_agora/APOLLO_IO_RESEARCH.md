# 🚀 APOLLO.IO API - INVESTIGACIÓN COMPLETA

## 📚 DOCUMENTACIÓN OFICIAL
- **🏠 Developer Hub**: https://docs.apollo.io/
- **📖 API Reference**: https://docs.apollo.io/reference/
- **🎓 Tutoriales**: https://docs.apollo.io/docs/overview-apollo-api-tutorials
- **🔑 Create API Keys**: https://docs.apollo.io/docs/create-api-keys
- **🧪 Test API Key**: https://docs.apollo.io/docs/test-api-key

---

## 🎯 APOLLO.IO VS LINKEDIN - DIFERENCIA CRÍTICA

### **❌ PROBLEMA CON LINKEDIN:**
- **Exportación limitada**: LinkedIn restringe severamente la exportación de datos
- **Sales Navigator**: Límites estrictos en descargas (solo 2,500 contactos por búsqueda)
- **Scraping prohibido**: Usar scrapers viola TOS y puede bloquear tu cuenta
- **Datos incompletos**: LinkedIn no proporciona emails ni teléfonos directamente
- **API restrictiva**: LinkedIn API no permite búsqueda masiva de leads

### **✅ SOLUCIÓN CON APOLLO.IO:**
- **Exportación ilimitada**: Puedes exportar listas completas sin restricciones
- **Formatos múltiples**: CSV, Excel, integración directa con CRM
- **Emails verificados**: Apollo proporciona emails verificados de cada lead
- **Teléfonos directos**: Acceso a teléfonos móviles y directos
- **API robusta**: Búsqueda programática sin límites artificiales
- **Extensión Chrome**: Exportar directamente desde Apollo.io a CSV/Excel
- **Integraciones**: Salesforce, HubSpot, Google Sheets, etc.

### **💡 VENTAJA CLAVE:**
Con Apollo.io puedes:
1. **Buscar** 10,000 leads en Chile del sector minero
2. **Exportar** todos los contactos con emails y teléfonos
3. **Importar** directamente a Supabase
4. **Automatizar** campañas de email/LinkedIn
5. **Sin restricciones** artificiales de LinkedIn

---

## 🎯 CAPACIDADES PRINCIPALES DE LA API

Según la [documentación oficial](https://docs.apollo.io/docs/api-overview), Apollo.io API te permite:

### **1. BÚSQUEDA (Search)**
- **People Search**: Buscar prospectos por título, ubicación, seniority, industria
- **Organization Search**: Buscar empresas por tamaño, industria, tecnologías
- **Organization Job Postings**: Ver vacantes activas de empresas

### **2. ENRIQUECIMIENTO (Enrichment)**
- **People Enrichment**: Revelar emails, teléfonos, historial laboral
- **Bulk People Enrichment**: Enriquecer múltiples personas en batch
- **Organization Enrichment**: Datos completos de empresas (tecnologías, empleados, ingresos)

### **3. CRM INTEGRADO**
- **Accounts**: Crear y gestionar cuentas (empresas)
- **Contacts**: Crear y gestionar contactos (personas)
- **Deals**: Crear y gestionar oportunidades de venta
- **Tasks**: Crear y gestionar tareas
- **Calls**: Registrar llamadas

### **4. AUTOMATIZACIÓN**
- **Sequences**: Crear y gestionar secuencias de emails automatizadas
- **Add Contacts to Sequence**: Agregar contactos a campañas
- **Update Contact Status**: Gestionar estado en secuencias

### **5. ANALYTICS**
- **API Usage Stats**: Ver consumo de créditos y rate limits
- **Email Accounts**: Gestionar cuentas de email conectadas
- **Users**: Listar usuarios del equipo

---

## 🔑 AUTENTICACIÓN

```python
headers = {
    "x-api-key": "YOUR_API_KEY",
    "Content-Type": "application/json",
    "accept": "application/json",
    "Cache-Control": "no-cache"
}
```

**Importante**: El header es `x-api-key` (minúsculas), no `X-Api-Key`

---

## 💰 LIMITACIONES DEL PLAN GRATUITO

### **❌ ENDPOINTS NO DISPONIBLES EN FREE PLAN:**
- `POST /api/v1/mixed_people/search` - Búsqueda avanzada de personas
- Otros endpoints de búsqueda avanzada requieren plan de pago

### **✅ ALTERNATIVAS DISPONIBLES:**
1. **Usar la interfaz web** de Apollo.io para búsquedas
2. **Crear listas y exportar CSV** (RECOMENDADO)
3. **Upgrade a plan de pago** para acceso completo a la API
4. **Usar extensión Chrome** "Apollo Scraper" para exportar

---

## 📋 FLUJO RECOMENDADO: LISTAS + CSV + SUPABASE

### **PASO 1: Crear Lista en Apollo.io** 
1. Ir a https://app.apollo.io/#/people
2. Usar filtros para buscar (ej: "CEO minería Chile")
3. Seleccionar contactos (checkbox o "Select All")
4. Click "Add to Lists" → "Create New List"
5. Nombrar lista (ej: "CEOs Minería Chile 2025")

### **PASO 2: Exportar Lista a CSV**
1. Ir a "Lists" en el menú lateral
2. Abrir tu lista creada
3. Seleccionar todos los contactos
4. Click "Export" → "Export to CSV"
5. Configurar campos a exportar:
   - Name, Email, Title, Company
   - Phone, LinkedIn URL, Location
   - Industry, Seniority, etc.
6. Descargar CSV

### **PASO 3: Importar CSV a Supabase**
1. Usar script Python para leer CSV
2. Transformar datos al formato de `active_contacts`
3. Insertar en Supabase con detección de duplicados
4. ✅ Listo!

### **VENTAJAS DE ESTE FLUJO:**
- ✅ **100% GRATIS** (no requiere plan de pago)
- ✅ **Exportación ilimitada** de listas
- ✅ **Datos verificados** (emails, teléfonos, LinkedIn)
- ✅ **Sin restricciones** de LinkedIn
- ✅ **Automatizable** (script de importación)

### **📊 PLANES DE APOLLO.IO:**
- **Free**: Acceso limitado a la API, búsquedas manuales en la web
- **Basic ($49/mes)**: Acceso completo a la API
- **Professional ($99/mes)**: API + features avanzados
- **Organization ($149/mes)**: API + team features

---

## 🎯 ENDPOINTS PRINCIPALES

### 1️⃣ **PEOPLE SEARCH** (Búsqueda de Personas)
**Endpoint**: `POST https://api.apollo.io/api/v1/mixed_people/search`

**Capacidades**:
- Buscar contactos por múltiples criterios
- Filtrar por título, seniority, ubicación, empresa
- Obtener emails verificados
- Obtener teléfonos directos
- Obtener perfiles de LinkedIn
- **NO CONSUME CRÉDITOS** para búsquedas básicas

**Parámetros principales**:
```python
{
    "person_titles": ["CEO", "CFO", "Director"],  # Títulos de trabajo
    "person_seniorities": ["c_suite", "vp", "director"],  # Nivel jerárquico
    "person_locations": ["chile", "santiago"],  # Ubicación personal
    "organization_locations": ["chile"],  # Ubicación de la empresa
    "q_organization_domains_list": ["empresa.cl"],  # Dominios de empresas
    "organization_num_employees_ranges": ["100,500"],  # Tamaño de empresa
    "contact_email_status": ["verified"],  # Solo emails verificados
    "q_keywords": "fintech blockchain",  # Palabras clave
    "page": 1,  # Paginación
    "per_page": 25  # Resultados por página (max 100)
}
```

**Respuesta incluye**:
- ✅ Email (verificado/no verificado)
- ✅ LinkedIn URL
- ✅ Teléfonos (móvil, trabajo, directo)
- ✅ Nombre completo, título, seniority
- ✅ Empresa (nombre, dominio, industria, tamaño)
- ✅ Ubicación (ciudad, estado, país, timezone)
- ✅ Redes sociales (Twitter, Facebook, GitHub)
- ✅ Historial laboral
- ✅ Score de confianza del email

---

### 2️⃣ **PEOPLE ENRICHMENT** (Enriquecimiento de Personas)
**Endpoint**: `POST https://api.apollo.io/api/v1/people/match`

**Capacidades**:
- Enriquecer 1 persona a la vez
- Revelar email personal (con parámetro `reveal_personal_emails=true`)
- Obtener teléfono directo
- **CONSUME CRÉDITOS** (1 crédito por persona)

**Parámetros**:
```python
{
    "first_name": "Juan",  # Opcional
    "last_name": "Pérez",  # Opcional
    "name": "Juan Pérez",  # Opcional (alternativa a first/last)
    "email": "juan@empresa.cl",  # Opcional
    "organization_name": "Empresa SA",  # Opcional
    "domain": "empresa.cl",  # Opcional
    "linkedin_url": "https://linkedin.com/in/juanperez"  # Opcional
}
```

**Nota**: Mientras más datos proveas, mejor será el match.

---

### 3️⃣ **ORGANIZATION SEARCH** (Búsqueda de Empresas)
**Endpoint**: `POST https://api.apollo.io/api/v1/mixed_companies/search`

**Capacidades**:
- Buscar empresas por industria, tamaño, ubicación
- Filtrar por tecnologías que usan
- Obtener datos de funding y revenue
- **NO CONSUME CRÉDITOS**

**Parámetros principales**:
```python
{
    "organization_num_employees_ranges": ["100,500", "500,1000"],
    "organization_locations": ["chile", "argentina"],
    "q_organization_keyword_tags": ["fintech", "saas"],
    "organization_industry_tag_ids": ["5567cd4773696439b10b0000"],
    "technologies": ["salesforce", "hubspot"],
    "page": 1,
    "per_page": 25
}
```

---

### 4️⃣ **ORGANIZATION ENRICHMENT** (Enriquecimiento de Empresas)
**Endpoint**: `GET https://api.apollo.io/api/v1/organizations/enrich`

**Capacidades**:
- Enriquecer datos de 1 empresa
- Obtener info completa de la empresa
- **CONSUME CRÉDITOS** (1 crédito por empresa)

**Parámetros**:
```python
{
    "domain": "empresa.cl"  # Requerido
}
```

---

### 5️⃣ **EMAIL SEQUENCES** (Secuencias de Email)
**Endpoints**:
- `GET /api/v1/emailer_campaigns` - Listar secuencias
- `POST /api/v1/emailer_campaigns/{id}/add_contact_ids` - Agregar contactos
- `POST /api/v1/emailer_campaigns/{id}/remove_contact_ids` - Remover contactos

**Capacidades**:
- Crear secuencias automatizadas de emails
- Agregar contactos a secuencias
- Tracking de aperturas y clicks
- Follow-ups automáticos

---

### 6️⃣ **JOB POSTINGS** (Ofertas de Trabajo)
**Endpoint**: `GET https://api.apollo.io/api/v1/organizations/{id}/job_postings`

**Capacidades**:
- Ver ofertas de trabajo de una empresa
- Identificar empresas en crecimiento
- Detectar intención de compra

---

## 💡 CASOS DE USO PARA QUANTEX

### **CASO 1: Búsqueda de Decision Makers en Chile**
```python
search_params = {
    "person_titles": ["CEO", "CFO", "Gerente General", "Director Financiero"],
    "person_seniorities": ["c_suite", "vp", "director"],
    "person_locations": ["chile"],
    "organization_num_employees_ranges": ["50,500", "500,5000"],
    "contact_email_status": ["verified"],
    "per_page": 100
}
```

### **CASO 2: Enriquecer Leads Existentes**
```python
# Tienes LinkedIn URL → Obtener email + teléfono
enrichment_params = {
    "linkedin_url": "https://linkedin.com/in/juanperez",
    "reveal_personal_emails": True
}
```

### **CASO 3: Buscar por Industria Específica**
```python
search_params = {
    "person_titles": ["CFO", "Director Financiero"],
    "organization_locations": ["chile"],
    "q_organization_keyword_tags": ["minería", "construcción", "retail"],
    "organization_num_employees_ranges": ["100,1000"]
}
```

---

## 📊 ESTRUCTURA DE DATOS COMPLETA

### **Contact (Persona)**
```python
{
    # Identidad
    "id": "apollo-id",
    "first_name": "Juan",
    "last_name": "Pérez",
    "name": "Juan Pérez",
    
    # Contacto
    "email": "juan@empresa.cl",
    "email_status": "verified",  # verified, unverified, unavailable
    "email_source": "apollo",
    "contact_emails": [
        {
            "email": "juan@empresa.cl",
            "email_status": "verified",
            "position": 1
        }
    ],
    
    # Teléfonos
    "phone_numbers": [
        {
            "raw_number": "+56912345678",
            "sanitized_number": "+56912345678",
            "type": "mobile",
            "status": "valid"
        }
    ],
    
    # Profesional
    "title": "CFO",
    "headline": "Chief Financial Officer at Empresa SA",
    "seniority": "c_suite",
    
    # Social
    "linkedin_url": "https://linkedin.com/in/juanperez",
    "twitter_url": "https://twitter.com/juanperez",
    "facebook_url": null,
    
    # Ubicación
    "city": "Santiago",
    "state": "Región Metropolitana",
    "country": "Chile",
    "time_zone": "America/Santiago",
    
    # Empresa
    "organization_name": "Empresa SA",
    "organization_id": "apollo-org-id",
    "organization": {
        "id": "apollo-org-id",
        "name": "Empresa SA",
        "website_url": "https://empresa.cl",
        "primary_domain": "empresa.cl",
        "linkedin_url": "https://linkedin.com/company/empresa",
        "founded_year": 2010,
        "phone": "+56223456789",
        "alexa_ranking": 50000
    },
    
    # Historial
    "employment_history": [
        {
            "title": "CFO",
            "organization_name": "Empresa SA",
            "current": true,
            "start_date": "2020-01-01",
            "end_date": null
        }
    ],
    
    # Metadata
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

### **Organization (Empresa)**
```python
{
    "id": "apollo-org-id",
    "name": "Empresa SA",
    "website_url": "https://empresa.cl",
    "primary_domain": "empresa.cl",
    
    # Social
    "linkedin_url": "https://linkedin.com/company/empresa",
    "twitter_url": "https://twitter.com/empresa",
    "facebook_url": "https://facebook.com/empresa",
    
    # Datos de empresa
    "founded_year": 2010,
    "phone": "+56223456789",
    "alexa_ranking": 50000,
    "employee_count": 250,
    "estimated_num_employees": 250,
    
    # Clasificación
    "industry": "Financial Services",
    "keywords": ["fintech", "banking", "payments"],
    "technologies": ["salesforce", "aws", "react"],
    
    # Financiero
    "annual_revenue": "$10M-$50M",
    "total_funding": "$5M",
    "publicly_traded_symbol": null,
    
    # Ubicación
    "city": "Santiago",
    "state": "Región Metropolitana",
    "country": "Chile",
    "street_address": "Av. Apoquindo 1234"
}
```

---

## 🎨 FILTROS AVANZADOS

### **Seniority Levels**
```python
seniorities = [
    "owner",      # Dueño
    "founder",    # Fundador
    "c_suite",    # C-Level (CEO, CFO, CTO, etc.)
    "partner",    # Socio
    "vp",         # Vice President
    "head",       # Head of
    "director",   # Director
    "manager",    # Manager
    "senior",     # Senior IC
    "entry",      # Entry level
    "intern"      # Intern
]
```

### **Email Status**
```python
email_statuses = [
    "verified",           # Email verificado (mejor calidad)
    "unverified",         # Email no verificado
    "likely_to_engage",   # Probable que responda
    "unavailable"         # No disponible
]
```

### **Contact Stages**
```python
contact_stages = [
    "not_contacted",
    "contacted",
    "replied",
    "interested",
    "not_interested",
    "unqualified",
    "qualified",
    "converted"
]
```

---

## ⚡ RATE LIMITS & CRÉDITOS

### **Rate Limits**
- **100 requests/minuto** (puede variar según plan)
- **Recomendación**: 1-2 segundos entre requests

### **Consumo de Créditos**
| Acción | Créditos |
|--------|----------|
| People Search | 0 créditos |
| Organization Search | 0 créditos |
| People Enrichment | 1 crédito |
| Organization Enrichment | 1 crédito |
| Email Reveal | 1 crédito adicional |
| Phone Reveal | 1 crédito adicional |

### **Planes**
- **Free**: 50 créditos/mes
- **Basic**: 1,200 créditos/mes ($49/mes)
- **Professional**: 12,000 créditos/mes ($99/mes)
- **Organization**: Ilimitado (custom pricing)

---

## 💻 EJEMPLO DE IMPLEMENTACIÓN EN PYTHON

```python
import httpx
import asyncio
from typing import List, Dict, Optional

class ApolloClient:
    """Cliente para Apollo.io API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.apollo.io/api/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "accept": "application/json"
        }
    
    async def search_people(
        self,
        person_titles: Optional[List[str]] = None,
        person_seniorities: Optional[List[str]] = None,
        person_locations: Optional[List[str]] = None,
        organization_locations: Optional[List[str]] = None,
        q_organization_domains_list: Optional[List[str]] = None,
        contact_email_status: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict:
        """Buscar personas con filtros"""
        
        url = f"{self.base_url}/mixed_people/search"
        
        payload = {
            "person_titles": person_titles,
            "person_seniorities": person_seniorities,
            "person_locations": person_locations,
            "organization_locations": organization_locations,
            "q_organization_domains_list": q_organization_domains_list,
            "contact_email_status": contact_email_status,
            "page": page,
            "per_page": per_page
        }
        
        # Remover None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def enrich_person(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        domain: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        reveal_personal_emails: bool = True
    ) -> Dict:
        """Enriquecer datos de 1 persona (CONSUME 1 CRÉDITO)"""
        
        url = f"{self.base_url}/people/match"
        
        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "organization_name": organization_name,
            "domain": domain,
            "linkedin_url": linkedin_url
        }
        
        # Remover None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        params = {}
        if reveal_personal_emails:
            params["reveal_personal_emails"] = "true"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url, 
                json=payload, 
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def search_organizations(
        self,
        organization_locations: Optional[List[str]] = None,
        organization_num_employees_ranges: Optional[List[str]] = None,
        q_organization_keyword_tags: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict:
        """Buscar empresas con filtros"""
        
        url = f"{self.base_url}/mixed_companies/search"
        
        payload = {
            "organization_locations": organization_locations,
            "organization_num_employees_ranges": organization_num_employees_ranges,
            "q_organization_keyword_tags": q_organization_keyword_tags,
            "page": page,
            "per_page": per_page
        }
        
        # Remover None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def enrich_organization(self, domain: str) -> Dict:
        """Enriquecer datos de 1 empresa (CONSUME 1 CRÉDITO)"""
        
        url = f"{self.base_url}/organizations/enrich"
        
        params = {"domain": domain}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()


# EJEMPLO DE USO
async def main():
    client = ApolloClient(api_key="YOUR_API_KEY")
    
    # Buscar CFOs en Chile
    results = await client.search_people(
        person_titles=["CFO", "Director Financiero"],
        person_locations=["chile"],
        organization_num_employees_ranges=["100,1000"],
        contact_email_status=["verified"],
        per_page=50
    )
    
    print(f"Encontrados: {results['pagination']['total_entries']} contactos")
    
    for contact in results['contacts']:
        print(f"- {contact['name']} | {contact['title']} | {contact['email']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔥 VENTAJAS VS PHANTOMBUSTER

| Feature | Apollo.io | Phantombuster |
|---------|-----------|---------------|
| **API Robusta** | ✅ REST API estable | ❌ API inconsistente |
| **Emails Verificados** | ✅ Sí | ❌ No |
| **Teléfonos Directos** | ✅ Sí | ❌ No |
| **Búsqueda Avanzada** | ✅ 50+ filtros | ❌ Limitado |
| **Sin Scraping** | ✅ Datos propios | ❌ Scraping de LinkedIn |
| **Rate Limits** | ✅ Claros | ❌ Confusos |
| **Documentación** | ✅ Excelente | ❌ Pobre |
| **Créditos** | ✅ Búsquedas gratis | ❌ Todo consume |
| **Paginación** | ✅ Nativa | ❌ Manual |

---

## 🎯 ESTRATEGIA RECOMENDADA PARA QUANTEX

### **FASE 1: BÚSQUEDA (GRATIS)**
1. Usar **People Search** para encontrar decision makers
2. Filtrar por:
   - Títulos: CEO, CFO, Gerente General
   - Seniority: c_suite, vp, director
   - Ubicación: Chile
   - Tamaño empresa: 100-5000 empleados
   - Email status: verified

### **FASE 2: ENRIQUECIMIENTO SELECTIVO (CONSUME CRÉDITOS)**
1. Solo enriquecer leads que:
   - Pasaron clasificación de IA
   - No tienen email en búsqueda inicial
   - Son de alta prioridad

### **FASE 3: AUTOMATIZACIÓN**
1. Agregar a secuencias de email en Apollo
2. Tracking automático de aperturas/clicks
3. Follow-ups automáticos

---

## 📦 REPOSITORIOS DE REFERENCIA

1. **edwardchoh/apollo-io-mcp-server** (⭐ MÁS COMPLETO)
   - Python MCP server
   - Implementación completa de todos los endpoints
   - Modelos Pydantic bien definidos
   - https://github.com/edwardchoh/apollo-io-mcp-server

2. **Significant-Gravitas/AutoGPT** (⭐ PRODUCCIÓN)
   - Implementación en AutoGPT
   - Manejo de paginación
   - Error handling robusto
   - https://github.com/Significant-Gravitas/AutoGPT

3. **sajdakabir/ContactHarvest** (⭐ EJEMPLO PRÁCTICO)
   - Script completo de extracción
   - CSV input/output
   - Rate limiting implementado
   - https://github.com/sajdakabir/ContactHarvest

4. **fmaume/apollo.io-API-for-linkedin-lead-generation**
   - Tutorial en Medium
   - Conversión de websites a leads
   - https://github.com/fmaume/apollo.io-API-for-linkedin-lead-generation

---

## 🚨 CONSIDERACIONES IMPORTANTES

### **✅ PROS**
- Base de datos masiva (275M+ contactos)
- Emails verificados (no rebotes)
- Teléfonos directos
- Búsquedas ilimitadas sin créditos
- API estable y documentada
- Paginación nativa
- Filtros muy avanzados

### **⚠️ CONTRAS**
- Enriquecimiento consume créditos
- Rate limits (100 req/min)
- Requiere plan pagado para uso intensivo
- Datos principalmente de USA/Europa (menos cobertura LATAM)

### **💡 TIPS**
1. **Maximizar búsquedas gratuitas** antes de enriquecer
2. **Cachear resultados** para evitar requests duplicados
3. **Usar múltiples filtros** para mejor targeting
4. **Verificar `email_status`** antes de usar emails
5. **Combinar con IA** para clasificación adicional

---

## 🔄 INTEGRACIÓN CON QUANTEX

### **Nueva Arquitectura Propuesta**
```
Apollo.io (People Search) → Supabase (apollo_leads)
         ↓
    IA Classification (Haiku)
         ↓
Apollo.io (Enrichment) → Supabase (active_contacts)
         ↓
    Email Sequences (Apollo o Brevo)
         ↓
    Tracking & Analytics (Quantex CRM)
```

### **Ventajas**
- ✅ Eliminar Phantombuster completamente
- ✅ Eliminar Airtable (todo en Supabase)
- ✅ Emails verificados desde el inicio
- ✅ Teléfonos directos disponibles
- ✅ Datos más completos y confiables
- ✅ API más estable y predecible

---

## 📝 PRÓXIMOS PASOS

1. ✅ Crear cuenta en Apollo.io
2. ✅ Obtener API key
3. ⏳ Crear `apollo_client.py` base
4. ⏳ Crear tabla `apollo_leads` en Supabase
5. ⏳ Implementar pipeline de búsqueda
6. ⏳ Integrar clasificación IA
7. ⏳ Implementar enriquecimiento selectivo
8. ⏳ Actualizar dashboard CRM

---

**Última actualización**: 2025-10-15
**Investigación realizada por**: Quantex AI Assistant



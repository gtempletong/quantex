# 🔧 Guía de Configuración de Variables de Entorno

## 📋 Variables de Entorno Necesarias

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

### 🌐 Supabase
```bash
SUPABASE_DOMAIN=tu_dominio_supabase_aqui
SUPABASE_ANON_KEY=tu_anon_key_aqui
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key_aqui
```

### 🔑 APIs Externas
```bash
# Firecrawl
FIRECRAWL_API_KEY=tu_firecrawl_api_key_aqui
FIRECRAWL_API_URL=https://api.firecrawl.dev/v0/scrape

# Serper (Google Search)
SERPER_API_KEY=tu_serper_api_key_aqui
SERPER_API_URL=https://google.serper.dev/search

# Perplexity AI
PERPLEXITY_API_KEY=tu_perplexity_api_key_aqui
PERPLEXITY_API_URL=https://api.perplexity.ai/chat/completions

# EODHD (Datos Financieros)
EODHD_API_KEY=tu_eodhd_api_key_aqui
EODHD_API_URL=https://eodhd.com/api/eod
```

### 🏦 Bancos Centrales
```bash
BCE_API_URL=https://data-api.ecb.europa.eu
BCENTRAL_API_URL=https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx
BCCH_API_URL=https://api.bcentral.cl/v1/series
```

### 📧 Gmail & Google Services
```bash
GMAIL_CREDENTIALS_PATH=./google_credentials.json
GMAIL_USER_EMAIL=tu_email_gmail_aqui
GMAIL_CREDENTIALS_FILE=./base/scripts/gmail_credentials.json
GMAIL_TOKEN_FILE=./base/scripts/gmail_token.json
GOOGLE_DRIVE_SCOPES=https://www.googleapis.com/auth/drive.readonly
```

### 📊 Email Marketing (Brevo)
```bash
BREVO_API_KEY=tu_brevo_api_key_aqui
```

### 🔗 LinkedIn & PhantomBuster
```bash
PHANTOMBUSTER_API_KEY=tu_phantombuster_api_key_aqui
PHANTOMBUSTER_SPREADSHEET_URL=tu_google_sheet_url_aqui
PHANTOMBUSTER_SPREADSHEET_TAB=tu_sheet_tab_name_aqui
```

### 📋 Airtable
```bash
AIRTABLE_API_KEY=tu_airtable_api_key_aqui
AIRTABLE_BASE_ID=tu_airtable_base_id_aqui
```

### 💬 Slack
```bash
SLACK_BOT_TOKEN=tu_slack_bot_token_aqui
SLACK_SIGNING_SECRET=tu_slack_signing_secret_aqui
```

### 🗄️ Pinecone
```bash
PINECONE_API_KEY=tu_pinecone_api_key_aqui
PINECONE_ENVIRONMENT=tu_pinecone_environment_aqui
```

### 🔒 Seguridad
```bash
JWT_SECRET_KEY=tu_jwt_secret_key_muy_seguro_aqui
ENCRYPTION_KEY=tu_encryption_key_aqui
```

## 📁 Archivos de Credenciales a Copiar

1. **`google_credentials.json`** → `./google_credentials.json`
2. **`base/scripts/gmail_credentials.json`** → `./base/scripts/gmail_credentials.json`
3. **`base/scripts/gmail_token.json`** → `./base/scripts/gmail_token.json`

## ⚠️ Importante

- **NO** subas el archivo `.env` a GitHub
- **NO** subas los archivos de credenciales a GitHub
- Mantén las credenciales seguras y privadas
- Usa rutas relativas (./) en lugar de rutas absolutas

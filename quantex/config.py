import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Config:
    """Configuración centralizada para Quantex"""
    
    # Supabase
    SUPABASE_DOMAIN = os.getenv("SUPABASE_DOMAIN")
    
    # APIs Externas
    FIRECRAWL_API_URL = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v0/scrape")
    SERPER_API_URL = os.getenv("SERPER_API_URL", "https://google.serper.dev/search")
    PERPLEXITY_API_URL = os.getenv("PERPLEXITY_API_URL", "https://api.perplexity.ai/chat/completions")
    
    # APIs Financieras
    EODHD_API_URL = os.getenv("EODHD_API_URL", "https://eodhd.com/api/eod")
    BCE_API_URL = os.getenv("BCE_API_URL", "https://data-api.ecb.europa.eu")
    BCENTRAL_API_URL = os.getenv("BCENTRAL_API_URL", "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx")
    BCCH_API_URL = os.getenv("BCCH_API_URL", "https://api.bcentral.cl/v1/series")
    
    # Google APIs
    GOOGLE_DRIVE_SCOPES = os.getenv("GOOGLE_DRIVE_SCOPES", "https://www.googleapis.com/auth/drive.readonly")
    
    @classmethod
    def get_supabase_domain(cls):
        """Obtener dominio de Supabase desde variables de entorno"""
        if not cls.SUPABASE_DOMAIN:
            raise ValueError("❌ SUPABASE_DOMAIN no está configurado en las variables de entorno")
        return cls.SUPABASE_DOMAIN
    
    @classmethod
    def get_firecrawl_url(cls):
        """Obtener URL de Firecrawl API"""
        return cls.FIRECRAWL_API_URL
    
    @classmethod
    def get_serper_url(cls):
        """Obtener URL de Serper API"""
        return cls.SERPER_API_URL
    
    @classmethod
    def get_perplexity_url(cls):
        """Obtener URL de Perplexity API"""
        return cls.PERPLEXITY_API_URL
    
    @classmethod
    def get_eodhd_url(cls):
        """Obtener URL base de EODHD API"""
        return cls.EODHD_API_URL
    
    @classmethod
    def get_bce_url(cls):
        """Obtener URL de BCE API"""
        return cls.BCE_API_URL
    
    @classmethod
    def get_bcentral_url(cls):
        """Obtener URL de Banco Central Chile API"""
        return cls.BCENTRAL_API_URL
    
    @classmethod
    def get_bcch_url(cls):
        """Obtener URL de BCCH API"""
        return cls.BCCH_API_URL
    
    @classmethod
    def get_google_drive_scopes(cls):
        """Obtener scopes de Google Drive"""
        return cls.GOOGLE_DRIVE_SCOPES
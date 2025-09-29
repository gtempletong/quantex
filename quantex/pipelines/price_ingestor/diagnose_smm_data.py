#!/usr/bin/env python3
"""
Diagnóstico de datos SMM - Verificar qué está pasando con shfe y lme
"""

import os
import sys
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from quantex.core.data_fetcher import get_data_series
from quantex.core.database_manager import supabase

def diagnose_smm_data():
    """Diagnosticar datos SMM"""
    print("🔍 DIAGNÓSTICO DE DATOS SMM")
    print("="*50)
    
    # Verificar series disponibles
    print("\n📊 SERIES DISPONIBLES:")
    try:
        series_res = supabase.table('series_definitions').select('ticker,description,display_name').ilike('ticker', '%shfe%').execute()
        if series_res.data:
            for series in series_res.data:
                print(f"   ✅ {series['ticker']}: {series.get('display_name', series.get('description', 'Sin descripción'))}")
        else:
            print("   ❌ No se encontraron series SHFE")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    try:
        series_res = supabase.table('series_definitions').select('ticker,description,display_name').ilike('ticker', '%lme%').execute()
        if series_res.data:
            for series in series_res.data:
                print(f"   ✅ {series['ticker']}: {series.get('display_name', series.get('description', 'Sin descripción'))}")
        else:
            print("   ❌ No se encontraron series LME")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Verificar datos recientes
    print("\n📈 DATOS RECIENTES (últimos 7 días):")
    
    for ticker in ['shfe', 'lme']:
        print(f"\n🔍 {ticker.upper()}:")
        try:
            df = get_data_series(ticker, days=7)
            if df is not None and not df.empty:
                print(f"   ✅ {len(df)} registros encontrados")
                print(f"   📅 Rango: {df.index[0].strftime('%Y-%m-%d')} a {df.index[-1].strftime('%Y-%m-%d')}")
                print(f"   💰 Último precio: {df['close'].iloc[-1] if 'close' in df.columns else df['value'].iloc[-1]}")
                print(f"   📊 Valores únicos: {df['close'].nunique() if 'close' in df.columns else df['value'].nunique()}")
                
                # Verificar si todos los valores son iguales (problema de forward fill)
                values = df['close'] if 'close' in df.columns else df['value']
                if values.nunique() == 1:
                    print(f"   ⚠️ PROBLEMA: Todos los valores son iguales ({values.iloc[0]})")
                else:
                    print(f"   ✅ Valores variados: min={values.min():.2f}, max={values.max():.2f}")
            else:
                print(f"   ❌ No hay datos para {ticker}")
        except Exception as e:
            print(f"   ❌ Error obteniendo datos: {e}")
    
    # Verificar datos en time_series_data directamente
    print("\n🗄️ DATOS EN TIME_SERIES_DATA:")
    try:
        for ticker in ['shfe', 'lme']:
            print(f"\n🔍 {ticker.upper()}:")
            res = supabase.table('time_series_data').select('timestamp,value').eq('ticker', ticker).order('timestamp', desc=True).limit(10).execute()
            if res.data:
                print(f"   ✅ {len(res.data)} registros recientes")
                for i, record in enumerate(res.data[:5]):
                    print(f"   {i+1}. {record['timestamp']}: {record['value']}")
            else:
                print(f"   ❌ No hay datos en time_series_data para {ticker}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*50)
    print("🎯 DIAGNÓSTICO COMPLETADO")

if __name__ == "__main__":
    diagnose_smm_data()


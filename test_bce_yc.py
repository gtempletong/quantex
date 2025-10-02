#!/usr/bin/env python3
"""
Test específico para BCE Yield Curves con dataflow YC
"""

import requests
import time

def test_yc_ticker(ticker):
    """Prueba un ticker específico en el dataflow YC"""
    url = f"https://data-api.ecb.europa.eu/service/data/YC/{ticker}"
    headers = {
        'Accept': 'application/vnd.sdmx.genericdata+xml;version=2.1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"\nTesting: {ticker}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ SUCCESS! Content length: {len(response.text)} bytes")
            
            # Buscar elementos de datos
            if '<ObsValue value=' in response.text:
                print("✅ Found observation values in XML!")
                return True
            else:
                print("⚠️ XML returned but no observation values found")
                print(f"Content preview: {response.text[:300]}")
                return False
        else:
            print(f"❌ Error: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("🎯 Testing BCE Yield Curve Dataflow YC")
    print("=" * 50)
    
    # Nuestros tickers específicos del BCE
    our_tickers = [
        "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_20Y",  # 20 años
        "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",  # 10 años  
        "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_5Y",   # 5 años
        "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y",   # 2 años
        "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y",  # 30 años
    ]
    
    success_count = 0
    for ticker in our_tickers:
        success = test_yc_ticker(ticker)
        if success:
            success_count += 1
        time.sleep(2)  # Delay para no spamear
    
    print(f"\n📊 SUMMARY:")
    print(f"Successful tickers: {success_count}/{len(our_tickers)}")
    
    if success_count > 0:
        print("\n🎉 MIGRATION READY!")
        print("Update bce_client.py with:")
        print("- API endpoint: https://data-api.ecb.europa.eu")
        print("- Dataflow: YC")
        print("- URL format: /service/data/YC/{ticker}")
    else:
        print("\n🤔 All tickers failed - may need different structure")

if __name__ == "__main__":
    main()



















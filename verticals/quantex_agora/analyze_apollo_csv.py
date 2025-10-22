#!/usr/bin/env python3
"""
Analizar CSV de Apollo.io para entender su estructura
"""

import csv
import json

csv_file = r"C:\quantex\verticals\quantex_agora\exports\apollo-contacts-export.csv"

print("=" * 80)
print("📊 ANÁLISIS DE CSV DE APOLLO.IO")
print("=" * 80)

with open(csv_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    
    # Obtener headers
    headers = reader.fieldnames
    print(f"\n📋 TOTAL DE COLUMNAS: {len(headers)}")
    print("\n📝 COLUMNAS DISPONIBLES:")
    for i, header in enumerate(headers, 1):
        print(f"   {i:2d}. {header}")
    
    # Leer primera fila para ver datos
    rows = list(reader)
    print(f"\n📊 TOTAL DE CONTACTOS: {len(rows)}")
    
    if rows:
        print("\n🔍 EJEMPLO DE PRIMER CONTACTO:")
        first = rows[0]
        
        # Campos más importantes
        important_fields = [
            'First Name', 'Last Name', 'Title', 'Company Name',
            'Email', 'Email Status', 'Work Direct Phone', 'Mobile Phone',
            'Person Linkedin Url', 'City', 'State', 'Country',
            'Industry', '# Employees', 'Seniority', 'Departments'
        ]
        
        for field in important_fields:
            value = first.get(field, '')
            if value:
                print(f"   {field:30s}: {value[:80]}")
        
        # Estadísticas
        print("\n📈 ESTADÍSTICAS:")
        
        emails_count = sum(1 for r in rows if r.get('Email'))
        print(f"   Con Email: {emails_count}/{len(rows)}")
        
        phones_count = sum(1 for r in rows if r.get('Mobile Phone') or r.get('Work Direct Phone'))
        print(f"   Con Teléfono: {phones_count}/{len(rows)}")
        
        linkedin_count = sum(1 for r in rows if r.get('Person Linkedin Url'))
        print(f"   Con LinkedIn: {linkedin_count}/{len(rows)}")
        
        verified_count = sum(1 for r in rows if r.get('Email Status') == 'Verified')
        print(f"   Emails Verificados: {verified_count}/{emails_count}")
        
        # Seniorities
        seniorities = {}
        for r in rows:
            sen = r.get('Seniority', 'N/A')
            seniorities[sen] = seniorities.get(sen, 0) + 1
        
        print(f"\n   Por Seniority:")
        for sen, count in sorted(seniorities.items(), key=lambda x: -x[1]):
            print(f"      {sen:20s}: {count}")
        
        # Industries
        industries = {}
        for r in rows:
            ind = r.get('Industry', 'N/A')
            industries[ind] = industries.get(ind, 0) + 1
        
        print(f"\n   Por Industria:")
        for ind, count in sorted(industries.items(), key=lambda x: -x[1])[:10]:
            print(f"      {ind:30s}: {count}")

print("\n" + "=" * 80)


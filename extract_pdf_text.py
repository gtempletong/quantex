#!/usr/bin/env python3
"""
Script para extraer texto del PDF y analizar su estructura
"""

import PyPDF2
import sys
from pathlib import Path

def extract_pdf_text(pdf_path: str, max_pages: int = 10):
    """Extrae texto de las primeras páginas del PDF"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            print(f"📄 PDF tiene {total_pages} páginas")
            print(f"📖 Extrayendo primeras {min(max_pages, total_pages)} páginas...")
            print("="*80)
            
            text_content = ""
            for page_num in range(min(max_pages, total_pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                
                print(f"\n--- PÁGINA {page_num + 1} ---")
                print(page_text[:500] + "..." if len(page_text) > 500 else page_text)
                print("-" * 40)
                
                text_content += f"\n--- PÁGINA {page_num + 1} ---\n"
                text_content += page_text + "\n"
            
            return text_content
            
    except Exception as e:
        print(f"❌ Error extrayendo PDF: {e}")
        return None

if __name__ == "__main__":
    pdf_path = "quantex/pipelines/price_ingestor/FIP ECOMAC II - Directorio 2Q2025.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ Archivo no encontrado: {pdf_path}")
        sys.exit(1)
    
    text = extract_pdf_text(pdf_path, max_pages=5)
    
    if text:
        # Guardar el texto extraído para análisis
        with open("pdf_content_sample.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n✅ Texto extraído guardado en: pdf_content_sample.txt")







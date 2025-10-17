"""Script para verificar estado de licitaciones"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from tenders.models import Tender

# Estadísticas
total = Tender.objects.count()
with_xml = Tender.objects.exclude(xml_content='').exclude(xml_content__isnull=True).count()
without_xml = total - with_xml

print("="*60)
print("ESTADO DE LICITACIONES")
print("="*60)
print(f"Total licitaciones: {total}")
print(f"Con XML completo: {with_xml}")
print(f"Sin XML: {without_xml}")

if with_xml > 0:
    sample = Tender.objects.exclude(xml_content='').exclude(xml_content__isnull=True).first()
    print(f"\n[MUESTRA]")
    print(f"  ID: {sample.ojs_notice_id}")
    print(f"  Titulo: {sample.title[:60]}...")
    print(f"  Tamano XML: {len(sample.xml_content)} caracteres")
    has_xml_tag = "<?xml" in sample.xml_content
    print(f"  XML valido: {has_xml_tag}")

    if not has_xml_tag:
        print("\n[WARNING] El XML no parece valido (no contiene <?xml)")
        print(f"Primeros 200 caracteres: {sample.xml_content[:200]}")
else:
    print("\n[INFO] No hay licitaciones con XML disponibles")
    print("Necesitas descargar licitaciones con contenido XML completo")

"""Script para descargar licitaciones CON contenido XML desde TED"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tenders.ted_downloader import download_and_save_tenders

print("="*60)
print("DESCARGA DE LICITACIONES CON XML")
print("="*60)

# Parámetros de descarga
params = {
    'days_back': 15,  # Últimos 15 días
    'max_download': 5,  # Máximo 5 licitaciones para prueba
    'cpv_codes': ['72'],  # Software y servicios IT
    'place': 'ESP',  # España
    'notice_type': 'cn-standard'  # Solo convocatorias estándar
}

print(f"\nParametros:")
print(f"  - Periodo: ultimos {params['days_back']} dias")
print(f"  - Maximo: {params['max_download']} licitaciones")
print(f"  - CPV: {params['cpv_codes']}")
print(f"  - Pais: {params['place']}")
print(f"\nIniciando descarga...\n")

try:
    result = download_and_save_tenders(**params)

    print("\n" + "="*60)
    print("RESULTADO")
    print("="*60)
    print(f"Total encontradas: {result['total_found']}")
    print(f"Descargadas: {result['downloaded']}")
    print(f"Guardadas: {result['saved']}")
    print(f"Errores: {len(result['errors'])}")

    # Verificar que se guardaron con XML
    from apps.tenders.models import Tender
    with_xml = Tender.objects.exclude(xml_content='').exclude(xml_content__isnull=True).count()
    print(f"\nLicitaciones con XML en BD: {with_xml}")

    if with_xml > 0:
        print("\n[SUCCESS] Descarga exitosa con XML!")
    else:
        print("\n[WARNING] Las licitaciones se descargaron pero sin XML")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

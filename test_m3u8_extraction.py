"""
Script de prueba para verificar extracción de m3u8 en modo móvil y escritorio
"""
from src.platzi.utils import get_m3u8_url

# Simular contenido de escritorio (JSON de Next.js)
escritorio_content = '''
"serverC":{"id":"serverC","hls":"https://api.platzi.com/mdstrm/v1/video/68dc1cdae738b5b94215cc55.m3u8","dash":"https://api.platzi.com/mdstrm/v1/video/68dc1cdae738b5b94215cc55.mpd"}
'''

# Simular contenido móvil (HTML directo)
movil_content = '''
<video src="https://api.platzi.com/mdstrm/v1/video/68dc1cdae738b5b94215cc55.m3u8">
'''

print("="*80)
print("PRUEBA DE EXTRACCIÓN M3U8")
print("="*80)

# Test 1: Escritorio (JSON)
print("\n[TEST 1] Contenido tipo ESCRITORIO (JSON de Next.js)")
try:
    url = get_m3u8_url(escritorio_content)
    print(f"✅ ÉXITO - URL extraída del JSON:")
    print(f"   {url}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 2: Móvil (HTML)
print("\n[TEST 2] Contenido tipo MÓVIL (HTML directo)")
try:
    url = get_m3u8_url(movil_content)
    print(f"✅ ÉXITO - URL extraída del HTML:")
    print(f"   {url}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 3: Sin m3u8
print("\n[TEST 3] Contenido sin m3u8 (debería fallar)")
try:
    url = get_m3u8_url("<html><body>No video here</body></html>")
    print(f"❌ FALLÓ - No debería encontrar m3u8")
except Exception as e:
    print(f"✅ CORRECTO - Error esperado: {e}")

print("\n" + "="*80)
print("PRUEBA COMPLETADA")
print("="*80)

#!/usr/bin/env python3
"""
Script para reiniciar clases con 'quiz' en el título que NO son quizzes reales.
Estas son clases educativas normales (pueden contener videos/lecturas).
"""
import json
from pathlib import Path

progress_file = Path("download_progress.json")

# Leer archivo
print(f"📖 Leyendo {progress_file}...")
with open(progress_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Crear backup
backup_file = progress_file.with_suffix('.backup3.json')
print(f"💾 Creando backup en {backup_file}...")
with open(backup_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Contadores
reset_count = 0

# Procesar cada curso
for course_id, course_data in data.get('courses', {}).items():
    units = course_data.get('units', {})
    
    # Lista de unidades a eliminar (para forzar re-descarga)
    to_remove = []
    for unit_id, unit_data in units.items():
        title = unit_data.get('title', '')
        # Si tiene "quiz" en el título pero NO es del patrón /clases/quiz/
        if 'quiz' in title.lower() and '/clases/quiz/' not in unit_id:
            to_remove.append(unit_id)
    
    # Eliminar las unidades del progreso para que se vuelvan a descargar
    for unit_id in to_remove:
        unit_data = units[unit_id]
        print(f"🔄 Reiniciando: {unit_data.get('title')} [{unit_id}]")
        del units[unit_id]
        reset_count += 1

# Guardar cambios
if reset_count > 0:
    print(f"\n💾 Guardando cambios en {progress_file}...")
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Proceso completado:")
    print(f"   - Clases reiniciadas: {reset_count}")
    print(f"   - Estas clases se volverán a descargar con la nueva lógica")
    print(f"   - Backup guardado en: {backup_file}")
else:
    print(f"\n⚠️  No se encontraron clases para reiniciar")

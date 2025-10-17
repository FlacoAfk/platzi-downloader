#!/usr/bin/env python3
"""
Script para reiniciar clases con "quiz" en el título que NO son quizzes reales.
Las clases con patrón /clases/quiz/NUMBER/ son quizzes reales y se mantienen como completadas.
Las clases con "quiz" en el título pero con otros patrones de URL son clases normales y se reinician.
"""
import json
import sys
from pathlib import Path

def reset_quiz_classes():
    progress_file = Path("download_progress.json")
    
    if not progress_file.exists():
        print(f"❌ Error: No se encontró el archivo {progress_file}")
        sys.exit(1)
    
    # Leer archivo
    print(f"📖 Leyendo {progress_file}...")
    with open(progress_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Crear backup
    backup_file = progress_file.with_suffix('.backup.json')
    print(f"💾 Creando backup en {backup_file}...")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Contadores
    reset_count = 0
    kept_count = 0
    
    # Procesar cada curso
    for course_id, course_data in data.get("courses", {}).items():
        units = course_data.get("units", {})
        
        for unit_id, unit_data in list(units.items()):
            title = unit_data.get("title", "").lower()
            
            # Si tiene "quiz" en el título
            if "quiz" in title:
                # Verificar si es un quiz real (patrón /clases/quiz/)
                if "/clases/quiz/" in unit_id:
                    # Es un quiz real, mantenerlo completado
                    kept_count += 1
                    print(f"✅ Mantenido (quiz real): {unit_data.get('title')}")
                else:
                    # Es una clase normal con "quiz" en el título, reiniciarla
                    if unit_data.get("status") == "completed":
                        # Eliminar la entrada para que se vuelva a descargar
                        del units[unit_id]
                        reset_count += 1
                        print(f"🔄 Reiniciado: {unit_data.get('title')} [{unit_id}]")
    
    # Guardar cambios
    if reset_count > 0:
        print(f"\n💾 Guardando cambios en {progress_file}...")
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Proceso completado:")
        print(f"   - Clases reiniciadas: {reset_count}")
        print(f"   - Quizzes reales mantenidos: {kept_count}")
        print(f"   - Backup guardado en: {backup_file}")
    else:
        print(f"\n⚠️  No se encontraron clases normales con 'quiz' en el título para reiniciar")
        print(f"   - Quizzes reales encontrados: {kept_count}")

if __name__ == "__main__":
    reset_quiz_classes()

#!/usr/bin/env python3
"""
Script para ELIMINAR del progreso todas las unidades con el patrón /clases/quiz/
Esto permite que se vuelvan a evaluar con la nueva lógica que los descarta automáticamente.
"""
import json
import sys
from pathlib import Path

def reset_quiz_pattern():
    progress_file = Path("download_progress.json")
    
    if not progress_file.exists():
        print(f"❌ Error: No se encontró el archivo {progress_file}")
        sys.exit(1)
    
    # Leer archivo
    print(f"📖 Leyendo {progress_file}...")
    with open(progress_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Crear backup
    backup_file = progress_file.with_suffix('.backup2.json')
    print(f"💾 Creando backup en {backup_file}...")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Contadores
    removed_count = 0
    
    # Procesar cada curso
    for course_id, course_data in data.get("courses", {}).items():
        units = course_data.get("units", {})
        
        # Crear lista de unidades a eliminar
        to_remove = []
        for unit_id in units.keys():
            if "/clases/quiz/" in unit_id:
                to_remove.append(unit_id)
        
        # Eliminar las unidades
        for unit_id in to_remove:
            unit_data = units[unit_id]
            print(f"🗑️  Eliminado: {unit_data.get('title')} [{unit_id}]")
            del units[unit_id]
            removed_count += 1
    
    # Guardar cambios
    if removed_count > 0:
        print(f"\n💾 Guardando cambios en {progress_file}...")
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Proceso completado:")
        print(f"   - Unidades eliminadas del progreso: {removed_count}")
        print(f"   - Estas unidades serán descartadas automáticamente en la próxima descarga")
        print(f"   - Backup guardado en: {backup_file}")
    else:
        print(f"\n⚠️  No se encontraron unidades con patrón /clases/quiz/ para eliminar")

if __name__ == "__main__":
    print("⚠️  ADVERTENCIA: Este script eliminará todas las entradas con patrón /clases/quiz/")
    print("    Estas son unidades de quizzes/exámenes que serán descartadas automáticamente.")
    response = input("\n¿Deseas continuar? (s/n): ")
    
    if response.lower() == 's':
        reset_quiz_pattern()
    else:
        print("❌ Operación cancelada")

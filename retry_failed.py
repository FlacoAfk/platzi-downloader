"""
Script para reintentar la descarga de clases con errores.
Cambia el estado de todas las clases/unidades con error a 'pending' 
para que sean reintentadas en la próxima ejecución.
"""
import json
from pathlib import Path
from datetime import datetime


def retry_failed_downloads():
    """Resetea el estado de todos los items con error a 'pending' para reintentarlos."""
    progress_file = Path("download_progress.json")
    
    if not progress_file.exists():
        print("❌ No se encontró el archivo download_progress.json")
        return
    
    # Cargar el archivo de progreso
    with open(progress_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Contadores
    courses_reset = 0
    units_reset = 0
    
    print("\n" + "="*80)
    print("🔄 RESETEO DE DESCARGAS CON ERROR")
    print("="*80 + "\n")
    
    # Resetear cursos con error
    for course_id, course_data in data.get("courses", {}).items():
        if course_data.get("status") == "failed":
            course_data["status"] = "pending"
            course_data["error"] = None
            courses_reset += 1
            print(f"🔄 Curso reseteado: {course_data.get('title', 'Sin título')}")
        
        # Resetear unidades con error dentro de cada curso
        for unit_id, unit_data in course_data.get("units", {}).items():
            if unit_data.get("status") == "failed":
                unit_data["status"] = "pending"
                unit_data["error"] = None
                units_reset += 1
                print(f"  ↳ Unidad reseteada: {unit_data.get('title', 'Sin título')}")
    
    # Limpiar la lista de errores
    errors_count = len(data.get("errors", []))
    data["errors"] = []
    
    # Actualizar timestamp
    data["last_updated"] = datetime.now().isoformat()
    
    # Guardar cambios
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print("✅ RESUMEN DEL RESETEO")
    print("="*80)
    print(f"📚 Cursos reseteados: {courses_reset}")
    print(f"📝 Unidades reseteadas: {units_reset}")
    print(f"🗑️  Errores limpiados: {errors_count}")
    print("="*80 + "\n")
    
    if courses_reset > 0 or units_reset > 0:
        print("✅ Los items con error ahora están marcados como 'pending'")
        print("💡 Ejecuta 'platzi download' o 'platzi batch-download' para reintentarlos\n")
    else:
        print("ℹ️  No se encontraron items con error para resetear\n")


if __name__ == "__main__":
    retry_failed_downloads()

"""
Script para verificar cursos con unidades pendientes.
Muestra qué cursos tienen unidades pendientes y serán re-procesados.
"""
import json
from pathlib import Path


def check_courses_with_pending_units():
    """Verifica y muestra cursos con unidades pendientes."""
    progress_file = Path("download_progress.json")
    
    if not progress_file.exists():
        print("❌ No se encontró el archivo download_progress.json")
        return
    
    with open(progress_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "="*100)
    print("🔍 CURSOS CON UNIDADES PENDIENTES")
    print("="*100 + "\n")
    
    courses_with_pending = []
    
    for course_id, course_data in data.get("courses", {}).items():
        course_title = course_data.get("title", "Sin título")
        course_status = course_data.get("status", "unknown")
        
        # Contar unidades por estado
        pending_units = []
        failed_units = []
        in_progress_units = []
        completed_units = 0
        
        for unit_id, unit_data in course_data.get("units", {}).items():
            unit_status = unit_data.get("status", "unknown")
            unit_title = unit_data.get("title", "Sin título")
            
            if unit_status == "pending":
                pending_units.append(unit_title)
            elif unit_status == "failed":
                failed_units.append(unit_title)
            elif unit_status == "in_progress":
                in_progress_units.append(unit_title)
            elif unit_status == "completed":
                completed_units += 1
        
        # Si tiene unidades pendientes, con error o en progreso
        total_pending = len(pending_units) + len(failed_units) + len(in_progress_units)
        
        if total_pending > 0:
            courses_with_pending.append({
                'title': course_title,
                'id': course_id,
                'status': course_status,
                'pending': pending_units,
                'failed': failed_units,
                'in_progress': in_progress_units,
                'completed': completed_units,
                'total_pending': total_pending
            })
    
    if not courses_with_pending:
        print("✅ No hay cursos con unidades pendientes")
        print("   Todos los cursos están completamente descargados\n")
        return
    
    print(f"📊 Se encontraron {len(courses_with_pending)} cursos con unidades pendientes:\n")
    
    for idx, course_info in enumerate(courses_with_pending, 1):
        print(f"{idx}. 📚 {course_info['title']}")
        print(f"   Estado del curso: {course_info['status']}")
        print(f"   ✅ Completadas: {course_info['completed']}")
        
        if course_info['pending']:
            print(f"   ⏸️  Pendientes: {len(course_info['pending'])}")
            for unit in course_info['pending'][:3]:
                print(f"      • {unit}")
            if len(course_info['pending']) > 3:
                print(f"      ... y {len(course_info['pending']) - 3} más")
        
        if course_info['failed']:
            print(f"   ❌ Con error: {len(course_info['failed'])}")
            for unit in course_info['failed'][:3]:
                print(f"      • {unit}")
            if len(course_info['failed']) > 3:
                print(f"      ... y {len(course_info['failed']) - 3} más")
        
        if course_info['in_progress']:
            print(f"   🔄 En progreso: {len(course_info['in_progress'])}")
            for unit in course_info['in_progress'][:3]:
                print(f"      • {unit}")
            if len(course_info['in_progress']) > 3:
                print(f"      ... y {len(course_info['in_progress']) - 3} más")
        
        print()
    
    print("="*100)
    print("\n💡 Estos cursos serán RE-PROCESADOS cuando ejecutes 'platzi batch-download'")
    print("   Solo se descargarán las unidades pendientes/con error/en progreso")
    print("   Las unidades completadas se saltarán automáticamente\n")
    
    print("="*100 + "\n")


if __name__ == "__main__":
    check_courses_with_pending_units()

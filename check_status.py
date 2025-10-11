"""
Script para verificar el estado actual de las descargas.
Muestra estadísticas detalladas del progreso, errores y items pendientes.
"""
import json
from pathlib import Path
from datetime import datetime


def format_timestamp(timestamp_str):
    """Formatea un timestamp ISO a un formato legible."""
    if not timestamp_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str


def check_download_status():
    """Verifica y muestra el estado actual de las descargas."""
    progress_file = Path("download_progress.json")
    
    if not progress_file.exists():
        print("❌ No se encontró el archivo download_progress.json")
        print("💡 Ejecuta primero 'platzi download' o 'platzi batch-download'\n")
        return
    
    # Cargar el archivo de progreso
    with open(progress_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Contadores
    stats = {
        'total_courses': 0,
        'completed_courses': 0,
        'failed_courses': 0,
        'pending_courses': 0,
        'in_progress_courses': 0,
        'total_units': 0,
        'completed_units': 0,
        'failed_units': 0,
        'pending_units': 0,
        'in_progress_units': 0,
    }
    
    failed_courses = []
    failed_units = []
    pending_courses = []
    pending_units = []
    
    # Analizar cursos
    for course_id, course_data in data.get("courses", {}).items():
        stats['total_courses'] += 1
        status = course_data.get("status", "unknown")
        
        if status == "completed":
            stats['completed_courses'] += 1
        elif status == "failed":
            stats['failed_courses'] += 1
            failed_courses.append((course_data.get('title', 'Sin título'), course_data.get('error', 'Sin error especificado')))
        elif status == "pending":
            stats['pending_courses'] += 1
            pending_courses.append(course_data.get('title', 'Sin título'))
        elif status == "in_progress":
            stats['in_progress_courses'] += 1
        
        # Analizar unidades dentro de cada curso
        for unit_id, unit_data in course_data.get("units", {}).items():
            stats['total_units'] += 1
            unit_status = unit_data.get("status", "unknown")
            
            if unit_status == "completed":
                stats['completed_units'] += 1
            elif unit_status == "failed":
                stats['failed_units'] += 1
                failed_units.append((
                    course_data.get('title', 'Sin título'),
                    unit_data.get('title', 'Sin título'),
                    unit_data.get('error', 'Sin error especificado')
                ))
            elif unit_status == "pending":
                stats['pending_units'] += 1
                pending_units.append((
                    course_data.get('title', 'Sin título'),
                    unit_data.get('title', 'Sin título')
                ))
            elif unit_status == "in_progress":
                stats['in_progress_units'] += 1
    
    # Mostrar resultados
    print("\n" + "="*100)
    print("📊 ESTADO ACTUAL DE LAS DESCARGAS")
    print("="*100 + "\n")
    
    # Información de sesión
    print("📅 Información de la Sesión:")
    print(f"   Iniciada: {format_timestamp(data.get('started_at'))}")
    print(f"   Última actualización: {format_timestamp(data.get('last_updated'))}")
    print()
    
    # Estadísticas generales
    print("📈 Estadísticas Generales:")
    print(f"   📚 Cursos Totales: {stats['total_courses']}")
    print(f"      ✅ Completados: {stats['completed_courses']} ({stats['completed_courses']/max(stats['total_courses'], 1)*100:.1f}%)")
    print(f"      ❌ Con Error: {stats['failed_courses']}")
    print(f"      ⏸️  Pendientes: {stats['pending_courses']}")
    print(f"      🔄 En Progreso: {stats['in_progress_courses']}")
    print()
    
    print(f"   📝 Unidades Totales: {stats['total_units']}")
    print(f"      ✅ Completadas: {stats['completed_units']} ({stats['completed_units']/max(stats['total_units'], 1)*100:.1f}%)")
    print(f"      ❌ Con Error: {stats['failed_units']}")
    print(f"      ⏸️  Pendientes: {stats['pending_units']}")
    print(f"      🔄 En Progreso: {stats['in_progress_units']}")
    print()
    
    # Rutas de aprendizaje
    if data.get("learning_paths"):
        print("🗂️  Rutas de Aprendizaje:")
        for path_id, path_data in data["learning_paths"].items():
            status_icon = "✅" if path_data["status"] == "completed" else "🔄"
            print(f"   {status_icon} {path_data['title']}")
            print(f"      Cursos: {path_data['completed_courses']}/{path_data['total_courses']} completados")
        print()
    
    # Cursos pendientes
    if pending_courses:
        print("⏸️  Cursos Pendientes:")
        for title in pending_courses[:10]:
            print(f"   • {title}")
        if len(pending_courses) > 10:
            print(f"   ... y {len(pending_courses) - 10} más")
        print()
    
    # Unidades pendientes
    if pending_units:
        print("⏸️  Unidades Pendientes:")
        for course_title, unit_title in pending_units[:10]:
            print(f"   • {course_title}")
            print(f"     ↳ {unit_title}")
        if len(pending_units) > 10:
            print(f"   ... y {len(pending_units) - 10} más")
        print()
    
    # Cursos con error
    if failed_courses:
        print("❌ Cursos con Error:")
        for title, error in failed_courses[:5]:
            print(f"   • {title}")
            print(f"     Error: {error}")
        if len(failed_courses) > 5:
            print(f"   ... y {len(failed_courses) - 5} más")
        print()
    
    # Unidades con error
    if failed_units:
        print("❌ Unidades con Error:")
        for course_title, unit_title, error in failed_units[:10]:
            print(f"   • {course_title}")
            print(f"     ↳ {unit_title}")
            print(f"     Error: {error}")
        if len(failed_units) > 10:
            print(f"   ... y {len(failed_units) - 10} más")
        print()
    
    # Lista completa de errores
    errors = data.get("errors", [])
    if errors:
        print(f"🗃️  Registro de Errores: {len(errors)} errores totales")
        print("   (Ver download_progress.json para detalles completos)")
        print()
    
    print("="*100)
    
    # Recomendaciones
    print("\n💡 Recomendaciones:")
    if stats['failed_courses'] > 0 or stats['failed_units'] > 0:
        print("   • Hay items con errores. Ejecuta 'python retry_failed.py' para reintentarlos")
    if stats['pending_courses'] > 0 or stats['pending_units'] > 0:
        print("   • Hay items pendientes. Ejecuta 'platzi batch-download' para continuar")
    if stats['failed_courses'] == 0 and stats['failed_units'] == 0 and stats['pending_courses'] == 0 and stats['pending_units'] == 0:
        if stats['total_courses'] > 0:
            print("   • ✅ ¡Todas las descargas están completas!")
        else:
            print("   • No hay descargas registradas aún")
    print()


if __name__ == "__main__":
    check_download_status()

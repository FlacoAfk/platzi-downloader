"""
Script de gestión completa de descargas de Platzi.
Facilita verificar estado, reintentar errores y continuar descargas.
"""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def show_menu():
    """Muestra el menú principal."""
    print("\n" + "="*80)
    print("🎓 GESTOR DE DESCARGAS PLATZI")
    print("="*80)
    print("\n📋 Opciones disponibles:")
    print("   1. 📊 Ver estado actual de descargas")
    print("   2. 🔄 Reintentar descargas con error")
    print("   3. 🔍 Ver cursos con unidades pendientes")
    print("   4. ▶️  Continuar/Iniciar descargas batch")
    print("   5. 📝 Ver últimos errores")
    print("   6. 🗑️  Limpiar errores sin cambiar estado")
    print("   7. ❌ Salir")
    print("\n" + "="*80)


def load_progress():
    """Carga el archivo de progreso."""
    progress_file = Path("download_progress.json")
    if not progress_file.exists():
        return None
    
    with open(progress_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_progress(data):
    """Guarda el archivo de progreso."""
    progress_file = Path("download_progress.json")
    data["last_updated"] = datetime.now().isoformat()
    
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def show_status():
    """Muestra el estado actual."""
    print("\n⏳ Cargando estado...")
    subprocess.run([sys.executable, "check_status.py"])
    input("\n✅ Presiona Enter para continuar...")


def retry_failed():
    """Reintenta las descargas con error."""
    print("\n⏳ Procesando...")
    subprocess.run([sys.executable, "retry_failed.py"])
    input("\n✅ Presiona Enter para continuar...")


def continue_downloads():
    """Continúa con las descargas batch."""
    print("\n" + "="*80)
    print("▶️  CONTINUAR DESCARGAS")
    print("="*80)
    
    # Verificar si existe urls.txt
    urls_file = Path("urls.txt")
    if not urls_file.exists():
        print("\n❌ No se encontró el archivo 'urls.txt'")
        print("💡 Crea un archivo 'urls.txt' con las URLs de los cursos a descargar")
        input("\n✅ Presiona Enter para continuar...")
        return
    
    print("\n📂 Archivo de URLs encontrado: urls.txt")
    
    # Mostrar opciones
    print("\n¿Qué comando deseas ejecutar?")
    print("   1. platzi batch-download (descarga batch)")
    print("   2. platzi download <url> (descarga individual)")
    print("   3. Volver al menú")
    
    choice = input("\nSelecciona una opción (1-3): ").strip()
    
    if choice == "1":
        print("\n🚀 Iniciando descarga batch...")
        print("💡 Para detener: Presiona Ctrl + C")
        print("="*80 + "\n")
        input("Presiona Enter para comenzar...")
        subprocess.run(["platzi", "batch-download"])
    elif choice == "2":
        url = input("\n📝 Ingresa la URL del curso: ").strip()
        if url:
            print(f"\n🚀 Descargando: {url}")
            print("💡 Para detener: Presiona Ctrl + C")
            print("="*80 + "\n")
            subprocess.run(["platzi", "download", url])
        else:
            print("❌ URL no válida")
    
    input("\n✅ Presiona Enter para continuar...")


def show_last_errors():
    """Muestra los últimos errores."""
    data = load_progress()
    
    if not data:
        print("\n❌ No se encontró el archivo de progreso")
        input("\n✅ Presiona Enter para continuar...")
        return
    
    errors = data.get("errors", [])
    
    print("\n" + "="*80)
    print("📝 ÚLTIMOS ERRORES")
    print("="*80)
    
    if not errors:
        print("\n✅ No hay errores registrados")
    else:
        print(f"\n📊 Total de errores: {len(errors)}")
        print("\n🔍 Últimos 20 errores:")
        
        for idx, error in enumerate(errors[-20:], 1):
            print(f"\n{idx}. [{error.get('type', 'unknown').upper()}] {error.get('title', 'Sin título')}")
            print(f"   Error: {error.get('error', 'Sin descripción')}")
            print(f"   Fecha: {error.get('timestamp', 'N/A')}")
    
    print("\n" + "="*80)
    input("\n✅ Presiona Enter para continuar...")


def clear_error_log():
    """Limpia el registro de errores sin cambiar estados."""
    data = load_progress()
    
    if not data:
        print("\n❌ No se encontró el archivo de progreso")
        input("\n✅ Presiona Enter para continuar...")
        return
    
    errors_count = len(data.get("errors", []))
    
    print("\n" + "="*80)
    print("🗑️  LIMPIAR REGISTRO DE ERRORES")
    print("="*80)
    
    print(f"\n📊 Errores registrados: {errors_count}")
    print("\n⚠️  NOTA: Esto solo limpiará el historial de errores.")
    print("   Los items con estado 'failed' NO cambiarán a 'pending'.")
    print("   Para reintentar errores, usa la opción 2 del menú principal.")
    
    if errors_count == 0:
        print("\n✅ No hay errores para limpiar")
        input("\n✅ Presiona Enter para continuar...")
        return
    
    confirm = input("\n¿Continuar? (s/n): ").strip().lower()
    
    if confirm == 's':
        data["errors"] = []
        save_progress(data)
        print(f"\n✅ Se limpiaron {errors_count} errores del registro")
    else:
        print("\n❌ Operación cancelada")
    
    input("\n✅ Presiona Enter para continuar...")


def check_pending_units():
    """Verifica cursos con unidades pendientes."""
    print("\n⏳ Verificando cursos con unidades pendientes...")
    subprocess.run([sys.executable, "check_pending_units.py"])
    input("\n✅ Presiona Enter para continuar...")


def main():
    """Función principal."""
    while True:
        show_menu()
        
        choice = input("\n👉 Selecciona una opción (1-7): ").strip()
        
        if choice == "1":
            show_status()
        elif choice == "2":
            retry_failed()
        elif choice == "3":
            check_pending_units()
        elif choice == "4":
            continue_downloads()
        elif choice == "5":
            show_last_errors()
        elif choice == "6":
            clear_error_log()
        elif choice == "7":
            print("\n👋 ¡Hasta pronto!")
            print("="*80 + "\n")
            break
        else:
            print("\n❌ Opción no válida. Intenta de nuevo.")
            input("\n✅ Presiona Enter para continuar...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        print("👋 ¡Hasta pronto!")
        print("="*80 + "\n")
        sys.exit(0)

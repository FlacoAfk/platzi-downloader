"""
Script de ayuda visual para mostrar instrucciones rápidas.
Muestra los comandos más comunes para gestionar descargas.
"""


def show_help():
    """Muestra la ayuda visual."""
    print("\n" + "="*100)
    print("🎓 PLATZI DOWNLOADER - AYUDA RÁPIDA")
    print("="*100 + "\n")
    
    print("📋 COMANDOS MÁS COMUNES:\n")
    
    print("1️⃣  ACTIVAR ENTORNO VIRTUAL (Siempre primero)")
    print("   " + "─"*90)
    print(r"   .\.venv\Scripts\Activate.ps1")
    print()
    
    print("2️⃣  GESTOR INTERACTIVO (⭐ La forma más fácil)")
    print("   " + "─"*90)
    print("   python manage_downloads.py")
    print("   → Menú interactivo con todas las opciones")
    print()
    
    print("3️⃣  VER ESTADO DE DESCARGAS")
    print("   " + "─"*90)
    print("   python check_status.py")
    print("   → Muestra progreso, errores y pendientes")
    print()
    
    print("4️⃣  REINTENTAR ERRORES")
    print("   " + "─"*90)
    print("   python retry_failed.py")
    print("   → Cambia estado de errores a 'pending' para reintentarlos")
    print()
    
    print("5️⃣  CONTINUAR/INICIAR DESCARGAS")
    print("   " + "─"*90)
    print("   platzi batch-download")
    print("   → Descarga cursos desde urls.txt")
    print()
    print("   platzi download <url>")
    print("   → Descarga un curso específico")
    print()
    
    print("6️⃣  DETENER DESCARGA EN PROGRESO")
    print("   " + "─"*90)
    print("   Ctrl + C")
    print("   → Detiene de forma segura (el progreso se guarda)")
    print()
    
    print("7️⃣  LIMPIAR CACHÉ")
    print("   " + "─"*90)
    print("   platzi clear-cache")
    print("   → Limpia el caché de Platzi")
    print()
    
    print("="*100)
    print("📖 DOCUMENTACIÓN COMPLETA:")
    print("="*100)
    print("   • INSTRUCCIONES_TU_CASO.md    → Instrucciones específicas para tu situación actual")
    print("   • GUIA_RAPIDA.md              → Guía de referencia rápida")
    print("   • GUIA_DETENER_Y_REINTENTAR.md → Guía detallada paso a paso")
    print("   • TOOLS.md                    → Documentación de herramientas disponibles")
    print("="*100)
    
    print("\n🎯 FLUJO DE TRABAJO RECOMENDADO:\n")
    print(r"   1. .\.venv\Scripts\Activate.ps1       ← Activar entorno")
    print("   2. python manage_downloads.py         ← Abrir gestor")
    print("   3. [Opción 1] Ver estado              ← Ver cómo van las cosas")
    print("   4. [Opción 2] Reintentar errores      ← Si hay errores")
    print("   5. [Opción 3] Continuar descargas     ← Iniciar/continuar")
    print("   6. [Ctrl + C] Detener si necesario    ← Para pausar")
    print("   7. Repetir desde paso 2               ← Hasta completar\n")
    
    print("="*100)
    print("💡 CONSEJO: Usa 'python manage_downloads.py' para todo, es la forma más fácil")
    print("="*100 + "\n")


def show_quick_start():
    """Muestra la guía de inicio rápido."""
    print("\n" + "="*100)
    print("🚀 INICIO RÁPIDO - PASOS INMEDIATOS")
    print("="*100 + "\n")
    
    print("SI TIENES EL CMD DESCARGANDO AHORA MISMO:\n")
    print("   1. Ve a la ventana del CMD")
    print("   2. Presiona: Ctrl + C")
    print("   3. Espera a que se detenga (el progreso se guarda automáticamente)\n")
    
    print("LUEGO, EN POWERSHELL:\n")
    print("   1. cd d:\\platzi-downloader")
    print(r"   2. .\.venv\Scripts\Activate.ps1")
    print("   3. python manage_downloads.py\n")
    
    print("EN EL MENÚ INTERACTIVO:\n")
    print("   → Opción 1: Ver estado actual")
    print("   → Opción 2: Reintentar errores (si los hay)")
    print("   → Opción 3: Continuar descargas\n")
    
    print("="*100)
    print("✅ ¡Eso es todo! El sistema se encarga del resto automáticamente")
    print("="*100 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        show_quick_start()
    else:
        show_help()
        
        response = input("¿Quieres ver la guía de INICIO RÁPIDO? (s/n): ").strip().lower()
        if response == 's':
            show_quick_start()

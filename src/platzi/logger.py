import sys
import traceback

from rich import print
from rich.console import Console
from rich.traceback import Traceback


class Logger:
    show_warnings = True
    is_writing = False
    debug_mode = False  # Debug mode disabled by default
    console = Console()

    @classmethod
    def error(cls, text, exception=None):
        """Log an error message. If debug_mode is enabled and exception is provided, show full traceback."""
        Logger.print(text, "ERROR:", "red")
        
        # If debug mode is enabled and we have an exception, show full traceback
        if cls.debug_mode and exception is not None:
            cls.debug_exception(exception)

    @classmethod
    def clear(cls):
        sys.stdout.write("\r" + " " * 100 + "\r")

    @classmethod
    def warning(cls, text):
        if cls.show_warnings:
            Logger.print(text, "WARNING:", "yellow")

    @classmethod
    def info(cls, text):
        Logger.print(text, "INFO:", "green")

    @classmethod
    def print(cls, text, head, color="green", end="\n"):
        cls.is_writing = True
        Logger.clear()
        print(f"[{color}]{head} {text}[/{color}]", end=end, flush=True)
        cls.is_writing = False

    @classmethod
    def clear_and_print(cls, text):
        cls.is_writing = True
        Logger.clear()
        print(text, flush=True)
        cls.is_writing = False
    
    @classmethod
    def debug(cls, text):
        """Log a debug message (only shown when debug_mode is enabled)."""
        if cls.debug_mode:
            Logger.print(text, "DEBUG:", "blue")
    
    @classmethod
    def debug_exception(cls, exception):
        """Log detailed exception information (only shown when debug_mode is enabled)."""
        if cls.debug_mode:
            cls.is_writing = True
            Logger.clear()
            print("\n[bold red]═══════════════════════════════════════════════════════════════════════[/bold red]")
            print("[bold red]🐛 DEBUG MODE: Detailed Exception Information[/bold red]")
            print("[bold red]═══════════════════════════════════════════════════════════════════════[/bold red]")
            
            # Show exception type and message
            print(f"\n[yellow]Exception Type:[/yellow] [red]{type(exception).__name__}[/red]")
            print(f"[yellow]Exception Message:[/yellow] [red]{str(exception)}[/red]\n")
            
            # Show full traceback using rich's Traceback for better formatting
            try:
                tb = Traceback.from_exception(
                    type(exception),
                    exception,
                    exception.__traceback__,
                    show_locals=True  # Show local variables
                )
                cls.console.print(tb)
            except Exception:
                # Fallback to standard traceback if rich fails
                print("[red]Full Traceback:[/red]")
                traceback.print_exception(type(exception), exception, exception.__traceback__)
            
            print("\n[bold red]═══════════════════════════════════════════════════════════════════════[/bold red]\n")
            cls.is_writing = False
    
    @classmethod
    def set_debug_mode(cls, enabled: bool):
        """Enable or disable debug mode."""
        cls.debug_mode = enabled
        if enabled:
            Logger.info("🐛 Debug mode ENABLED - Detailed error information will be shown")
        else:
            Logger.info("Debug mode disabled")

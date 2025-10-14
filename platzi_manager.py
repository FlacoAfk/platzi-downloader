#!/usr/bin/env python3
"""
Platzi Download Manager - Herramienta Consolidada
===================================================

Gestión completa del sistema de descargas:
- Ver estado detallado
- Limpiar tracking de archivos eliminados
- Resetear cursos/unidades para re-descarga
- Verificar archivos faltantes
- Reintentar errores

Compatible con el sistema de trazabilidad v2.0
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI colors for better readability
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class ProgressManager:
    """Manages download progress tracking."""
    
    def __init__(self, checkpoint_file: str = "download_progress.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.data = None
        self._load()
    
    def _load(self):
        """Load checkpoint file."""
        if not self.checkpoint_file.exists():
            print(f"❌ Checkpoint file not found: {self.checkpoint_file}")
            print(f"💡 Run 'platzi download <URL>' first to create it")
            return False
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            print(f"❌ Error loading checkpoint: {e}")
            return False
    
    def _save(self):
        """Save checkpoint file."""
        try:
            self.data["last_updated"] = datetime.now().isoformat()
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error saving checkpoint: {e}")
            return False
    
    def _backup(self):
        """Create backup before modifying."""
        backup_path = self.checkpoint_file.with_suffix('.json.backup')
        try:
            shutil.copy2(self.checkpoint_file, backup_path)
            print(f"💾 Backup created: {backup_path}")
            return True
        except Exception as e:
            print(f"⚠️  Could not create backup: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get current statistics."""
        if not self.data:
            return {}
        
        stats = {
            'total_courses': len(self.data.get("courses", {})),
            'completed_courses': 0,
            'failed_courses': 0,
            'in_progress_courses': 0,
            'total_units': 0,
            'completed_units': 0,
            'failed_units': 0,
            'in_progress_units': 0,
            'pending_units': 0,
        }
        
        for course_data in self.data.get("courses", {}).values():
            status = course_data.get("status", "")
            if status == "completed":
                stats['completed_courses'] += 1
            elif status == "failed":
                stats['failed_courses'] += 1
            elif status == "in_progress":
                stats['in_progress_courses'] += 1
            
            for unit_data in course_data.get("units", {}).values():
                stats['total_units'] += 1
                unit_status = unit_data.get("status", "")
                if unit_status == "completed":
                    stats['completed_units'] += 1
                elif unit_status == "failed":
                    stats['failed_units'] += 1
                elif unit_status == "in_progress":
                    stats['in_progress_units'] += 1
                elif unit_status == "pending":
                    stats['pending_units'] += 1
        
        return stats
    
    def show_status(self, verbose: bool = False):
        """Display detailed status."""
        if not self.data:
            return
        
        print("\n" + "="*100)
        print("📊 DOWNLOAD STATUS - Platzi Downloader")
        print("="*100 + "\n")
        
        # Session info
        print("📅 Session Info:")
        print(f"   Started: {self._format_timestamp(self.data.get('started_at'))}")
        print(f"   Last updated: {self._format_timestamp(self.data.get('last_updated'))}")
        if "_metadata" in self.data:
            print(f"   Tracker version: {self.data['_metadata'].get('version', '1.0')}")
            if self.data['_metadata'].get('last_validation'):
                print(f"   Last validation: {self._format_timestamp(self.data['_metadata']['last_validation'])}")
        print()
        
        # Statistics
        stats = self.get_statistics()
        print("📈 Statistics:")
        print(f"   📚 Courses: {stats['completed_courses']}/{stats['total_courses']} completed")
        if stats['failed_courses'] > 0:
            print(f"      ❌ Failed: {stats['failed_courses']}")
        if stats['in_progress_courses'] > 0:
            print(f"      🔄 In progress: {stats['in_progress_courses']}")
        
        print(f"   📝 Units: {stats['completed_units']}/{stats['total_units']} completed")
        if stats['failed_units'] > 0:
            print(f"      ❌ Failed: {stats['failed_units']}")
        if stats['in_progress_units'] > 0:
            print(f"      🔄 In progress: {stats['in_progress_units']}")
        if stats['pending_units'] > 0:
            print(f"      ⏸️  Pending: {stats['pending_units']}")
        print()
        
        # Learning paths
        if self.data.get("learning_paths"):
            print("🗂️  Learning Paths:")
            for path_data in self.data["learning_paths"].values():
                status_icon = "✅" if path_data["status"] == "completed" else "🔄"
                print(f"   {status_icon} {path_data['title']}: {path_data['completed_courses']}/{path_data['total_courses']} courses")
            print()
        
        # Courses with pending units
        courses_with_pending = []
        for course_id, course_data in self.data.get("courses", {}).items():
            pending_count = sum(1 for u in course_data.get("units", {}).values() 
                              if u.get("status") in ["pending", "failed", "in_progress"])
            if pending_count > 0:
                courses_with_pending.append((course_data.get("title", "Unknown"), pending_count))
        
        if courses_with_pending:
            print(f"⏳ Courses with Pending Work ({len(courses_with_pending)}):")
            for title, count in courses_with_pending[:10]:
                print(f"   • {title}: {count} units pending")
            if len(courses_with_pending) > 10:
                print(f"   ... and {len(courses_with_pending) - 10} more")
            print()
        
        # Recent errors
        errors = self.data.get("errors", [])
        if errors:
            print(f"❌ Recent Errors ({len(errors)} total, showing last 5):")
            for error in errors[-5:]:
                print(f"   • [{error.get('type', 'unknown').upper()}] {error.get('title', 'Unknown')}")
                print(f"     {error.get('error', 'No description')[:80]}...")
            print()
        
        print("="*100)
        
        # Recommendations
        print("\n💡 Recommendations:")
        if stats['failed_units'] > 0 or stats['failed_courses'] > 0:
            print("   • Run with --retry-failed to retry failed downloads")
        if courses_with_pending:
            print("   • Run 'platzi download <URL>' to continue incomplete courses")
        if stats['completed_courses'] == stats['total_courses'] and stats['total_courses'] > 0:
            print("   • ✅ All downloads complete!")
        print()
    
    def _format_timestamp(self, timestamp_str):
        """Format ISO timestamp to readable format."""
        if not timestamp_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return timestamp_str
    
    def retry_failed(self, course_id: str = None, dry_run: bool = False) -> int:
        """Mark failed units as pending for retry."""
        if not self.data:
            return 0
        
        retried_count = 0
        
        if not dry_run:
            self._backup()
        
        for cid, course_data in self.data.get("courses", {}).items():
            if course_id and cid != course_id:
                continue
            
            for unit_id, unit_data in course_data.get("units", {}).items():
                if unit_data.get("status") == "failed":
                    if dry_run:
                        print(f"   Would retry: {course_data.get('title')} / {unit_data.get('title')}")
                    else:
                        unit_data["status"] = "pending"
                        unit_data["error"] = None
                    retried_count += 1
        
        if retried_count > 0 and not dry_run:
            self._save()
            print(f"✅ Marked {retried_count} failed units as pending for retry")
        elif retried_count == 0:
            print("✅ No failed units found")
        
        return retried_count
    
    def reset_course(self, course_pattern: str, dry_run: bool = False) -> int:
        """Reset a course for complete re-download."""
        if not self.data:
            return 0
        
        if not dry_run:
            self._backup()
        
        courses_reset = 0
        course_pattern_lower = course_pattern.lower()
        
        for course_id, course_data in list(self.data.get("courses", {}).items()):
            course_title = course_data.get("title", "").lower()
            
            if course_pattern_lower in course_title or course_pattern_lower in course_id.lower():
                if dry_run:
                    print(f"   Would reset: {course_data.get('title')}")
                else:
                    del self.data["courses"][course_id]
                    print(f"🔄 Reset: {course_data.get('title')}")
                courses_reset += 1
        
        if courses_reset > 0:
            if dry_run:
                print(f"\n[DRY-RUN] Would reset {courses_reset} course(s)")
            else:
                self._save()
                print(f"\n✅ Reset {courses_reset} course(s). Run 'platzi download <URL>' to re-download")
        else:
            print(f"❌ No courses matching '{course_pattern}' found")
        
        return courses_reset
    
    def clean_tracking(self, dry_run: bool = False) -> Tuple[int, int]:
        """Remove tracking entries for non-existent files."""
        if not self.data:
            return 0, 0
        
        if not dry_run:
            self._backup()
        
        courses_base = Path("Courses")
        if not courses_base.exists():
            print("❌ Courses directory not found")
            return 0, 0
        
        courses_removed = 0
        units_removed = 0
        empty_dirs = 0
        
        print("\n🔍 Checking for missing files...")
        
        for course_id, course_data in list(self.data.get("courses", {}).items()):
            course_title = course_data.get("title", "Unknown")
            
            # Only check completed courses
            if course_data.get("status") != "completed":
                continue
            
            # Try to find course directory
            course_dir = self._find_course_directory(courses_base, course_title)
            
            if not course_dir:
                # Check if it's an empty directory
                clean_title = self._clean_string(course_title, max_length=80)
                direct_path = courses_base / clean_title
                
                # Also check in learning paths for empty dirs
                found_empty = False
                for learning_path in courses_base.iterdir():
                    if not learning_path.is_dir():
                        continue
                    for course_dir_check in learning_path.iterdir():
                        if course_dir_check.is_dir() and clean_title in course_dir_check.name:
                            if not any(course_dir_check.iterdir()):
                                found_empty = True
                                empty_dirs += 1
                                print(f"  📁 Empty directory (no files): {course_title}")
                                break
                    if found_empty:
                        break
                
                if not found_empty:
                    print(f"  ❌ Missing directory: {course_title}")
                
                if not dry_run:
                    del self.data["courses"][course_id]
                courses_removed += 1
                continue
            
            # Check units
            units = course_data.get("units", {})
            for unit_id, unit_data in list(units.items()):
                if unit_data.get("status") != "completed":
                    continue
                
                unit_title = unit_data.get("title", "Unknown")
                # Simplified check: just verify course dir exists
                # Actual file checking is complex due to naming variations
                if not course_dir.exists():
                    print(f"    ❌ Missing unit: {unit_title}")
                    if not dry_run:
                        del course_data["units"][unit_id]
                    units_removed += 1
        
        if not dry_run and (courses_removed > 0 or units_removed > 0):
            self._save()
        
        if empty_dirs > 0:
            print(f"\n💡 Note: {empty_dirs} course(s) have empty directories (no files inside)")
            print(f"   These directories exist but contain no downloaded content")
        
        return courses_removed, units_removed
    
    def _find_course_directory(self, courses_base: Path, course_title: str) -> Path:
        """Try to find course directory with flexible matching."""
        # Clean title for comparison
        clean_title = self._clean_string(course_title, max_length=80)
        
        # Normalize for comparison: remove punctuation, extra spaces, lowercase
        def normalize(text):
            import re
            # Remove common punctuation
            text = text.replace(':', '').replace('.', '').replace(',', '').replace('¿', '').replace('?', '')
            # Replace multiple spaces with single space
            text = re.sub(r'\s+', ' ', text)
            # Lowercase and strip
            return text.lower().strip()
        
        # Get both full and truncated normalized versions
        original_normalized = normalize(course_title)
        clean_normalized = normalize(clean_title)
        
        # Also create a "core" version (first 50 chars of normalized)
        core_normalized = original_normalized[:50] if len(original_normalized) > 50 else original_normalized
        
        # Try direct path (exact match)
        direct_path = courses_base / clean_title
        if direct_path.exists() and direct_path.is_dir():
            # Check if directory has content
            try:
                if any(direct_path.iterdir()):
                    return direct_path
            except:
                pass
        
        # Try in learning paths (subdirectories) with flexible matching
        for learning_path in courses_base.iterdir():
            if not learning_path.is_dir():
                continue
            
            for course_dir in learning_path.iterdir():
                if not course_dir.is_dir():
                    continue
                
                # Check if directory has content
                try:
                    if not any(course_dir.iterdir()):
                        continue
                except:
                    continue
                
                # Normalize the directory name and remove numeric prefixes (e.g., "1. ", "10. ")
                dir_name = course_dir.name
                
                # Remove numeric prefix if present (e.g., "1. Curso..." -> "Curso...")
                import re
                dir_name = re.sub(r'^\d+\.\s*', '', dir_name)
                
                course_dir_normalized = normalize(dir_name)
                
                # Multiple matching strategies (from most specific to most flexible)
                # Strategy 1: Exact match after normalization
                if original_normalized == course_dir_normalized or clean_normalized == course_dir_normalized:
                    return course_dir
                
                # Strategy 2: One is substring of the other (for truncated names)
                # Be more lenient with truncated names (at least 40 chars match)
                # BUT: Make sure it's not a false positive (e.g., "html" in "practico de html")
                min_match_len = 40
                
                if len(original_normalized) >= min_match_len and len(course_dir_normalized) >= min_match_len:
                    # Check if one is substring of the other
                    if course_dir_normalized in original_normalized:
                        # course_dir is substring of original (truncation case)
                        return course_dir
                    elif original_normalized in course_dir_normalized:
                        # original is substring of course_dir (should be rare, but possible)
                        # Additional check: make sure the match is at the beginning (not random substring)
                        if course_dir_normalized.startswith(original_normalized[:30]):
                            return course_dir
                
                if len(clean_normalized) >= min_match_len and len(course_dir_normalized) >= min_match_len:
                    if course_dir_normalized in clean_normalized:
                        return course_dir
                    elif clean_normalized in course_dir_normalized:
                        if course_dir_normalized.startswith(clean_normalized[:30]):
                            return course_dir
                
                # Strategy 3: Core match (first 50 chars) for very long names
                course_dir_core = course_dir_normalized[:50] if len(course_dir_normalized) > 50 else course_dir_normalized
                
                # Match if cores are very similar (at least 45 chars)
                if len(core_normalized) >= 45 and len(course_dir_core) >= 45:
                    if core_normalized[:45] == course_dir_core[:45]:
                        return course_dir
                
                # For shorter cores, allow substring matching
                if core_normalized == course_dir_core or (len(core_normalized) > 30 and core_normalized in course_dir_core):
                    return course_dir
                
                # Also try: if course_dir is very similar to start of original
                if len(course_dir_normalized) >= 50 and course_dir_normalized == original_normalized[:len(course_dir_normalized)]:
                    return course_dir
                
                # Strategy 4: Remove common prefixes and match
                # Remove "Curso de ", "Curso ", etc.
                # BUT: Only if the remaining text is long enough to avoid false positives
                def remove_prefix(text):
                    prefixes = ['curso de ', 'curso ', 'audiocurso de ', 'audiocurso ']
                    for prefix in prefixes:
                        if text.startswith(prefix):
                            return text[len(prefix):]
                    return text
                
                original_no_prefix = remove_prefix(original_normalized)
                clean_no_prefix = remove_prefix(clean_normalized)
                dir_no_prefix = remove_prefix(course_dir_normalized)
                
                # Only match if the remaining text is substantial (>15 chars) to avoid false positives
                # e.g., "html" shouldn't match "practico de html y css"
                if len(original_no_prefix) > 15 and len(dir_no_prefix) > 15:
                    if original_no_prefix in dir_no_prefix or dir_no_prefix in original_no_prefix:
                        return course_dir
                
                if len(clean_no_prefix) > 15 and len(dir_no_prefix) > 15:
                    if clean_no_prefix in dir_no_prefix or dir_no_prefix in clean_no_prefix:
                        return course_dir
        
        return None
    
    def _clean_string(self, text: str, max_length: int = 80) -> str:
        """Clean string for filesystem."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, '')
        
        if len(text) > max_length:
            text = text[:max_length].rstrip()
        
        return text.strip()
    
    def list_courses(self, filter_status: str = None):
        """List all courses with their status."""
        if not self.data:
            return
        
        print("\n" + "="*100)
        print("📚 COURSES LIST")
        if filter_status:
            print(f"Filtering by status: {filter_status}")
        print("="*100 + "\n")
        
        courses = self.data.get("courses", {})
        if not courses:
            print("No courses found")
            return
        
        for idx, (course_id, course_data) in enumerate(courses.items(), 1):
            status = course_data.get("status", "unknown")
            
            if filter_status and status != filter_status:
                continue
            
            title = course_data.get("title", "Unknown")
            units = course_data.get("units", {})
            
            # Count unit statuses
            completed = sum(1 for u in units.values() if u.get("status") == "completed")
            failed = sum(1 for u in units.values() if u.get("status") == "failed")
            pending = sum(1 for u in units.values() if u.get("status") in ["pending", "in_progress"])
            
            # Status icon
            if status == "completed":
                icon = "✅"
            elif status == "failed":
                icon = "❌"
            elif status == "in_progress":
                icon = "🔄"
            else:
                icon = "⏸️"
            
            print(f"{idx}. {icon} {title}")
            print(f"   Status: {status}")
            print(f"   Units: {completed}/{len(units)} completed", end="")
            if failed > 0:
                print(f", {failed} failed", end="")
            if pending > 0:
                print(f", {pending} pending", end="")
            print()
            print(f"   ID: {course_id}")
            print()
        
        print("="*100)


def main():
    parser = argparse.ArgumentParser(
        description="Platzi Download Manager - Comprehensive download management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show status
  python platzi_manager.py --status
  
  # Show detailed status
  python platzi_manager.py --status --verbose
  
  # Retry all failed downloads
  python platzi_manager.py --retry-failed
  
  # Reset a specific course for re-download
  python platzi_manager.py --reset-course "python"
  
  # Clean tracking (remove entries for missing files)
  python platzi_manager.py --clean-tracking
  
  # Preview clean tracking (dry-run)
  python platzi_manager.py --clean-tracking --dry-run
  
  # List all courses
  python platzi_manager.py --list-courses
  
  # List only failed courses
  python platzi_manager.py --list-courses --filter-status failed
        """
    )
    
    parser.add_argument(
        '--checkpoint',
        default='download_progress.json',
        help='Path to checkpoint file (default: download_progress.json)'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show download status'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose status'
    )
    
    parser.add_argument(
        '--retry-failed',
        action='store_true',
        help='Mark failed units as pending for retry'
    )
    
    parser.add_argument(
        '--reset-course',
        metavar='PATTERN',
        help='Reset course(s) matching pattern for complete re-download'
    )
    
    parser.add_argument(
        '--clean-tracking',
        action='store_true',
        help='Remove tracking entries for non-existent files'
    )
    
    parser.add_argument(
        '--list-courses',
        action='store_true',
        help='List all courses'
    )
    
    parser.add_argument(
        '--filter-status',
        choices=['completed', 'failed', 'in_progress', 'pending'],
        help='Filter courses by status (use with --list-courses)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    
    args = parser.parse_args()
    
    # Create manager
    manager = ProgressManager(args.checkpoint)
    
    if not manager.data:
        sys.exit(1)
    
    # Execute action
    if args.status:
        manager.show_status(verbose=args.verbose)
    
    elif args.retry_failed:
        print("\n🔄 Retrying Failed Downloads")
        print("="*100 + "\n")
        if args.dry_run:
            print("⚠️  DRY-RUN MODE\n")
        count = manager.retry_failed(dry_run=args.dry_run)
        if count > 0 and not args.dry_run:
            print(f"\n💡 Now run: platzi download <URL> to retry failed units")
    
    elif args.reset_course:
        print(f"\n🔄 Resetting Course: {args.reset_course}")
        print("="*100 + "\n")
        if args.dry_run:
            print("⚠️  DRY-RUN MODE\n")
        manager.reset_course(args.reset_course, dry_run=args.dry_run)
    
    elif args.clean_tracking:
        print("\n🧹 Cleaning Tracking")
        print("="*100 + "\n")
        if args.dry_run:
            print("⚠️  DRY-RUN MODE\n")
        courses_removed, units_removed = manager.clean_tracking(dry_run=args.dry_run)
        print(f"\nSummary:")
        print(f"  Courses removed: {courses_removed}")
        print(f"  Units removed: {units_removed}")
        if not args.dry_run and (courses_removed > 0 or units_removed > 0):
            print(f"\n💡 Re-download removed items: platzi download <URL>")
    
    elif args.list_courses:
        manager.list_courses(filter_status=args.filter_status)
    
    else:
        # No action specified, show status by default
        manager.show_status()
        print("\n💡 Run with --help to see all options")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)

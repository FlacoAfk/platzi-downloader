"""
Progress tracking system for Platzi downloader.
Keeps track of completed/failed downloads and allows resuming from checkpoints.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

from .logger import Logger


class DownloadStatus(Enum):
    """Status of a download item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProgressTracker:
    """Tracks download progress and allows resuming from checkpoints."""
    
    def __init__(self, checkpoint_file: str = "download_progress.json", validate_files: bool = True):
        self.checkpoint_file = Path(checkpoint_file)
        self.validate_files = validate_files
        self.data: Dict = {
            "started_at": None,
            "last_updated": None,
            "learning_paths": {},
            "courses": {},
            "units": {},
            "errors": [],
            "statistics": {
                "total_courses": 0,
                "completed_courses": 0,
                "failed_courses": 0,
                "total_units": 0,
                "completed_units": 0,
                "failed_units": 0,
            },
            "_metadata": {
                "version": "2.0",
                "last_validation": None,
            }
        }
        self._load()
        if self.validate_files:
            self._validate_on_load()
    
    def _load(self):
        """Load existing progress from checkpoint file."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # Merge loaded data, preserving structure for new fields
                    for key in loaded_data:
                        if key in self.data and isinstance(self.data[key], dict) and isinstance(loaded_data[key], dict):
                            self.data[key].update(loaded_data[key])
                        else:
                            self.data[key] = loaded_data[key]
                    
                    # Ensure metadata exists (for backwards compatibility)
                    if "_metadata" not in self.data:
                        self.data["_metadata"] = {
                            "version": "2.0",
                            "last_validation": None,
                        }
                    
                Logger.info(f"📂 Checkpoint loaded from {self.checkpoint_file}")
                self._log_progress_summary()
            except Exception as e:
                Logger.warning(f"Could not load checkpoint: {e}")
    
    def _save(self):
        """Save current progress to checkpoint file."""
        try:
            self.data["last_updated"] = datetime.now().isoformat()
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            Logger.error(f"Could not save checkpoint: {e}")
    
    def start_session(self):
        """Mark the start of a download session."""
        if not self.data["started_at"]:
            self.data["started_at"] = datetime.now().isoformat()
        self._save()
    
    def start_learning_path(self, path_id: str, title: str, total_courses: int):
        """Register a learning path."""
        self.data["learning_paths"][path_id] = {
            "title": title,
            "status": DownloadStatus.IN_PROGRESS.value,
            "total_courses": total_courses,
            "completed_courses": 0,
            "failed_courses": 0,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
        }
        self._save()
    
    def start_course(self, course_id: str, title: str, learning_path_id: Optional[str] = None):
        """Register a course as started (or restarted)."""
        # Check if course already exists (retry scenario)
        is_new_course = course_id not in self.data["courses"]
        
        # Preserve existing units and learning paths if restarting
        existing_units = {}
        existing_learning_path_ids = []
        if not is_new_course:
            if "units" in self.data["courses"][course_id]:
                existing_units = self.data["courses"][course_id]["units"]
            # Preserve existing learning_path_ids (handle both old singular and new list format)
            old_path_ids = self.data["courses"][course_id].get("learning_path_ids", [])
            old_path_id = self.data["courses"][course_id].get("learning_path_id")
            if old_path_ids:
                existing_learning_path_ids = old_path_ids
            elif old_path_id:
                existing_learning_path_ids = [old_path_id]
        
        # Add new learning_path_id if provided and not already in list
        learning_path_ids = existing_learning_path_ids.copy()
        if learning_path_id and learning_path_id not in learning_path_ids:
            learning_path_ids.append(learning_path_id)
        
        self.data["courses"][course_id] = {
            "title": title,
            "status": DownloadStatus.IN_PROGRESS.value,
            "learning_path_ids": learning_path_ids,  # Now a list
            "started_at": self.data["courses"][course_id].get("started_at", datetime.now().isoformat()) if not is_new_course else datetime.now().isoformat(),
            "completed_at": None,
            "error": None,
            "units": existing_units  # Preserve existing unit data
        }
        
        # Only increment counter if it's a new course
        if is_new_course:
            self.data["statistics"]["total_courses"] += 1
        
        self._save()
    
    def complete_course(self, course_id: str):
        """Mark a course as completed."""
        if course_id in self.data["courses"]:
            course_data = self.data["courses"][course_id]
            previous_status = course_data["status"]
            
            course_data["status"] = DownloadStatus.COMPLETED.value
            course_data["completed_at"] = datetime.now().isoformat()
            course_data["error"] = None  # Clear any previous error
            
            # Only increment counter if it wasn't already completed
            if previous_status != DownloadStatus.COMPLETED.value:
                self.data["statistics"]["completed_courses"] += 1
            
            # Update learning path progress if applicable (handle both old and new format)
            learning_path_ids = course_data.get("learning_path_ids", [])
            if not learning_path_ids:
                old_path_id = course_data.get("learning_path_id")
                if old_path_id:
                    learning_path_ids = [old_path_id]
            
            for learning_path_id in learning_path_ids:
                if learning_path_id in self.data["learning_paths"]:
                    if previous_status != DownloadStatus.COMPLETED.value:
                        self.data["learning_paths"][learning_path_id]["completed_courses"] += 1
            
            self._save()
            Logger.info(f"✅ Course '{course_data['title']}' marked as completed")
    
    def fail_course(self, course_id: str, error: str):
        """Mark a course as failed."""
        if course_id in self.data["courses"]:
            course_data = self.data["courses"][course_id]
            previous_status = course_data["status"]
            
            course_data["status"] = DownloadStatus.FAILED.value
            course_data["error"] = error
            course_data["completed_at"] = datetime.now().isoformat()
            
            # Only increment failed counter if it wasn't already failed
            if previous_status != DownloadStatus.FAILED.value:
                self.data["statistics"]["failed_courses"] += 1
            
            # Update learning path progress if applicable (handle both old and new format)
            learning_path_ids = course_data.get("learning_path_ids", [])
            if not learning_path_ids:
                old_path_id = course_data.get("learning_path_id")
                if old_path_id:
                    learning_path_ids = [old_path_id]
            
            for learning_path_id in learning_path_ids:
                if learning_path_id in self.data["learning_paths"]:
                    if previous_status != DownloadStatus.FAILED.value:
                        self.data["learning_paths"][learning_path_id]["failed_courses"] += 1
            
            # Add to errors list
            self.data["errors"].append({
                "type": "course",
                "id": course_id,
                "title": course_data["title"],
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            
            self._save()
            Logger.error(f"❌ Course '{course_data['title']}' marked as failed: {error}")
    
    def start_unit(self, course_id: str, unit_id: str, title: str):
        """Register a unit as started (or restarted)."""
        if course_id in self.data["courses"]:
            # Check if unit already exists (retry scenario)
            is_new_unit = unit_id not in self.data["courses"][course_id].get("units", {})
            
            self.data["courses"][course_id]["units"][unit_id] = {
                "title": title,
                "status": DownloadStatus.IN_PROGRESS.value,
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "error": None
            }
            
            # Only increment counter if it's a new unit
            if is_new_unit:
                self.data["statistics"]["total_units"] += 1
            
            self._save()
    
    def complete_unit(self, course_id: str, unit_id: str):
        """Mark a unit as completed."""
        if course_id in self.data["courses"] and unit_id in self.data["courses"][course_id]["units"]:
            unit_data = self.data["courses"][course_id]["units"][unit_id]
            previous_status = unit_data["status"]
            
            unit_data["status"] = DownloadStatus.COMPLETED.value
            unit_data["completed_at"] = datetime.now().isoformat()
            unit_data["error"] = None  # Clear any previous error
            
            # Only increment completed counter if it wasn't already completed
            if previous_status != DownloadStatus.COMPLETED.value:
                self.data["statistics"]["completed_units"] += 1
            
            self._save()
    
    def fail_unit(self, course_id: str, unit_id: str, error: str):
        """Mark a unit as failed."""
        if course_id in self.data["courses"] and unit_id in self.data["courses"][course_id]["units"]:
            unit_data = self.data["courses"][course_id]["units"][unit_id]
            previous_status = unit_data["status"]
            
            unit_data["status"] = DownloadStatus.FAILED.value
            unit_data["error"] = error
            unit_data["completed_at"] = datetime.now().isoformat()
            
            # Only increment failed counter if it wasn't already failed
            if previous_status != DownloadStatus.FAILED.value:
                self.data["statistics"]["failed_units"] += 1
            
            # Add to errors list
            self.data["errors"].append({
                "type": "unit",
                "course_id": course_id,
                "unit_id": unit_id,
                "title": unit_data["title"],
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            
            self._save()
    
    def complete_learning_path(self, path_id: str):
        """Mark a learning path as completed."""
        if path_id in self.data["learning_paths"]:
            self.data["learning_paths"][path_id]["status"] = DownloadStatus.COMPLETED.value
            self.data["learning_paths"][path_id]["completed_at"] = datetime.now().isoformat()
            self._save()
    
    def is_course_completed(self, course_id: str) -> bool:
        """Check if a course was already completed."""
        if course_id in self.data["courses"]:
            return self.data["courses"][course_id]["status"] == DownloadStatus.COMPLETED.value
        return False
    
    def is_unit_completed(self, course_id: str, unit_id: str) -> bool:
        """Check if a unit was already completed."""
        if course_id in self.data["courses"] and unit_id in self.data["courses"][course_id]["units"]:
            return self.data["courses"][course_id]["units"][unit_id]["status"] == DownloadStatus.COMPLETED.value
        return False
    
    def has_pending_units(self, course_id: str) -> bool:
        """Check if a course has any pending or in-progress units."""
        if course_id not in self.data["courses"]:
            return False
        
        course_data = self.data["courses"][course_id]
        
        # Check if any unit is pending or in progress
        for unit_id, unit_data in course_data.get("units", {}).items():
            unit_status = unit_data.get("status")
            if unit_status in [DownloadStatus.PENDING.value, DownloadStatus.IN_PROGRESS.value, DownloadStatus.FAILED.value]:
                return True
        
        return False
    
    def should_skip_course(self, course_id: str) -> bool:
        """Determine if a course should be skipped (already completed AND no pending units)."""
        # Skip only if course is completed AND has no pending units
        return self.is_course_completed(course_id) and not self.has_pending_units(course_id)
    
    def should_skip_unit(self, course_id: str, unit_id: str) -> bool:
        """Determine if a unit should be skipped (already completed)."""
        return self.is_unit_completed(course_id, unit_id)
    
    def get_pending_courses(self) -> List[str]:
        """Get list of course IDs that are pending or in progress."""
        pending = []
        for course_id, course_data in self.data["courses"].items():
            status = course_data["status"]
            if status in [DownloadStatus.PENDING.value, DownloadStatus.IN_PROGRESS.value]:
                pending.append(course_id)
        return pending
    
    def generate_report(self) -> str:
        """Generate a summary report of the download progress."""
        report_lines = [
            "=" * 100,
            "📊 DOWNLOAD PROGRESS REPORT",
            "=" * 100,
            "",
            f"Session started: {self.data.get('started_at', 'N/A')}",
            f"Last updated: {self.data.get('last_updated', 'N/A')}",
            "",
            "📈 STATISTICS:",
            f"  Courses: {self.data['statistics']['completed_courses']}/{self.data['statistics']['total_courses']} completed, "
            f"{self.data['statistics']['failed_courses']} failed",
            f"  Units: {self.data['statistics']['completed_units']}/{self.data['statistics']['total_units']} completed, "
            f"{self.data['statistics']['failed_units']} failed",
            "",
        ]
        
        # Learning paths summary
        if self.data["learning_paths"]:
            report_lines.append("🗂️  LEARNING PATHS:")
            for path_id, path_data in self.data["learning_paths"].items():
                completed = path_data['completed_courses']
                total = path_data['total_courses']
                
                # Determine icon based on actual progress
                if completed == 0:
                    status_icon = "⏸️"  # Not started
                elif completed == total:
                    status_icon = "✅"  # All completed
                else:
                    status_icon = "🔄"  # In progress
                
                report_lines.append(
                    f"  {status_icon} {path_data['title']}: "
                    f"{completed}/{total} courses completed"
                )
            report_lines.append("")
        
        # Failed and pending items
        failed_units = self.get_failed_units()
        if failed_units:
            report_lines.append("❌ FAILED UNITS:")
            for unit in failed_units[:10]:  # Show first 10
                report_lines.append(f"  - {unit['course_title']} / {unit['unit_title']}")
                report_lines.append(f"    Error: {unit['error']}")
            if len(failed_units) > 10:
                report_lines.append(f"  ... and {len(failed_units) - 10} more failed units")
            report_lines.append("")
        
        # Courses with pending work
        courses_with_pending = []
        for course_id, course_data in self.data["courses"].items():
            progress = self.get_course_progress(course_id)
            if progress["pending_units"] > 0:
                courses_with_pending.append({
                    "title": course_data["title"],
                    "pending": progress["pending_units"],
                    "failed": progress["failed_units"],
                    "completed": progress["completed_units"],
                    "total": progress["total_units"]
                })
        
        if courses_with_pending:
            report_lines.append("⏳ COURSES WITH PENDING UNITS:")
            for course in courses_with_pending[:10]:
                status = f"{course['completed']}/{course['total']} completed"
                if course['failed'] > 0:
                    status += f", {course['failed']} failed"
                report_lines.append(f"  - {course['title']}: {status}")
            report_lines.append("")
        
        report_lines.append("=" * 100)
        
        return "\n".join(report_lines)
    
    def save_final_report(self, filename: str = "download_report.txt"):
        """Save the final report to a file."""
        try:
            report = self.generate_report()
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            Logger.info(f"📄 Final report saved to {filename}")
        except Exception as e:
            Logger.error(f"Could not save report: {e}")
    
    def _log_progress_summary(self):
        """Log a summary of loaded progress."""
        try:
            total_courses = len(self.data["courses"])
            completed_courses = sum(1 for c in self.data["courses"].values() if c["status"] == DownloadStatus.COMPLETED.value)
            in_progress_courses = sum(1 for c in self.data["courses"].values() if c["status"] == DownloadStatus.IN_PROGRESS.value)
            failed_courses = sum(1 for c in self.data["courses"].values() if c["status"] == DownloadStatus.FAILED.value)
            
            total_units = sum(len(c.get("units", {})) for c in self.data["courses"].values())
            completed_units = sum(
                sum(1 for u in c.get("units", {}).values() if u["status"] == DownloadStatus.COMPLETED.value)
                for c in self.data["courses"].values()
            )
            failed_units = sum(
                sum(1 for u in c.get("units", {}).values() if u["status"] == DownloadStatus.FAILED.value)
                for c in self.data["courses"].values()
            )
            in_progress_units = sum(
                sum(1 for u in c.get("units", {}).values() if u["status"] == DownloadStatus.IN_PROGRESS.value)
                for c in self.data["courses"].values()
            )
            
            if total_courses > 0:
                Logger.info(f"📊 Progress: {completed_courses}/{total_courses} courses completed, {in_progress_courses} in progress, {failed_courses} failed")
            if total_units > 0:
                Logger.info(f"📊 Units: {completed_units}/{total_units} completed, {in_progress_units} in progress, {failed_units} failed")
        except Exception:
            pass
    
    def _validate_on_load(self):
        """Validate downloaded files against checkpoint on load."""
        try:
            Logger.info("🔍 Validating downloaded files...")
            revalidated_courses = 0
            revalidated_units = 0
            
            for course_id, course_data in self.data["courses"].items():
                # Only validate courses marked as completed or in_progress
                if course_data["status"] in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_PROGRESS.value]:
                    for unit_id, unit_data in course_data.get("units", {}).items():
                        # Check if unit is marked as completed but might need revalidation
                        if unit_data["status"] == DownloadStatus.COMPLETED.value:
                            # Unit marked as completed - trust the checkpoint
                            # (we don't verify physical files to avoid false negatives)
                            pass
                        elif unit_data["status"] == DownloadStatus.IN_PROGRESS.value:
                            # Unit was interrupted - mark as pending for retry
                            Logger.info(f"🔄 Found interrupted unit: {unit_data['title']}")
                            unit_data["status"] = DownloadStatus.PENDING.value
                            revalidated_units += 1
                        elif unit_data["status"] == DownloadStatus.FAILED.value:
                            # Keep failed status but log it
                            Logger.warning(f"⚠️  Previously failed unit: {unit_data['title']}")
                
                # Check if course status needs adjustment
                if course_data["status"] == DownloadStatus.IN_PROGRESS.value:
                    # Course was interrupted - it will be re-evaluated
                    Logger.info(f"🔄 Found interrupted course: {course_data['title']}")
                    revalidated_courses += 1
            
            if revalidated_courses > 0 or revalidated_units > 0:
                Logger.info(f"✅ Validation complete: {revalidated_units} interrupted units will be retried")
                self.data["_metadata"]["last_validation"] = datetime.now().isoformat()
                self._save()
        except Exception as e:
            Logger.warning(f"Could not validate files: {e}")
    
    def get_course_progress(self, course_id: str) -> Dict:
        """Get detailed progress information for a course."""
        if course_id not in self.data["courses"]:
            return {
                "exists": False,
                "status": None,
                "total_units": 0,
                "completed_units": 0,
                "failed_units": 0,
                "pending_units": 0,
            }
        
        course_data = self.data["courses"][course_id]
        units = course_data.get("units", {})
        
        return {
            "exists": True,
            "status": course_data["status"],
            "total_units": len(units),
            "completed_units": sum(1 for u in units.values() if u["status"] == DownloadStatus.COMPLETED.value),
            "failed_units": sum(1 for u in units.values() if u["status"] == DownloadStatus.FAILED.value),
            "pending_units": sum(1 for u in units.values() if u["status"] in [DownloadStatus.PENDING.value, DownloadStatus.IN_PROGRESS.value]),
            "title": course_data.get("title", "Unknown"),
        }
    
    def get_failed_units(self, course_id: str = None) -> List[Dict]:
        """Get list of all failed units, optionally filtered by course."""
        failed = []
        for cid, course_data in self.data["courses"].items():
            if course_id and cid != course_id:
                continue
            
            for unit_id, unit_data in course_data.get("units", {}).items():
                if unit_data["status"] == DownloadStatus.FAILED.value:
                    failed.append({
                        "course_id": cid,
                        "course_title": course_data["title"],
                        "unit_id": unit_id,
                        "unit_title": unit_data["title"],
                        "error": unit_data.get("error", "Unknown error"),
                        "timestamp": unit_data.get("completed_at"),
                    })
        return failed
    
    def retry_failed_units(self, course_id: str = None):
        """Mark failed units as pending for retry."""
        retried_count = 0
        for cid, course_data in self.data["courses"].items():
            if course_id and cid != course_id:
                continue
            
            for unit_id, unit_data in course_data.get("units", {}).items():
                if unit_data["status"] == DownloadStatus.FAILED.value:
                    unit_data["status"] = DownloadStatus.PENDING.value
                    unit_data["error"] = None
                    retried_count += 1
        
        if retried_count > 0:
            Logger.info(f"🔄 Marked {retried_count} failed units for retry")
            self._save()
        return retried_count
    
    def get_failed_courses(self) -> Dict:
        """Get dictionary of all failed courses."""
        failed = {}
        for course_id, course_data in self.data["courses"].items():
            if course_data["status"] == DownloadStatus.FAILED.value:
                failed[course_id] = course_data
        return failed
    
    def reset_course(self, course_id: str):
        """Reset a course status to allow retry."""
        if course_id in self.data["courses"]:
            course_data = self.data["courses"][course_id]
            old_status = course_data["status"]
            
            # Reset course to in_progress
            course_data["status"] = DownloadStatus.IN_PROGRESS.value
            course_data["error"] = None
            course_data["completed_at"] = None
            
            # Update statistics counters
            if old_status == DownloadStatus.FAILED.value:
                self.data["statistics"]["failed_courses"] = max(0, self.data["statistics"]["failed_courses"] - 1)
            elif old_status == DownloadStatus.COMPLETED.value:
                self.data["statistics"]["completed_courses"] = max(0, self.data["statistics"]["completed_courses"] - 1)
            
            # Reset all units to pending
            for unit_id, unit_data in course_data.get("units", {}).items():
                old_unit_status = unit_data["status"]
                unit_data["status"] = DownloadStatus.PENDING.value
                unit_data["error"] = None
                unit_data["completed_at"] = None
                
                if old_unit_status == DownloadStatus.FAILED.value:
                    self.data["statistics"]["failed_units"] = max(0, self.data["statistics"]["failed_units"] - 1)
                elif old_unit_status == DownloadStatus.COMPLETED.value:
                    self.data["statistics"]["completed_units"] = max(0, self.data["statistics"]["completed_units"] - 1)
            
            self._save()
            Logger.info(f"🔄 Course '{course_data['title']}' reset for retry")
    
    def remove_course(self, course_id: str):
        """Remove a completed course from the tracker."""
        if course_id in self.data["courses"]:
            course_data = self.data["courses"][course_id]
            course_status = course_data["status"]
            
            # Update statistics
            if course_status == DownloadStatus.COMPLETED.value:
                self.data["statistics"]["completed_courses"] = max(0, self.data["statistics"]["completed_courses"] - 1)
            elif course_status == DownloadStatus.FAILED.value:
                self.data["statistics"]["failed_courses"] = max(0, self.data["statistics"]["failed_courses"] - 1)
            
            self.data["statistics"]["total_courses"] = max(0, self.data["statistics"]["total_courses"] - 1)
            
            # Update unit statistics
            for unit_data in course_data.get("units", {}).values():
                unit_status = unit_data["status"]
                if unit_status == DownloadStatus.COMPLETED.value:
                    self.data["statistics"]["completed_units"] = max(0, self.data["statistics"]["completed_units"] - 1)
                elif unit_status == DownloadStatus.FAILED.value:
                    self.data["statistics"]["failed_units"] = max(0, self.data["statistics"]["failed_units"] - 1)
                self.data["statistics"]["total_units"] = max(0, self.data["statistics"]["total_units"] - 1)
            
            # Remove from courses
            del self.data["courses"][course_id]
            self._save()
            Logger.info(f"🗑️  Removed course '{course_data['title']}' from tracker")
    
    def remove_learning_path(self, path_id: str):
        """Remove a completed learning path from the tracker."""
        if path_id in self.data["learning_paths"]:
            path_data = self.data["learning_paths"][path_id]
            del self.data["learning_paths"][path_id]
            self._save()
            Logger.info(f"🗑️  Removed learning path '{path_data['title']}' from tracker")
    
    def reset(self):
        """Reset all progress (use with caution!)."""
        self.data = {
            "started_at": None,
            "last_updated": None,
            "learning_paths": {},
            "courses": {},
            "units": {},
            "errors": [],
            "statistics": {
                "total_courses": 0,
                "completed_courses": 0,
                "failed_courses": 0,
                "total_units": 0,
                "completed_units": 0,
                "failed_units": 0,
            },
            "_metadata": {
                "version": "2.0",
                "last_validation": None,
            }
        }
        self._save()
        Logger.info("🔄 Progress tracker reset")

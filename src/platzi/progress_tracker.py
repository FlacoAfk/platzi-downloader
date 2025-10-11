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
    
    def __init__(self, checkpoint_file: str = "download_progress.json"):
        self.checkpoint_file = Path(checkpoint_file)
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
            }
        }
        self._load()
    
    def _load(self):
        """Load existing progress from checkpoint file."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.data.update(loaded_data)
                Logger.info(f"📂 Checkpoint loaded from {self.checkpoint_file}")
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
        """Register a course as started."""
        self.data["courses"][course_id] = {
            "title": title,
            "status": DownloadStatus.IN_PROGRESS.value,
            "learning_path_id": learning_path_id,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None,
            "units": {}
        }
        self.data["statistics"]["total_courses"] += 1
        self._save()
    
    def complete_course(self, course_id: str):
        """Mark a course as completed."""
        if course_id in self.data["courses"]:
            self.data["courses"][course_id]["status"] = DownloadStatus.COMPLETED.value
            self.data["courses"][course_id]["completed_at"] = datetime.now().isoformat()
            self.data["statistics"]["completed_courses"] += 1
            
            # Update learning path progress if applicable
            learning_path_id = self.data["courses"][course_id].get("learning_path_id")
            if learning_path_id and learning_path_id in self.data["learning_paths"]:
                self.data["learning_paths"][learning_path_id]["completed_courses"] += 1
            
            self._save()
            Logger.info(f"✅ Course '{self.data['courses'][course_id]['title']}' marked as completed")
    
    def fail_course(self, course_id: str, error: str):
        """Mark a course as failed."""
        if course_id in self.data["courses"]:
            self.data["courses"][course_id]["status"] = DownloadStatus.FAILED.value
            self.data["courses"][course_id]["error"] = error
            self.data["courses"][course_id]["completed_at"] = datetime.now().isoformat()
            self.data["statistics"]["failed_courses"] += 1
            
            # Update learning path progress if applicable
            learning_path_id = self.data["courses"][course_id].get("learning_path_id")
            if learning_path_id and learning_path_id in self.data["learning_paths"]:
                self.data["learning_paths"][learning_path_id]["failed_courses"] += 1
            
            # Add to errors list
            self.data["errors"].append({
                "type": "course",
                "id": course_id,
                "title": self.data["courses"][course_id]["title"],
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            
            self._save()
            Logger.error(f"❌ Course '{self.data['courses'][course_id]['title']}' marked as failed: {error}")
    
    def start_unit(self, course_id: str, unit_id: str, title: str):
        """Register a unit as started."""
        if course_id in self.data["courses"]:
            self.data["courses"][course_id]["units"][unit_id] = {
                "title": title,
                "status": DownloadStatus.IN_PROGRESS.value,
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "error": None
            }
            self.data["statistics"]["total_units"] += 1
            self._save()
    
    def complete_unit(self, course_id: str, unit_id: str):
        """Mark a unit as completed."""
        if course_id in self.data["courses"] and unit_id in self.data["courses"][course_id]["units"]:
            self.data["courses"][course_id]["units"][unit_id]["status"] = DownloadStatus.COMPLETED.value
            self.data["courses"][course_id]["units"][unit_id]["completed_at"] = datetime.now().isoformat()
            self.data["statistics"]["completed_units"] += 1
            self._save()
    
    def fail_unit(self, course_id: str, unit_id: str, error: str):
        """Mark a unit as failed."""
        if course_id in self.data["courses"] and unit_id in self.data["courses"][course_id]["units"]:
            self.data["courses"][course_id]["units"][unit_id]["status"] = DownloadStatus.FAILED.value
            self.data["courses"][course_id]["units"][unit_id]["error"] = error
            self.data["courses"][course_id]["units"][unit_id]["completed_at"] = datetime.now().isoformat()
            self.data["statistics"]["failed_units"] += 1
            
            # Add to errors list
            self.data["errors"].append({
                "type": "unit",
                "course_id": course_id,
                "unit_id": unit_id,
                "title": self.data["courses"][course_id]["units"][unit_id]["title"],
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
    
    def should_skip_course(self, course_id: str) -> bool:
        """Determine if a course should be skipped (already completed)."""
        return self.is_course_completed(course_id)
    
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
                status_icon = "✅" if path_data["status"] == DownloadStatus.COMPLETED.value else "🔄"
                report_lines.append(
                    f"  {status_icon} {path_data['title']}: "
                    f"{path_data['completed_courses']}/{path_data['total_courses']} courses completed"
                )
            report_lines.append("")
        
        # Failed items
        if self.data["errors"]:
            report_lines.append("❌ ERRORS:")
            for error in self.data["errors"][-10:]:  # Last 10 errors
                report_lines.append(f"  - [{error['type'].upper()}] {error['title']}: {error['error']}")
            if len(self.data["errors"]) > 10:
                report_lines.append(f"  ... and {len(self.data['errors']) - 10} more errors")
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
            }
        }
        self._save()
        Logger.info("🔄 Progress tracker reset")

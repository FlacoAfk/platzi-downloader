#!/usr/bin/env python3
"""
Diagnostic Tool - Platzi Downloader
====================================

Analyzes the Courses directory and download_progress.json to find discrepancies.
"""

import json
from pathlib import Path
from collections import defaultdict


def analyze_filesystem():
    """Analyze the Courses directory structure."""
    courses_base = Path("Courses")
    
    if not courses_base.exists():
        print("❌ Courses directory not found")
        return None, None
    
    learning_paths = {}
    total_course_dirs = 0
    empty_dirs = 0
    
    print("\n" + "="*100)
    print("📁 FILESYSTEM ANALYSIS")
    print("="*100 + "\n")
    
    for item in courses_base.iterdir():
        if not item.is_dir():
            continue
        
        # Count items inside
        items_inside = list(item.iterdir())
        courses_inside = [c for c in items_inside if c.is_dir()]
        
        learning_paths[item.name] = {
            'path': item,
            'courses': [],
            'empty_courses': 0
        }
        
        if not courses_inside:
            print(f"📂 {item.name}/")
            print(f"   └─ EMPTY (0 course directories)")
            empty_dirs += 1
        else:
            print(f"📂 {item.name}/")
            for course in courses_inside:
                files_inside = list(course.iterdir())
                total_course_dirs += 1
                
                if not files_inside:
                    print(f"   ├─ 📁 {course.name}/ (EMPTY - 0 files)")
                    learning_paths[item.name]['empty_courses'] += 1
                    empty_dirs += 1
                else:
                    print(f"   ├─ 📁 {course.name}/ ({len(files_inside)} items)")
                    learning_paths[item.name]['courses'].append({
                        'name': course.name,
                        'items': len(files_inside)
                    })
    
    print(f"\n📊 Summary:")
    print(f"   Learning Path directories: {len(learning_paths)}")
    print(f"   Course directories (total): {total_course_dirs}")
    print(f"   Empty directories: {empty_dirs}")
    
    return learning_paths, empty_dirs


def analyze_json():
    """Analyze the download_progress.json file."""
    progress_file = Path("download_progress.json")
    
    if not progress_file.exists():
        print("\n❌ download_progress.json not found")
        return None
    
    with open(progress_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "="*100)
    print("📊 JSON ANALYSIS")
    print("="*100 + "\n")
    
    # Learning paths in JSON
    lp_data = data.get("learning_paths", {})
    print(f"🗂️  Learning Paths in JSON: {len(lp_data)}")
    for lp_id, lp_info in lp_data.items():
        print(f"   • {lp_info['title']}: {lp_info['completed_courses']}/{lp_info['total_courses']} completed")
    
    # Courses in JSON
    courses_data = data.get("courses", {})
    print(f"\n📚 Courses in JSON: {len(courses_data)}")
    
    by_status = defaultdict(int)
    for course_data in courses_data.values():
        status = course_data.get("status", "unknown")
        by_status[status] += 1
    
    for status, count in by_status.items():
        print(f"   • {status}: {count}")
    
    # Count completed courses
    completed_courses = [c for c in courses_data.values() if c.get("status") == "completed"]
    print(f"\n✅ Completed courses in JSON: {len(completed_courses)}")
    
    return data


def compare_filesystem_vs_json(learning_paths, json_data):
    """Compare filesystem with JSON data."""
    print("\n" + "="*100)
    print("🔍 DISCREPANCY ANALYSIS")
    print("="*100 + "\n")
    
    if not json_data:
        print("❌ Cannot compare - JSON data not available")
        return
    
    courses_data = json_data.get("courses", {})
    completed_courses = {
        course_id: course_data 
        for course_id, course_data in courses_data.items() 
        if course_data.get("status") == "completed"
    }
    
    print(f"📌 Courses marked as COMPLETED in JSON: {len(completed_courses)}")
    print(f"📁 Course directories with FILES: {sum(len(lp['courses']) for lp in learning_paths.values())}")
    
    # Find courses in JSON but not in filesystem
    print(f"\n⚠️  Courses in JSON (completed) but MISSING/EMPTY on disk:")
    missing_count = 0
    
    for course_id, course_data in completed_courses.items():
        title = course_data.get("title", "Unknown")
        
        # Try to find in filesystem
        found = False
        for lp_name, lp_info in learning_paths.items():
            for course in lp_info['courses']:
                # Normalize names for comparison
                title_normalized = title.lower().replace('.', '').replace(':', '').replace(' ', '')
                course_normalized = course['name'].lower().replace('.', '').replace(':', '').replace(' ', '')
                
                if title_normalized in course_normalized or course_normalized in title_normalized:
                    found = True
                    break
            if found:
                break
        
        if not found:
            missing_count += 1
            print(f"   {missing_count}. {title}")
    
    if missing_count == 0:
        print("   ✅ All completed courses have directories with files")
    else:
        print(f"\n💡 Total: {missing_count} courses marked as completed but missing/empty on disk")


def main():
    print("\n" + "="*100)
    print("🔬 PLATZI DOWNLOADER - DIAGNOSTIC TOOL")
    print("="*100)
    
    # Analyze filesystem
    learning_paths, empty_dirs = analyze_filesystem()
    
    # Analyze JSON
    json_data = analyze_json()
    
    # Compare
    if learning_paths and json_data:
        compare_filesystem_vs_json(learning_paths, json_data)
    
    print("\n" + "="*100)
    print("💡 RECOMMENDATIONS")
    print("="*100 + "\n")
    
    if empty_dirs and empty_dirs > 0:
        print("⚠️  You have empty directories!")
        print("   This means:")
        print("   • The courses were registered in JSON as 'completed'")
        print("   • But the actual files were never downloaded or were deleted")
        print()
        print("   Solutions:")
        print("   1. Clean the JSON to remove these entries:")
        print("      python platzi_manager.py --clean-tracking")
        print()
        print("   2. Then re-download the courses:")
        print("      platzi download <URL>")
    
    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    main()

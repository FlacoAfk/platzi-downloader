#!/usr/bin/env python3
"""Script para encontrar clases con 'quiz' en el título pero que NO son quizzes reales"""
import json

with open('download_progress.json', encoding='utf-8') as f:
    data = json.load(f)

found = []
for course in data.get('courses', {}).values():
    for unit_id, unit_data in course.get('units', {}).items():
        title = unit_data.get('title', '')
        if 'quiz' in title.lower() and '/clases/quiz/' not in unit_id:
            found.append((unit_id, title))

if found:
    print(f"✅ Encontradas {len(found)} clases con 'quiz' en el título pero que NO son quizzes reales:")
    for unit_id, title in found:
        print(f"  - {unit_id} -> {title}")
else:
    print("❌ No se encontraron clases con 'quiz' en el título fuera del patrón /clases/quiz/")

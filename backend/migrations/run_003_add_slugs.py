#!/usr/bin/env python3
"""
Migration script to add slug fields to courses and lessons tables.
Run this script once to add SEO-friendly URL slugs.
"""

import os
import sys
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_client import supabase


def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    # Convert to lowercase
    slug = title.lower()
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove non-alphanumeric characters (except hyphens)
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def check_column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a table by trying to select it."""
    try:
        supabase.table(table).select(column).limit(1).execute()
        return True
    except Exception as e:
        return False


def migrate():
    """Run the migration to add slugs."""
    print("Starting slug migration...")

    # Check if slug column exists in courses
    slug_exists = check_column_exists('courses', 'slug')

    if not slug_exists:
        print("\n⚠️  Slug column doesn't exist yet.")
        print("Please run this SQL in your Supabase dashboard SQL Editor:\n")
        print("---")
        print("ALTER TABLE courses ADD COLUMN IF NOT EXISTS slug TEXT;")
        print("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS slug TEXT;")
        print("---")
        print("\nThen run this script again.")
        return False

    print("✅ Slug column exists in courses table")

    # Update courses with slugs
    print("\n📚 Updating courses with slugs...")
    courses = supabase.table('courses').select('id, title, slug').execute()

    for course in courses.data:
        if not course.get('slug'):
            slug = generate_slug(course['title'])
            print(f"  - {course['title']} -> {slug}")
            supabase.table('courses').update({'slug': slug}).eq('id', course['id']).execute()

    print(f"✅ Updated {len(courses.data)} courses")

    # Update lessons with slugs
    print("\n📖 Updating lessons with slugs...")
    lessons = supabase.table('lessons').select('id, title, slug').execute()

    for lesson in lessons.data:
        if not lesson.get('slug'):
            slug = generate_slug(lesson['title'])
            print(f"  - {lesson['title']} -> {slug}")
            supabase.table('lessons').update({'slug': slug}).eq('id', lesson['id']).execute()

    print(f"✅ Updated {len(lessons.data)} lessons")

    # Verify
    print("\n🔍 Verifying slugs...")
    courses = supabase.table('courses').select('title, slug').execute()
    for c in courses.data:
        print(f"  Course: {c['title']} -> /learn/{c['slug']}")

    lessons = supabase.table('lessons').select('title, slug').execute()
    for l in lessons.data:
        print(f"  Lesson: {l['title']} -> /learn/[course]/{l['slug']}")

    print("\n✅ Migration complete!")
    return True


if __name__ == '__main__':
    migrate()

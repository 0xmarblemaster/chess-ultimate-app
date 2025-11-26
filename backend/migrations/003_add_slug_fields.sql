-- ============================================
-- Migration: Add slug fields for SEO-friendly URLs
-- ============================================

-- Add slug column to courses
ALTER TABLE courses ADD COLUMN IF NOT EXISTS slug TEXT UNIQUE;

-- Add slug column to lessons
ALTER TABLE lessons ADD COLUMN IF NOT EXISTS slug TEXT;

-- Create unique index for lesson slugs within a module
CREATE UNIQUE INDEX IF NOT EXISTS idx_lessons_slug_module ON lessons(module_id, slug);

-- Create index for fast slug lookups
CREATE INDEX IF NOT EXISTS idx_courses_slug ON courses(slug);

-- Update existing courses with slugs generated from titles
UPDATE courses
SET slug = LOWER(REGEXP_REPLACE(REGEXP_REPLACE(title, '[^a-zA-Z0-9\s-]', '', 'g'), '\s+', '-', 'g'))
WHERE slug IS NULL;

-- Update existing lessons with slugs generated from titles
UPDATE lessons
SET slug = LOWER(REGEXP_REPLACE(REGEXP_REPLACE(title, '[^a-zA-Z0-9\s-]', '', 'g'), '\s+', '-', 'g'))
WHERE slug IS NULL;

-- Make slug NOT NULL after populating
ALTER TABLE courses ALTER COLUMN slug SET NOT NULL;
ALTER TABLE lessons ALTER COLUMN slug SET NOT NULL;

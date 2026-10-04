-- Migration: create recipe_images table for Neon Object Storage
-- Date: 2026-10-03

CREATE TABLE IF NOT EXISTS recipe_images (
    image_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id     UUID NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    object_key    TEXT NOT NULL,
    original_filename TEXT,
    content_type  TEXT,
    size_bytes    BIGINT,
    sort_order    INT NOT NULL DEFAULT 0,
    created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(recipe_id, object_key)
);

CREATE INDEX IF NOT EXISTS ix_recipe_images_recipe_id
    ON recipe_images(recipe_id);

-- Initialize database for PR Analyzer
-- This script runs when PostgreSQL container starts

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE pr_analyzer'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'pr_analyzer');

-- Set up extensions (if needed in the future)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pg_trgm";
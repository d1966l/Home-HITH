-- ============================================================
-- Migration 002 – Add AnomalyRows to NightlyUpdateLog
-- DB: referralHistDB  |  Server: localhost\SQLDEVSERVER
-- Run once; idempotent
-- ============================================================

USE referralHistDB;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.NightlyUpdateLog')
      AND name = 'AnomalyRows'
)
BEGIN
    ALTER TABLE dbo.NightlyUpdateLog
        ADD AnomalyRows int NOT NULL DEFAULT 0;
    PRINT 'Added AnomalyRows to dbo.NightlyUpdateLog';
END
ELSE
    PRINT 'AnomalyRows already exists – skipped';
GO

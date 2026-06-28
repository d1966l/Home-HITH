-- ============================================================
-- Migration 001 – Setup for nightly discharge update pipeline
-- DB: referralHistDB  |  Server: localhost\SQLDEVSERVER
-- Run once; idempotent
-- ============================================================

USE referralHistDB;
GO

-- 1. Add SyncedToHistDtm tracking column to source table
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.referrals_flattened')
      AND name = 'SyncedToHistDtm'
)
BEGIN
    ALTER TABLE dbo.referrals_flattened
        ADD SyncedToHistDtm datetime2 NULL;
    PRINT 'Added SyncedToHistDtm to dbo.referrals_flattened';
END
ELSE
    PRINT 'SyncedToHistDtm already exists – skipped';
GO

-- 2. Create audit log table
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('dbo.NightlyUpdateLog') AND type = 'U')
BEGIN
    CREATE TABLE dbo.NightlyUpdateLog (
        LogID        int          IDENTITY(1,1) NOT NULL CONSTRAINT PK_NightlyUpdateLog PRIMARY KEY,
        RunDtm       datetime2    NOT NULL,
        StageRows    int          NOT NULL DEFAULT 0,
        StagedRows   int          NOT NULL DEFAULT 0,
        HistInserts  int          NOT NULL DEFAULT 0,
        HistUpdates  int          NOT NULL DEFAULT 0,
        Status       nvarchar(20) NOT NULL DEFAULT 'Success',
        ErrorMsg     nvarchar(2000) NULL
    );
    PRINT 'Created dbo.NightlyUpdateLog';
END
ELSE
    PRINT 'dbo.NightlyUpdateLog already exists – skipped';
GO

-- ============================================================
-- Procedure: dbo.usp_NightlyDischargeUpdate
-- DB: referralHistDB  |  Server: localhost\SQLDEVSERVER
--
-- Nightly pipeline: picks up newly discharged patients from
-- dbo.referrals_flattened and promotes them into hist.Activity_Fact_Referral
-- via the stg staging layer.
--
-- Flow:
--   1. dbo.referrals_flattened (source, operational)
--        ↓  filter: ReferralStatus = 'Discharged' AND SyncedToHistDtm IS NULL
--   2. stg.Activity_Fact_Referral_Stage  (raw nvarchar landing)
--        ↓  promote: skip rows with NULL ReferralID or MRN
--   3. stg.Activity_Fact_Referral        (clean staging)
--        ↓  MERGE on ReferralID
--   4. hist.Activity_Fact_Referral       (typed history / fact)
--        ↓  mark synced
--   5. dbo.referrals_flattened.SyncedToHistDtm = @RunDtm
--        ↓  audit
--   6. dbo.NightlyUpdateLog
-- ============================================================

USE referralHistDB;
GO

CREATE OR ALTER PROCEDURE dbo.usp_NightlyDischargeUpdate
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @RunDtm       datetime2 = GETDATE();
    DECLARE @StageRows    int       = 0;
    DECLARE @StagedRows   int       = 0;
    DECLARE @Inserts      int       = 0;
    DECLARE @Updates      int       = 0;
    DECLARE @AnomalyRows  int       = 0;
    DECLARE @ErrMsg       nvarchar(2000) = NULL;

    -- Business rules:
    --   • A valid discharge must have ReferralStatus = 'Discharged' AND DischargeDate IS NOT NULL.
    --     Stage 1: Triage records will not yet have a DischargeDate and must be excluded.
    --   • An admission > 6 weeks old with no DischargeDate and not yet Discharged is anomalous
    --     and is flagged in the audit log rather than silently ignored.

    BEGIN TRY

        -- --------------------------------------------------------
        -- Step 0: Flag anomalies – admitted > 6 weeks, no discharge
        -- These are out of the ordinary; log count but do not block.
        -- --------------------------------------------------------
        SELECT @AnomalyRows = COUNT(*)
        FROM dbo.referrals_flattened
        WHERE AdmitDate IS NOT NULL
          AND DischargeDate IS NULL
          AND ReferralStatus <> 'Discharged'
          AND AdmitDate < DATEADD(WEEK, -6, CAST(@RunDtm AS date));

        IF @AnomalyRows > 0
            PRINT CONCAT(
                CONVERT(nvarchar(30), @RunDtm, 120),
                ' | WARNING: ', @AnomalyRows,
                ' patient(s) admitted > 6 weeks with no discharge date.'
            );

        -- --------------------------------------------------------
        -- Step 1: Raw landing – source → stg._Stage (all nvarchar)
        --
        -- Guard: ReferralStatus = 'Discharged' AND DischargeDate IS NOT NULL
        --   Stage 1 (Triage) records never have a DischargeDate yet – exclude.
        -- --------------------------------------------------------
        TRUNCATE TABLE stg.Activity_Fact_Referral_Stage;

        INSERT INTO stg.Activity_Fact_Referral_Stage (
            ReferralID, MRN, ReferralStatus, IsOOA, IsAgedCare,
            Postcode, Subregion, LGA, SourceHospital, ReferralSource,
            GPSuburb, Condition, ConditionGroup, Treatment, Medication,
            Frequency, AdmitDate, DischargeDate, LengthOfStay, Outcome,
            SourceFile, LoadDtm
        )
        SELECT
            CAST(ReferralID    AS nvarchar(100)),
            CAST(MRN           AS nvarchar(100)),
            ReferralStatus,
            -- text columns must go via varchar before nvarchar
            CAST(CAST(IsOOA    AS varchar(10))  AS nvarchar(10)),
            CAST(IsAgedCare    AS nvarchar(10)),
            CAST(Postcode      AS nvarchar(50)),
            Subregion,
            LGA,
            SourceHospital,
            ReferralSource,
            GPSuburb,
            Condition,
            ConditionGroup,
            Treatment,
            Medication,
            CAST(CAST(Frequency      AS varchar(200)) AS nvarchar(200)),
            CONVERT(nvarchar(20), AdmitDate,     23),  -- YYYY-MM-DD
            CONVERT(nvarchar(20), DischargeDate, 23),
            CAST(CAST(LengthOfStay   AS varchar(50))  AS nvarchar(50)),
            Outcome,
            SourceFile,
            CONVERT(nvarchar(30), LoadDtm, 126)
        FROM dbo.referrals_flattened
        WHERE ReferralStatus = 'Discharged'
          AND DischargeDate  IS NOT NULL      -- Stage 1 (Triage): no discharge date yet, exclude
          AND SyncedToHistDtm IS NULL;

        SET @StageRows = @@ROWCOUNT;

        IF @StageRows = 0
        BEGIN
            PRINT CONCAT(CONVERT(nvarchar(30), @RunDtm, 120), ' | No new discharged records to process.');
            INSERT INTO dbo.NightlyUpdateLog (RunDtm, StageRows, StagedRows, HistInserts, HistUpdates, AnomalyRows, Status)
            VALUES (@RunDtm, 0, 0, 0, 0, @AnomalyRows, 'NoData');
            RETURN;
        END

        -- --------------------------------------------------------
        -- Step 2: Promote from _Stage → stg (validated rows only)
        -- --------------------------------------------------------
        TRUNCATE TABLE stg.Activity_Fact_Referral;

        INSERT INTO stg.Activity_Fact_Referral (
            ReferralID, MRN, ReferralStatus, IsOOA, IsAgedCare,
            Postcode, Subregion, LGA, SourceHospital, ReferralSource,
            GPSuburb, Condition, ConditionGroup, Treatment, Medication,
            Frequency, AdmitDate, DischargeDate, LengthOfStay, Outcome,
            SourceFile, LoadDtm
        )
        SELECT
            ReferralID, MRN, ReferralStatus, IsOOA, IsAgedCare,
            Postcode, Subregion, LGA, SourceHospital, ReferralSource,
            GPSuburb, Condition, ConditionGroup, Treatment, Medication,
            Frequency, AdmitDate, DischargeDate, LengthOfStay, Outcome,
            SourceFile, LoadDtm
        FROM stg.Activity_Fact_Referral_Stage
        WHERE ReferralID IS NOT NULL
          AND LTRIM(RTRIM(ReferralID)) <> ''
          AND MRN IS NOT NULL
          AND LTRIM(RTRIM(MRN)) <> '';

        SET @StagedRows = @@ROWCOUNT;

        -- --------------------------------------------------------
        -- Step 3: MERGE stg → hist (with typed conversions)
        -- --------------------------------------------------------
        DECLARE @merge_output TABLE (action_type nvarchar(10));

        MERGE hist.Activity_Fact_Referral AS tgt
        USING stg.Activity_Fact_Referral  AS src
            ON tgt.ReferralID = src.ReferralID

        WHEN MATCHED THEN
            UPDATE SET
                tgt.MRN            = src.MRN,
                tgt.ReferralStatus = src.ReferralStatus,
                tgt.IsOOA          = TRY_CAST(src.IsOOA       AS bit),
                tgt.IsAgedCare     = TRY_CAST(src.IsAgedCare   AS bit),
                tgt.Postcode       = src.Postcode,
                tgt.Subregion      = src.Subregion,
                tgt.LGA            = src.LGA,
                tgt.SourceHospital = src.SourceHospital,
                tgt.ReferralSource = src.ReferralSource,
                tgt.GPSuburb       = src.GPSuburb,
                tgt.Condition      = src.Condition,
                tgt.ConditionGroup = src.ConditionGroup,
                tgt.Treatment      = src.Treatment,
                tgt.Medication     = src.Medication,
                tgt.Frequency      = src.Frequency,
                tgt.AdmitDate      = TRY_CAST(src.AdmitDate      AS date),
                tgt.DischargeDate  = TRY_CAST(src.DischargeDate  AS date),
                tgt.LengthOfStay   = TRY_CAST(src.LengthOfStay   AS int),
                tgt.Outcome        = src.Outcome,
                tgt.SourceFile     = src.SourceFile,
                tgt.LoadDtm        = TRY_CAST(src.LoadDtm         AS datetime2)

        WHEN NOT MATCHED BY TARGET THEN
            INSERT (
                ReferralID, MRN, ReferralStatus, IsOOA, IsAgedCare,
                Postcode, Subregion, LGA, SourceHospital, ReferralSource,
                GPSuburb, Condition, ConditionGroup, Treatment, Medication,
                Frequency, AdmitDate, DischargeDate, LengthOfStay, Outcome,
                SourceFile, LoadDtm, InsertDtm
            )
            VALUES (
                src.ReferralID,
                src.MRN,
                src.ReferralStatus,
                TRY_CAST(src.IsOOA        AS bit),
                TRY_CAST(src.IsAgedCare   AS bit),
                src.Postcode,
                src.Subregion,
                src.LGA,
                src.SourceHospital,
                src.ReferralSource,
                src.GPSuburb,
                src.Condition,
                src.ConditionGroup,
                src.Treatment,
                src.Medication,
                src.Frequency,
                TRY_CAST(src.AdmitDate     AS date),
                TRY_CAST(src.DischargeDate AS date),
                TRY_CAST(src.LengthOfStay  AS int),
                src.Outcome,
                src.SourceFile,
                TRY_CAST(src.LoadDtm       AS datetime2),
                @RunDtm
            )

        OUTPUT $action INTO @merge_output;

        SELECT
            @Inserts = SUM(CASE WHEN action_type = 'INSERT' THEN 1 ELSE 0 END),
            @Updates = SUM(CASE WHEN action_type = 'UPDATE' THEN 1 ELSE 0 END)
        FROM @merge_output;

        -- --------------------------------------------------------
        -- Step 4: Mark source records as synced
        -- --------------------------------------------------------
        UPDATE f
        SET    f.SyncedToHistDtm = @RunDtm
        FROM   dbo.referrals_flattened f
        INNER JOIN stg.Activity_Fact_Referral s
            ON CAST(f.ReferralID AS nvarchar(100)) = s.ReferralID;

        -- --------------------------------------------------------
        -- Step 5: Audit log
        -- --------------------------------------------------------
        INSERT INTO dbo.NightlyUpdateLog (RunDtm, StageRows, StagedRows, HistInserts, HistUpdates, AnomalyRows, Status)
        VALUES (@RunDtm, @StageRows, @StagedRows, @Inserts, @Updates, @AnomalyRows, 'Success');

        PRINT CONCAT(
            CONVERT(nvarchar(30), @RunDtm, 120),
            ' | Staged: ', @StageRows,
            ' | Promoted: ', @StagedRows,
            ' | Inserts: ', @Inserts,
            ' | Updates: ', @Updates
        );

    END TRY
    BEGIN CATCH
        SET @ErrMsg = ERROR_MESSAGE();

        INSERT INTO dbo.NightlyUpdateLog (RunDtm, StageRows, StagedRows, HistInserts, HistUpdates, AnomalyRows, Status, ErrorMsg)
        VALUES (@RunDtm, @StageRows, @StagedRows, @Inserts, @Updates, @AnomalyRows, 'Error', @ErrMsg);

        RAISERROR(@ErrMsg, 16, 1);
    END CATCH
END;
GO

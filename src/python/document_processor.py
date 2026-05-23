"""
document_processor.py – main orchestrator for the Home-HITH admit document
processing pipeline.

Pipeline
--------
1. Retrieve paired documents from SharePoint
2. Extract text and split into overlapping chunks (for logging / debug)
3. Submit documents to the Azure AI Document Intelligence model
4. Upsert extracted structured data into Dataverse
5. (Optionally) trigger population of the Admit Template

Usage
-----
    python document_processor.py                 # process all pending pairs
    python document_processor.py --patient 12345 # reprocess one patient
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from ai_model_client import AIModelClient, AIModelConfig, AdmitRecord
from chunker import Chunker
from dataverse_client import DataverseClient, DataverseConfig
from sharepoint_client import SharePointClient, SharePointConfig

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Orchestrates the full admit-document pipeline.

    Parameters
    ----------
    sp_client : SharePointClient
        Used to list and download paired documents from SharePoint.
    ai_client : AIModelClient
        Submits documents to the trained AI model.
    dv_client : DataverseClient
        Persists extracted data in Dataverse.
    chunker : Chunker
        Splits documents into chunks (used for debug logging; the AI model
        receives the full document bytes, not individual chunks).
    """

    def __init__(
        self,
        sp_client: SharePointClient,
        ai_client: AIModelClient,
        dv_client: DataverseClient,
        chunker: Chunker | None = None,
    ) -> None:
        self.sp_client = sp_client
        self.ai_client = ai_client
        self.dv_client = dv_client
        self.chunker = chunker or Chunker()

    # ------------------------------------------------------------------
    # Pipeline entry points
    # ------------------------------------------------------------------

    def process_all(self) -> list[AdmitRecord]:
        """Fetch all document pairs and process each one."""
        pairs = self.sp_client.get_document_pairs()
        logger.info("Found %d document pair(s) to process", len(pairs))
        records: list[AdmitRecord] = []
        for pair in pairs:
            try:
                record = self.process_pair(pair)
                records.append(record)
            except Exception as exc:
                logger.error("Failed to process patient %s: %s", pair.patient_id, exc, exc_info=True)
        return records

    def process_patient(self, patient_id: str) -> AdmitRecord | None:
        """Fetch and process the document pair for a specific patient."""
        pairs = self.sp_client.get_document_pairs()
        for pair in pairs:
            if pair.patient_id == patient_id:
                return self.process_pair(pair)
        logger.warning("No document pair found for patient %s", patient_id)
        return None

    def process_pair(self, pair) -> AdmitRecord:
        """
        Process a single :class:`~sharepoint_client.DocumentPair`.

        Steps:
        1. Log chunk information (useful for debugging extraction quality).
        2. Submit documents to the AI model.
        3. Upsert the result into Dataverse.
        """
        logger.info("Processing patient %s (%s)", pair.patient_id, pair.primary_name)

        # --- Step 1: chunk for debug logging ---
        primary_chunks = self.chunker.chunk_document(
            pair.primary, pair.primary_name, pair.patient_id
        )
        logger.debug(
            "Patient %s primary document: %d chunk(s) from %s",
            pair.patient_id,
            len(primary_chunks),
            pair.primary_name,
        )
        if pair.secondary:
            secondary_chunks = self.chunker.chunk_document(
                pair.secondary, pair.secondary_name, pair.patient_id
            )
            logger.debug(
                "Patient %s secondary document: %d chunk(s) from %s",
                pair.patient_id,
                len(secondary_chunks),
                pair.secondary_name,
            )

        # --- Step 2: AI model ---
        record = self.ai_client.analyze_pair(
            primary_content=pair.primary,
            primary_name=pair.primary_name,
            patient_id=pair.patient_id,
            secondary_content=pair.secondary,
            secondary_name=pair.secondary_name,
        )
        logger.info(
            "AI model extracted %d field(s) for patient %s (confidence %.2f)",
            len(record.raw_extracted_fields),
            record.patient_id,
            record.confidence_score,
        )

        # --- Step 3: Dataverse ---
        self.dv_client.upsert(record)
        logger.info("Saved admit record for patient %s to Dataverse", record.patient_id)

        return record


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_processor() -> DocumentProcessor:
    sp_config = SharePointConfig.from_env()
    ai_config = AIModelConfig.from_env()
    dv_config = DataverseConfig.from_env()

    return DocumentProcessor(
        sp_client=SharePointClient(sp_config),
        ai_client=AIModelClient(ai_config),
        dv_client=DataverseClient(dv_config),
        chunker=Chunker(
            chunk_size=int(os.environ.get("CHUNK_SIZE", "2000")),
            overlap=int(os.environ.get("CHUNK_OVERLAP", "200")),
        ),
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Process paired admit documents from SharePoint and save to Dataverse"
    )
    parser.add_argument(
        "--patient",
        metavar="PATIENT_ID",
        help="Only process the document pair for this patient ID",
    )
    args = parser.parse_args(argv)

    processor = _build_processor()

    if args.patient:
        record = processor.process_patient(args.patient)
        if record is None:
            return 1
    else:
        records = processor.process_all()
        if not records:
            logger.warning("No records were processed")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Unit tests for the document_processor orchestrator.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

sys.modules.setdefault("requests", MagicMock())
sys.modules.setdefault("msal", MagicMock())
# Stub pypdf / docx so chunker can be imported without them
sys.modules.setdefault("pypdf", MagicMock())
sys.modules.setdefault("docx", MagicMock())


class TestDocumentProcessorProcessAll(unittest.TestCase):
    def _make_processor(self):
        from document_processor import DocumentProcessor
        sp = MagicMock()
        ai = MagicMock()
        dv = MagicMock()
        chunker = MagicMock()
        return DocumentProcessor(sp, ai, dv, chunker), sp, ai, dv

    def test_process_all_returns_records(self):
        processor, sp, ai, dv = self._make_processor()

        pair = MagicMock()
        pair.patient_id = "P001"
        pair.primary_name = "face.pdf"
        pair.secondary = b"data"
        pair.secondary_name = "assess.docx"
        sp.get_document_pairs.return_value = [pair]

        from ai_model_client import AdmitRecord
        record = AdmitRecord(patient_id="P001")
        ai.analyze_pair.return_value = record

        results = processor.process_all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].patient_id, "P001")
        dv.upsert.assert_called_once_with(record)

    def test_process_all_skips_errored_pairs(self):
        processor, sp, ai, dv = self._make_processor()

        pair1 = MagicMock()
        pair1.patient_id = "P001"
        pair1.primary_name = "face.pdf"
        pair1.secondary = None
        pair1.secondary_name = None

        pair2 = MagicMock()
        pair2.patient_id = "P002"
        pair2.primary_name = "face2.pdf"
        pair2.secondary = None
        pair2.secondary_name = None

        sp.get_document_pairs.return_value = [pair1, pair2]

        from ai_model_client import AdmitRecord
        # P001 fails, P002 succeeds
        ai.analyze_pair.side_effect = [RuntimeError("AI failure"), AdmitRecord(patient_id="P002")]

        results = processor.process_all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].patient_id, "P002")

    def test_process_patient_not_found_returns_none(self):
        processor, sp, ai, dv = self._make_processor()
        sp.get_document_pairs.return_value = []
        result = processor.process_patient("UNKNOWN")
        self.assertIsNone(result)

    def test_process_patient_found(self):
        processor, sp, ai, dv = self._make_processor()

        pair = MagicMock()
        pair.patient_id = "P005"
        pair.primary_name = "face.pdf"
        pair.secondary = b"data"
        pair.secondary_name = "assess.docx"
        sp.get_document_pairs.return_value = [pair]

        from ai_model_client import AdmitRecord
        record = AdmitRecord(patient_id="P005")
        ai.analyze_pair.return_value = record

        result = processor.process_patient("P005")
        self.assertIsNotNone(result)
        self.assertEqual(result.patient_id, "P005")


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for the AI model client and AdmitRecord merge logic.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

# Stub out requests so the import itself doesn't need a network
sys.modules.setdefault("requests", MagicMock())
sys.modules.setdefault("msal", MagicMock())


class TestAdmitRecord(unittest.TestCase):
    def setUp(self):
        from ai_model_client import AdmitRecord
        self.AdmitRecord = AdmitRecord

    def test_defaults(self):
        r = self.AdmitRecord(patient_id="P001")
        self.assertEqual(r.patient_id, "P001")
        self.assertIsNone(r.patient_first_name)
        self.assertEqual(r.secondary_diagnoses, [])
        self.assertEqual(r.confidence_score, 0.0)

    def test_source_files_default_empty(self):
        r = self.AdmitRecord(patient_id="P002")
        self.assertEqual(r.source_files, [])


class TestMergeRecords(unittest.TestCase):
    def setUp(self):
        from ai_model_client import AdmitRecord, AIModelClient
        self.AdmitRecord = AdmitRecord
        self.merge = AIModelClient._merge_records

    def test_primary_value_preferred(self):
        primary = self.AdmitRecord(patient_id="P001", patient_first_name="Alice")
        secondary = self.AdmitRecord(patient_id="P001", patient_first_name="Bob")
        merged = self.merge(primary, secondary)
        self.assertEqual(merged.patient_first_name, "Alice")

    def test_secondary_fills_gap(self):
        primary = self.AdmitRecord(patient_id="P001", patient_first_name=None)
        secondary = self.AdmitRecord(patient_id="P001", patient_first_name="Carol")
        merged = self.merge(primary, secondary)
        self.assertEqual(merged.patient_first_name, "Carol")

    def test_lists_merged_without_duplicates(self):
        primary = self.AdmitRecord(patient_id="P001", medications=["Aspirin", "Lisinopril"])
        secondary = self.AdmitRecord(patient_id="P001", medications=["Lisinopril", "Metformin"])
        merged = self.merge(primary, secondary)
        self.assertIn("Aspirin", merged.medications)
        self.assertIn("Metformin", merged.medications)
        self.assertEqual(merged.medications.count("Lisinopril"), 1)

    def test_source_files_combined(self):
        primary = self.AdmitRecord(patient_id="P001", source_files=["face.pdf"])
        secondary = self.AdmitRecord(patient_id="P001", source_files=["assess.docx"])
        merged = self.merge(primary, secondary)
        self.assertIn("face.pdf", merged.source_files)
        self.assertIn("assess.docx", merged.source_files)

    def test_confidence_averaged(self):
        primary = self.AdmitRecord(patient_id="P001", confidence_score=0.8)
        secondary = self.AdmitRecord(patient_id="P001", confidence_score=0.6)
        merged = self.merge(primary, secondary)
        self.assertAlmostEqual(merged.confidence_score, 0.7, places=4)


class TestGetFieldValue(unittest.TestCase):
    def setUp(self):
        from ai_model_client import AIModelClient
        self.gv = AIModelClient._get_field_value

    def test_returns_content(self):
        fields = {"PatientFirstName": {"content": "Jane", "confidence": 0.9}}
        self.assertEqual(self.gv(fields, "PatientFirstName"), "Jane")

    def test_falls_back_to_value_string(self):
        fields = {"PatientFirstName": {"valueString": "Jane"}}
        self.assertEqual(self.gv(fields, "PatientFirstName"), "Jane")

    def test_missing_key_returns_none(self):
        self.assertIsNone(self.gv({}, "PatientFirstName"))

    def test_non_dict_value_returns_none(self):
        self.assertIsNone(self.gv({"key": "not_a_dict"}, "key"))


class TestGetListField(unittest.TestCase):
    def setUp(self):
        from ai_model_client import AIModelClient
        self.gl = AIModelClient._get_list_field

    def test_returns_list(self):
        fields = {
            "Medications": {
                "valueArray": [
                    {"valueString": "Aspirin"},
                    {"valueString": "Metformin"},
                ]
            }
        }
        result = self.gl(fields, "Medications")
        self.assertEqual(result, ["Aspirin", "Metformin"])

    def test_empty_array(self):
        fields = {"Medications": {"valueArray": []}}
        self.assertEqual(self.gl(fields, "Medications"), [])

    def test_missing_key_returns_empty_list(self):
        self.assertEqual(self.gl({}, "Medications"), [])


if __name__ == "__main__":
    unittest.main()

"""
AI model client for extracting structured admit data from document chunks.

The client wraps **Azure AI Document Intelligence** (formerly Form Recognizer)
which hosts the already-trained custom model that understands the specific
layout of the paired admit documents.

The extracted fields are mapped to the :class:`AdmitRecord` dataclass that
mirrors the Dataverse ``hith_admitdata`` table schema.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class AdmitRecord:
    """
    Structured data extracted from a pair of admit documents.

    Fields mirror the ``hith_admitdata`` Dataverse table.
    """

    patient_id: str
    # Patient demographics
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
    patient_date_of_birth: Optional[str] = None
    patient_gender: Optional[str] = None
    patient_address: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_insurance_id: Optional[str] = None
    patient_insurance_name: Optional[str] = None
    # Clinical information
    primary_diagnosis: Optional[str] = None
    secondary_diagnoses: List[str] = field(default_factory=list)
    physician_name: Optional[str] = None
    physician_npi: Optional[str] = None
    referring_physician: Optional[str] = None
    admit_date: Optional[str] = None
    discharge_date: Optional[str] = None
    # Care plan
    functional_limitations: Optional[str] = None
    mental_status: Optional[str] = None
    prognosis: Optional[str] = None
    skilled_services: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    # Processing metadata
    source_files: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    raw_extracted_fields: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Azure AI Document Intelligence client
# ---------------------------------------------------------------------------

class AIModelConfig:
    """Configuration for Azure AI Document Intelligence."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model_id: str,
        api_version: str = "2024-02-29-preview",
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model_id = model_id
        self.api_version = api_version

    @classmethod
    def from_env(cls) -> "AIModelConfig":
        return cls(
            endpoint=os.environ["AZURE_DOC_INTELLIGENCE_ENDPOINT"],
            api_key=os.environ["AZURE_DOC_INTELLIGENCE_KEY"],
            model_id=os.environ.get("AZURE_DOC_INTELLIGENCE_MODEL_ID", "admit-documents-model"),
        )


class AIModelClient:
    """
    Calls the Azure AI Document Intelligence API to analyse document chunks
    and extract structured admit data.

    The *already-trained* custom model is identified by ``config.model_id``.
    """

    def __init__(self, config: AIModelConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Low-level API
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {
            "Ocp-Apim-Subscription-Key": self.config.api_key,
            "Content-Type": "application/json",
        }

    def _analyze_bytes(self, content: bytes) -> Dict[str, Any]:
        """
        Submit a document for analysis and poll until complete.

        Returns the raw JSON result from the API.
        """
        import base64
        import time

        url = (
            f"{self.config.endpoint}/documentintelligence/documentModels"
            f"/{self.config.model_id}:analyze"
            f"?api-version={self.config.api_version}"
        )
        body = {"base64Source": base64.b64encode(content).decode()}
        resp = requests.post(url, headers=self._headers(), json=body, timeout=30)
        resp.raise_for_status()

        # The API is async – poll the operation-location header
        operation_url = resp.headers.get("Operation-Location") or resp.headers.get("operation-location")
        if not operation_url:
            # Synchronous path (shouldn't happen in practice)
            return resp.json()

        poll_headers = {"Ocp-Apim-Subscription-Key": self.config.api_key}
        for attempt in range(60):  # up to ~5 minutes
            time.sleep(5)
            poll_resp = requests.get(operation_url, headers=poll_headers, timeout=30)
            poll_resp.raise_for_status()
            result = poll_resp.json()
            status = result.get("status", "")
            if status == "succeeded":
                return result
            if status == "failed":
                raise RuntimeError(f"Document analysis failed: {result.get('error')}")
            logger.debug("Waiting for analysis (attempt %d, status=%s)", attempt + 1, status)

        raise TimeoutError("Document analysis did not complete within the allowed time")

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_field_value(fields: Dict[str, Any], key: str) -> Optional[str]:
        field_data = fields.get(key, {})
        if isinstance(field_data, dict):
            return field_data.get("content") or field_data.get("valueString")
        return None

    @staticmethod
    def _get_list_field(fields: Dict[str, Any], key: str) -> List[str]:
        field_data = fields.get(key, {})
        if isinstance(field_data, dict):
            items = field_data.get("valueArray", [])
            return [
                item.get("valueString") or item.get("content", "")
                for item in items
                if item.get("valueString") or item.get("content")
            ]
        return []

    def _parse_result(self, patient_id: str, raw: Dict[str, Any], source_files: List[str]) -> AdmitRecord:
        """Map the raw API response to an :class:`AdmitRecord`."""
        documents = raw.get("analyzeResult", {}).get("documents", [])
        if not documents:
            logger.warning("No documents found in AI model response for patient %s", patient_id)
            return AdmitRecord(patient_id=patient_id, source_files=source_files)

        # Use the highest-confidence document result
        doc = max(documents, key=lambda d: d.get("confidence", 0))
        fields: Dict[str, Any] = doc.get("fields", {})
        gv = self._get_field_value
        gl = self._get_list_field

        confidence = float(doc.get("confidence", 0))
        avg_field_confidence = (
            sum(
                float(v.get("confidence", 0))
                for v in fields.values()
                if isinstance(v, dict) and "confidence" in v
            )
            / max(len(fields), 1)
        )

        return AdmitRecord(
            patient_id=patient_id,
            patient_first_name=gv(fields, "PatientFirstName"),
            patient_last_name=gv(fields, "PatientLastName"),
            patient_date_of_birth=gv(fields, "DateOfBirth"),
            patient_gender=gv(fields, "Gender"),
            patient_address=gv(fields, "Address"),
            patient_phone=gv(fields, "PhoneNumber"),
            patient_insurance_id=gv(fields, "InsuranceID"),
            patient_insurance_name=gv(fields, "InsuranceName"),
            primary_diagnosis=gv(fields, "PrimaryDiagnosis"),
            secondary_diagnoses=gl(fields, "SecondaryDiagnoses"),
            physician_name=gv(fields, "PhysicianName"),
            physician_npi=gv(fields, "PhysicianNPI"),
            referring_physician=gv(fields, "ReferringPhysician"),
            admit_date=gv(fields, "AdmitDate"),
            discharge_date=gv(fields, "DischargeDate"),
            functional_limitations=gv(fields, "FunctionalLimitations"),
            mental_status=gv(fields, "MentalStatus"),
            prognosis=gv(fields, "Prognosis"),
            skilled_services=gl(fields, "SkilledServices"),
            medications=gl(fields, "Medications"),
            allergies=gl(fields, "Allergies"),
            source_files=source_files,
            confidence_score=round((confidence + avg_field_confidence) / 2, 4),
            raw_extracted_fields=fields,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_document(self, content: bytes, patient_id: str, filename: str) -> AdmitRecord:
        """
        Send a single document to the AI model and return an :class:`AdmitRecord`.
        """
        logger.info("Analysing document %s for patient %s", filename, patient_id)
        raw = self._analyze_bytes(content)
        return self._parse_result(patient_id, raw, [filename])

    def analyze_pair(
        self,
        primary_content: bytes,
        primary_name: str,
        patient_id: str,
        secondary_content: Optional[bytes] = None,
        secondary_name: Optional[str] = None,
    ) -> AdmitRecord:
        """
        Analyse a primary document (and optionally a secondary document) and
        merge the results into a single :class:`AdmitRecord`.

        When a secondary document is provided its fields supplement (but do
        not overwrite) fields extracted from the primary.
        """
        primary_record = self.analyze_document(primary_content, patient_id, primary_name)

        if secondary_content is None or secondary_name is None:
            return primary_record

        secondary_record = self.analyze_document(secondary_content, patient_id, secondary_name)
        return self._merge_records(primary_record, secondary_record)

    @staticmethod
    def _merge_records(primary: AdmitRecord, secondary: AdmitRecord) -> AdmitRecord:
        """
        Merge two records, preferring non-None values from the primary and
        filling gaps from the secondary.
        """
        merged = AdmitRecord(
            patient_id=primary.patient_id,
            source_files=primary.source_files + secondary.source_files,
            confidence_score=round((primary.confidence_score + secondary.confidence_score) / 2, 4),
        )

        def _pick(primary_val, secondary_val):
            return primary_val if primary_val is not None else secondary_val

        def _merge_list(primary_list, secondary_list):
            combined = list(primary_list)
            for item in secondary_list:
                if item not in combined:
                    combined.append(item)
            return combined

        merged.patient_first_name = _pick(primary.patient_first_name, secondary.patient_first_name)
        merged.patient_last_name = _pick(primary.patient_last_name, secondary.patient_last_name)
        merged.patient_date_of_birth = _pick(primary.patient_date_of_birth, secondary.patient_date_of_birth)
        merged.patient_gender = _pick(primary.patient_gender, secondary.patient_gender)
        merged.patient_address = _pick(primary.patient_address, secondary.patient_address)
        merged.patient_phone = _pick(primary.patient_phone, secondary.patient_phone)
        merged.patient_insurance_id = _pick(primary.patient_insurance_id, secondary.patient_insurance_id)
        merged.patient_insurance_name = _pick(primary.patient_insurance_name, secondary.patient_insurance_name)
        merged.primary_diagnosis = _pick(primary.primary_diagnosis, secondary.primary_diagnosis)
        merged.secondary_diagnoses = _merge_list(primary.secondary_diagnoses, secondary.secondary_diagnoses)
        merged.physician_name = _pick(primary.physician_name, secondary.physician_name)
        merged.physician_npi = _pick(primary.physician_npi, secondary.physician_npi)
        merged.referring_physician = _pick(primary.referring_physician, secondary.referring_physician)
        merged.admit_date = _pick(primary.admit_date, secondary.admit_date)
        merged.discharge_date = _pick(primary.discharge_date, secondary.discharge_date)
        merged.functional_limitations = _pick(primary.functional_limitations, secondary.functional_limitations)
        merged.mental_status = _pick(primary.mental_status, secondary.mental_status)
        merged.prognosis = _pick(primary.prognosis, secondary.prognosis)
        merged.skilled_services = _merge_list(primary.skilled_services, secondary.skilled_services)
        merged.medications = _merge_list(primary.medications, secondary.medications)
        merged.allergies = _merge_list(primary.allergies, secondary.allergies)
        merged.raw_extracted_fields = {**secondary.raw_extracted_fields, **primary.raw_extracted_fields}
        return merged

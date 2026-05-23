"""
Dataverse client – saves extracted :class:`AdmitRecord` data to the
``hith_admitdata`` table in Microsoft Dataverse via the Web API.

Authentication uses Azure AD client credentials (same app registration as the
SharePoint client).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import msal
import requests

from ai_model_client import AdmitRecord

logger = logging.getLogger(__name__)


class DataverseConfig:
    """Configuration for the Dataverse Web API connection."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        environment_url: str,
        table_name: str = "hith_admitdatas",
    ) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        # e.g. https://orgXXXXXXXX.crm.dynamics.com
        self.environment_url = environment_url.rstrip("/")
        self.table_name = table_name

    @classmethod
    def from_env(cls) -> "DataverseConfig":
        return cls(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
            environment_url=os.environ["DATAVERSE_ENVIRONMENT_URL"],
            table_name=os.environ.get("DATAVERSE_TABLE_NAME", "hith_admitdatas"),
        )


class DataverseClient:
    """
    Upserts :class:`AdmitRecord` instances into the Dataverse
    ``hith_admitdata`` table using the Dataverse Web API (OData v4).
    """

    API_VERSION = "v9.2"

    def __init__(self, config: DataverseConfig) -> None:
        self.config = config
        self._token: Optional[str] = None
        self._msal_app = msal.ConfidentialClientApplication(
            client_id=config.client_id,
            authority=f"https://login.microsoftonline.com/{config.tenant_id}",
            client_credential=config.client_secret,
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        scope = [f"{self.config.environment_url}/.default"]
        result = self._msal_app.acquire_token_for_client(scopes=scope)
        if "access_token" not in result:
            raise RuntimeError(f"Failed to acquire Dataverse token: {result.get('error_description')}")
        return result["access_token"]

    def _headers(self) -> dict:
        if not self._token:
            self._token = self._get_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Prefer": "return=representation",
        }

    def _base_url(self) -> str:
        return f"{self.config.environment_url}/api/data/{self.API_VERSION}"

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _record_to_payload(record: AdmitRecord) -> Dict[str, Any]:
        """Convert an :class:`AdmitRecord` to a Dataverse table row payload."""
        payload: Dict[str, Any] = {
            "hith_patientid": record.patient_id,
            "hith_patientfirstname": record.patient_first_name,
            "hith_patientlastname": record.patient_last_name,
            "hith_dateofbirth": record.patient_date_of_birth,
            "hith_gender": record.patient_gender,
            "hith_address": record.patient_address,
            "hith_phonenumber": record.patient_phone,
            "hith_insuranceid": record.patient_insurance_id,
            "hith_insurancename": record.patient_insurance_name,
            "hith_primarydiagnosis": record.primary_diagnosis,
            "hith_secondarydiagnoses": json.dumps(record.secondary_diagnoses),
            "hith_physicianname": record.physician_name,
            "hith_physiciannpi": record.physician_npi,
            "hith_referringphysician": record.referring_physician,
            "hith_admitdate": record.admit_date,
            "hith_dischargedate": record.discharge_date,
            "hith_functionallimitations": record.functional_limitations,
            "hith_mentalstatus": record.mental_status,
            "hith_prognosis": record.prognosis,
            "hith_skilledservices": json.dumps(record.skilled_services),
            "hith_medications": json.dumps(record.medications),
            "hith_allergies": json.dumps(record.allergies),
            "hith_sourcefiles": json.dumps(record.source_files),
            "hith_confidencescore": record.confidence_score,
        }
        # Remove None values so Dataverse keeps existing values on upsert
        return {k: v for k, v in payload.items() if v is not None}

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def upsert(self, record: AdmitRecord) -> Dict[str, Any]:
        """
        Upsert an admit record using the patient ID as the alternate key.

        If a row with the same ``hith_patientid`` already exists it is
        updated; otherwise a new row is created.

        Returns the created / updated row as a dict.
        """
        payload = self._record_to_payload(record)
        # Use PATCH with alternate key for upsert behaviour
        url = (
            f"{self._base_url()}/{self.config.table_name}"
            f"(hith_patientid='{record.patient_id}')"
        )
        headers = {
            **self._headers(),
            "If-Match": "*",  # allow create OR update
        }
        resp = requests.patch(url, headers=headers, json=payload, timeout=30)

        if resp.status_code == 401:
            self._token = self._get_token()
            headers["Authorization"] = f"Bearer {self._token}"
            resp = requests.patch(url, headers=headers, json=payload, timeout=30)

        if resp.status_code == 412:
            # Row doesn't exist – create it instead
            create_url = f"{self._base_url()}/{self.config.table_name}"
            resp = requests.post(create_url, headers=self._headers(), json=payload, timeout=30)

        resp.raise_for_status()
        logger.info("Upserted admit record for patient %s (HTTP %s)", record.patient_id, resp.status_code)
        return resp.json() if resp.content else {"hith_patientid": record.patient_id}

    def get_by_patient_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single row by patient ID, or None if not found."""
        url = (
            f"{self._base_url()}/{self.config.table_name}"
            f"(hith_patientid='{patient_id}')"
        )
        resp = requests.get(url, headers=self._headers(), timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def list_records(self, top: int = 100, filter_expr: Optional[str] = None) -> list:
        """Return a list of admit data rows, optionally filtered."""
        url = f"{self._base_url()}/{self.config.table_name}?$top={top}"
        if filter_expr:
            url += f"&$filter={requests.utils.quote(filter_expr)}"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json().get("value", [])

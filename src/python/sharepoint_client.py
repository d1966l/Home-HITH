"""
SharePoint client for retrieving paired PDF / MS Word admit documents.

Paired documents share a common base name, e.g.:
  - patient_12345_facesheet.pdf
  - patient_12345_assessment.docx

The client authenticates via Azure AD (client credentials) and uses the
Microsoft Graph API to list and download files from a configured SharePoint
document library.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import msal
import requests

logger = logging.getLogger(__name__)


@dataclass
class DocumentPair:
    """A matched pair of admit documents (e.g. face sheet + assessment)."""

    patient_id: str
    primary: bytes  # raw file bytes for the primary document
    primary_name: str
    secondary: Optional[bytes] = None  # raw file bytes for the secondary document
    secondary_name: Optional[str] = None
    primary_content_type: str = "application/pdf"
    secondary_content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@dataclass
class SharePointConfig:
    """Configuration for the SharePoint / Graph API connection."""

    tenant_id: str
    client_id: str
    client_secret: str
    site_id: str  # SharePoint site ID (GUID or hostname:path)
    drive_id: str  # Document library drive ID
    folder_path: str = "Admit Documents"  # Relative folder path within the drive
    pair_separator: str = "_"  # Separator used to extract patient_id from filenames
    primary_suffixes: List[str] = field(default_factory=lambda: ["facesheet", "face_sheet", "face-sheet"])
    secondary_suffixes: List[str] = field(default_factory=lambda: ["assessment", "order", "orders"])
    supported_extensions: List[str] = field(default_factory=lambda: [".pdf", ".docx", ".doc"])

    @classmethod
    def from_env(cls) -> "SharePointConfig":
        """Build configuration from environment variables."""
        return cls(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
            site_id=os.environ["SHAREPOINT_SITE_ID"],
            drive_id=os.environ["SHAREPOINT_DRIVE_ID"],
            folder_path=os.environ.get("SHAREPOINT_FOLDER_PATH", "Admit Documents"),
        )


class SharePointClient:
    """Authenticates with Microsoft Graph and retrieves document pairs from SharePoint."""

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    SCOPE = ["https://graph.microsoft.com/.default"]

    def __init__(self, config: SharePointConfig) -> None:
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
        result = self._msal_app.acquire_token_for_client(scopes=self.SCOPE)
        if "access_token" not in result:
            raise RuntimeError(f"Failed to acquire token: {result.get('error_description')}")
        return result["access_token"]

    def _headers(self) -> dict:
        if not self._token:
            self._token = self._get_token()
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    # ------------------------------------------------------------------
    # Graph API helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, **kwargs) -> dict:
        resp = requests.get(url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code == 401:
            # Token may have expired – refresh once
            self._token = self._get_token()
            resp = requests.get(url, headers=self._headers(), timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _download(self, download_url: str) -> bytes:
        resp = requests.get(download_url, timeout=60)
        resp.raise_for_status()
        return resp.content

    # ------------------------------------------------------------------
    # File listing
    # ------------------------------------------------------------------

    def list_files(self) -> List[dict]:
        """Return all files in the configured SharePoint folder."""
        url = (
            f"{self.GRAPH_BASE}/sites/{self.config.site_id}"
            f"/drives/{self.config.drive_id}"
            f"/root:/{self.config.folder_path}:/children"
        )
        items: List[dict] = []
        while url:
            data = self._get(url)
            items.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
        return items

    # ------------------------------------------------------------------
    # Pairing logic
    # ------------------------------------------------------------------

    def _extract_patient_id(self, filename: str) -> Optional[str]:
        """
        Derive a patient identifier from the filename.

        Strategy: split on the separator and return the segment that looks like
        a patient identifier (a run of digits, or the first two tokens joined).
        Falls back to the full stem if no digits are found.
        """
        stem, _ = os.path.splitext(filename)
        parts = stem.split(self.config.pair_separator)
        # Look for a numeric segment
        for part in parts:
            if part.isdigit():
                return part
        # Fall back to first two tokens as a composite key
        return self.config.pair_separator.join(parts[:2]) if len(parts) >= 2 else stem

    def _classify(self, filename: str) -> Optional[str]:
        """Return 'primary', 'secondary', or None based on suffix matching."""
        stem = os.path.splitext(filename)[0].lower()
        for suffix in self.config.primary_suffixes:
            if suffix in stem:
                return "primary"
        for suffix in self.config.secondary_suffixes:
            if suffix in stem:
                return "secondary"
        return None

    def get_document_pairs(self) -> List[DocumentPair]:
        """
        List files in the SharePoint folder, match them into pairs, and
        download their content.

        Returns a list of :class:`DocumentPair` objects where at least the
        primary document is present.
        """
        files = self.list_files()
        grouped: dict[str, dict] = {}

        for item in files:
            name: str = item.get("name", "")
            ext = os.path.splitext(name)[1].lower()
            if ext not in self.config.supported_extensions:
                continue
            if "file" not in item:  # skip folders
                continue

            patient_id = self._extract_patient_id(name)
            if patient_id not in grouped:
                grouped[patient_id] = {}

            role = self._classify(name)
            download_url = item.get("@microsoft.graph.downloadUrl") or item.get("downloadUrl")
            grouped[patient_id][role or name] = {"name": name, "url": download_url}

        pairs: List[DocumentPair] = []
        for patient_id, docs in grouped.items():
            primary_meta = docs.get("primary")
            if not primary_meta:
                logger.warning("No primary document found for patient %s – skipping", patient_id)
                continue

            logger.info("Downloading documents for patient %s", patient_id)
            primary_bytes = self._download(primary_meta["url"])
            secondary_meta = docs.get("secondary")
            secondary_bytes = self._download(secondary_meta["url"]) if secondary_meta else None

            pairs.append(
                DocumentPair(
                    patient_id=patient_id,
                    primary=primary_bytes,
                    primary_name=primary_meta["name"],
                    secondary=secondary_bytes,
                    secondary_name=secondary_meta["name"] if secondary_meta else None,
                )
            )
        return pairs

    # ------------------------------------------------------------------
    # Individual file upload (for populated Admit Templates)
    # ------------------------------------------------------------------

    def upload_file(self, filename: str, content: bytes, folder_path: Optional[str] = None) -> dict:
        """Upload a file back to SharePoint (e.g. a populated Admit Template)."""
        folder = folder_path or self.config.folder_path
        url = (
            f"{self.GRAPH_BASE}/sites/{self.config.site_id}"
            f"/drives/{self.config.drive_id}"
            f"/root:/{folder}/{filename}:/content"
        )
        headers = {**self._headers(), "Content-Type": "application/octet-stream"}
        resp = requests.put(url, headers=headers, data=content, timeout=60)
        resp.raise_for_status()
        return resp.json()

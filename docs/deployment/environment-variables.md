# Environment Variables Reference

This document defines the environment variables required by Home-HITH for authentication, SharePoint access, AI extraction, Dataverse connectivity, and pipeline behavior.

---

# Azure Authentication

These variables are used to authenticate against Azure Active Directory.

| Variable | Description |
|-----------|-------------|
| AZURE_TENANT_ID | Azure AD Tenant ID |
| AZURE_CLIENT_ID | Azure App Registration Client ID |
| AZURE_CLIENT_SECRET | Azure App Registration Client Secret |

### Example

```env
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>
```

---

# SharePoint

These variables configure the SharePoint site, library, and folder where admit documents are stored.

| Variable | Description |
|-----------|-------------|
| SHAREPOINT_SITE_ID | SharePoint site ID or hostname and path |
| SHAREPOINT_DRIVE_ID | SharePoint document library drive ID |
| SHAREPOINT_FOLDER_PATH | Relative path to the Admit Documents folder |

### Example

```env
SHAREPOINT_SITE_ID=<sharepoint-site-id-or-hostname-path>
SHAREPOINT_DRIVE_ID=<document-library-drive-id>
SHAREPOINT_FOLDER_PATH=Admit Documents
```

---

# Azure AI Document Intelligence

These variables control the Document Intelligence endpoint and model used by the pipeline.

| Variable | Description |
|-----------|-------------|
| AZURE_DOC_INTELLIGENCE_ENDPOINT | Azure AI Document Intelligence endpoint |
| AZURE_DOC_INTELLIGENCE_KEY | API key for Document Intelligence |
| AZURE_DOC_INTELLIGENCE_MODEL_ID | Model identifier for admit document extraction |

### Example

```env
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://<resource-name>.cognitiveservices.azure.com
AZURE_DOC_INTELLIGENCE_KEY=<secret>
AZURE_DOC_INTELLIGENCE_MODEL_ID=admit-documents-model
```

---

# Dataverse

These variables configure the Dataverse environment and target table.

| Variable | Description |
|-----------|-------------|
| DATAVERSE_ENVIRONMENT_URL | Dataverse environment URL |
| DATAVERSE_TABLE_NAME | Dataverse table name |

### Example

```env
DATAVERSE_ENVIRONMENT_URL=https://orgXXXXXXXX.crm.dynamics.com
DATAVERSE_TABLE_NAME=hith_admitdatas
```

---

# Python Pipeline Settings

These variables are consumed by the Python processing pipeline.

| Variable | Description |
|-----------|-------------|
| CHUNK_SIZE | Document chunk size for debug logging (default: 2000) |
| CHUNK_OVERLAP | Chunk overlap for debug logging (default: 200) |
| LOG_LEVEL | Logging level for the pipeline |

### Example

```env
CHUNK_SIZE=2000
CHUNK_OVERLAP=200
LOG_LEVEL=INFO
```

---

# Complete Example .env

```env
# Azure AD authentication
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>

# SharePoint
SHAREPOINT_SITE_ID=<sharepoint-site-id-or-hostname-path>
SHAREPOINT_DRIVE_ID=<document-library-drive-id>
SHAREPOINT_FOLDER_PATH=Admit Documents

# Azure AI Document Intelligence
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://<resource-name>.cognitiveservices.azure.com
AZURE_DOC_INTELLIGENCE_KEY=<secret>
AZURE_DOC_INTELLIGENCE_MODEL_ID=admit-documents-model

# Dataverse
DATAVERSE_ENVIRONMENT_URL=https://orgXXXXXXXX.crm.dynamics.com
DATAVERSE_TABLE_NAME=hith_admitdatas

# Pipeline settings
CHUNK_SIZE=2000
CHUNK_OVERLAP=200
LOG_LEVEL=INFO
```

---

# Security Guidelines

- Never commit `.env` files to GitHub.
- Store secrets in Azure Key Vault where possible.
- Rotate application secrets regularly.
- Apply least-privilege permissions to Azure App Registrations.
- Use separate configuration values for Development, Test, and Production environments.

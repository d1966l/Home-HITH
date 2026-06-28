# Environment Variables Reference

This document defines the environment variables required by Home-HITH for authentication, document processing, data storage, and workflow automation.

---

# Azure Authentication

These variables are used to authenticate against Azure Active Directory and Microsoft services.

| Variable | Description |
|-----------|-------------|
| TENANT_ID | Azure AD Tenant ID |
| CLIENT_ID | Azure App Registration Client ID |
| CLIENT_SECRET | Azure App Registration Client Secret |
| AUTHORITY | Azure AD authority URL |

### Example

```env
TENANT_ID=<tenant-id>
CLIENT_ID=<client-id>
CLIENT_SECRET=<client-secret>
AUTHORITY=https://login.microsoftonline.com/<tenant-id>
```

---

# Microsoft Graph & SharePoint

These variables control access to SharePoint and Microsoft Graph.

| Variable | Description |
|-----------|-------------|
| GRAPH_ENDPOINT | Microsoft Graph API endpoint |
| GRAPH_SCOPE | Microsoft Graph scope |
| SHAREPOINT_SITE | SharePoint site containing admit documents |
| SHAREPOINT_DRIVE | Document library name |
| SHAREPOINT_FOLDER | Folder monitored for admit documents |

### Example

```env
GRAPH_ENDPOINT=https://graph.microsoft.com/v1.0
GRAPH_SCOPE=https://graph.microsoft.com/.default

SHAREPOINT_SITE=Home-HITH
SHAREPOINT_DRIVE=Documents
SHAREPOINT_FOLDER=AdmitDocuments
```

---

# Azure AI Document Intelligence

These variables control AI document extraction.

| Variable | Description |
|-----------|-------------|
| DOC_INTELLIGENCE_ENDPOINT | Azure AI Document Intelligence endpoint |
| DOC_INTELLIGENCE_KEY | API key |
| DOC_INTELLIGENCE_MODEL | Trained model identifier |

### Example

```env
DOC_INTELLIGENCE_ENDPOINT=https://homehith-ai.cognitiveservices.azure.com/
DOC_INTELLIGENCE_KEY=<secret>
DOC_INTELLIGENCE_MODEL=admit-documents-model
```

---

# Dataverse

These variables control Dataverse connectivity.

| Variable | Description |
|-----------|-------------|
| DATAVERSE_URL | Dataverse environment URL |
| DATAVERSE_TABLE | Target table |
| DATAVERSE_ALT_KEY | Alternate key used for upserts |

### Example

```env
DATAVERSE_URL=https://org.crm6.dynamics.com
DATAVERSE_TABLE=hith_admitdata
DATAVERSE_ALT_KEY=patientid
```

---

# Azure Function

These variables support the processing engine.

| Variable | Description |
|-----------|-------------|
| FUNCTION_APP_NAME | Azure Function application |
| FUNCTION_TIMEOUT | Processing timeout (seconds) |
| LOG_LEVEL | Logging level |

### Example

```env
FUNCTION_APP_NAME=home-hith-document-processor
FUNCTION_TIMEOUT=300
LOG_LEVEL=INFO
```

---

# Processing Configuration

These variables control text extraction and processing behavior.

| Variable | Description |
|-----------|-------------|
| CHUNK_SIZE | Text chunk size |
| CHUNK_OVERLAP | Chunk overlap |
| MAX_DOCUMENT_SIZE_MB | Maximum document size |
| RETRY_COUNT | Retry attempts |

### Example

```env
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_DOCUMENT_SIZE_MB=20
RETRY_COUNT=3
```

---

# Power Apps

These variables support dashboard configuration.

| Variable | Description |
|-----------|-------------|
| POWERAPPS_ENVIRONMENT | Power Platform environment |
| DASHBOARD_NAME | Dashboard application name |

### Example

```env
POWERAPPS_ENVIRONMENT=Home-HITH-Dev
DASHBOARD_NAME=Home-HITH Dashboard
```

---

# Template Generation

These variables support Word document generation.

| Variable | Description |
|-----------|-------------|
| TEMPLATE_LIBRARY | SharePoint template library |
| TEMPLATE_NAME | Word template filename |
| OUTPUT_LIBRARY | Output document library |

### Example

```env
TEMPLATE_LIBRARY=AdmitTemplates
TEMPLATE_NAME=HITH_Admit_Template.docx
OUTPUT_LIBRARY=GeneratedDocuments
```

---

# Complete Example .env

```env
# Azure Authentication
TENANT_ID=<tenant-id>
CLIENT_ID=<client-id>
CLIENT_SECRET=<client-secret>
AUTHORITY=https://login.microsoftonline.com/<tenant-id>

# Microsoft Graph
GRAPH_ENDPOINT=https://graph.microsoft.com/v1.0
GRAPH_SCOPE=https://graph.microsoft.com/.default

# SharePoint
SHAREPOINT_SITE=Home-HITH
SHAREPOINT_DRIVE=Documents
SHAREPOINT_FOLDER=AdmitDocuments

# Azure AI Document Intelligence
DOC_INTELLIGENCE_ENDPOINT=https://homehith-ai.cognitiveservices.azure.com/
DOC_INTELLIGENCE_KEY=<secret>
DOC_INTELLIGENCE_MODEL=admit-documents-model

# Dataverse
DATAVERSE_URL=https://org.crm6.dynamics.com
DATAVERSE_TABLE=hith_admitdata
DATAVERSE_ALT_KEY=patientid

# Azure Function
FUNCTION_APP_NAME=home-hith-document-processor
FUNCTION_TIMEOUT=300
LOG_LEVEL=INFO

# Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_DOCUMENT_SIZE_MB=20
RETRY_COUNT=3

# Power Apps
POWERAPPS_ENVIRONMENT=Home-HITH-Dev
DASHBOARD_NAME=Home-HITH Dashboard

# Template Generation
TEMPLATE_LIBRARY=AdmitTemplates
TEMPLATE_NAME=HITH_Admit_Template.docx
OUTPUT_LIBRARY=GeneratedDocuments
```

---

# Security Guidelines

- Never commit `.env` files to GitHub.
- Store secrets in Azure Key Vault where possible.
- Rotate application secrets regularly.
- Apply least-privilege permissions to Azure App Registrations.
- Use separate configurations for Development, Test, and Production environments.
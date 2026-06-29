# Deployment Guide

## Overview

This guide describes how to deploy the Home-HITH admit processing pipeline using:

- SharePoint Online for intake documents
- Power Automate for trigger orchestration
- Azure Functions for pipeline execution
- Azure AI Document Intelligence for extraction
- Microsoft Dataverse for structured data storage
- Power Apps for operational dashboard and template generation

The repository contains the pipeline implementation in `src/python/document_processor.py` and Power Automate flow definitions in `src/flows/`.

---

## Prerequisites

1. Azure subscription with sufficient permissions to create:
   - Azure Function App
   - Storage account
   - Azure AI Document Intelligence / Cognitive Services resource
   - Azure App Registration
2. Microsoft 365 tenant with:
   - SharePoint Online site and document library
   - Power Automate licensing for premium connectors
   - Dataverse environment
3. Local development environment:
   - Python 3.10+ installed
   - `pip` available
   - Azure Functions Core Tools installed if deploying from local machine

---

## Azure Resources

Create the following resources in your Azure subscription:

- Resource group for Home-HITH
- Storage account for the Function App
- Azure Function App (Python runtime)
- Azure AI Document Intelligence resource or Cognitive Services resource with a Document Intelligence model
- App Registration in Azure AD for service-to-service authentication

---

## App Registration

1. Register a new application in Azure Active Directory.
2. Create a client secret and save the value.
3. Assign API permissions:
   - Microsoft Graph: `Files.Read.All`, `Sites.Read.All` (application permissions)
   - Dynamics CRM: `user_impersonation` (application permission)
4. Grant admin consent for the permissions.

This app registration is used by both SharePoint and Dataverse clients in the Python pipeline.

---

## SharePoint Configuration

1. Create or identify a SharePoint site for the Home-HITH intake documents.
2. Create a document library named `Admit Documents` or update the `SHAREPOINT_FOLDER_PATH` setting.
3. Add a secure folder structure if required and upload test paired documents.
4. Ensure the service principal has access to the SharePoint site and drive.

Document pairing convention:

- `patientId_facesheet.pdf`
- `patientId_assessment.docx`

Example:

```text
12345_facesheet.pdf
12345_assessment.docx
```

---

## Dataverse Configuration

1. Create a Dataverse table for admit records.
2. The repository includes `src/dataverse/admit_data_table.json` with the expected column schema.
3. Import that schema into Dataverse or create a table named `hith_admitdatas` with the mapped fields.
4. Confirm the table contains fields used by the pipeline and flows, such as:
   - `hith_patientid`
   - `hith_patientfirstname`
   - `hith_dateofbirth`
   - `hith_admitdate`
   - `hith_admittemplatepopulated`

---

## Azure AI Document Intelligence

1. Create an Azure AI Document Intelligence resource or a Cognitive Services resource with Document Intelligence enabled.
2. Train and deploy a model for admit documents, or use an existing model with the identifier configured as `AZURE_DOC_INTELLIGENCE_MODEL_ID`.
3. Save the endpoint URL and key for the environment configuration.

---

## Azure Functions

Home-HITH uses `src/python/document_processor.py` as the pipeline orchestrator. To host it in Azure Functions, the easiest path is to create a Python HTTP-trigger Function App that invokes the document processor.

### Recommended deployment approach

1. Create a Python Azure Function App (Linux or Windows) with runtime 3.10 or higher.
2. Configure the Function App name and storage account.
3. Enable the Python worker and set `FUNCTIONS_WORKER_RUNTIME=python`.
4. Deploy the repository code to the Function App, including the `src/python/` folder and its dependencies.

### App settings

Configure the following application settings in the Function App:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `SHAREPOINT_SITE_ID`
- `SHAREPOINT_DRIVE_ID`
- `SHAREPOINT_FOLDER_PATH` (default: `Admit Documents`)
- `AZURE_DOC_INTELLIGENCE_ENDPOINT`
- `AZURE_DOC_INTELLIGENCE_KEY`
- `AZURE_DOC_INTELLIGENCE_MODEL_ID` (default: `admit-documents-model`)
- `DATAVERSE_ENVIRONMENT_URL`
- `DATAVERSE_TABLE_NAME` (default: `hith_admitdatas`)
- `CHUNK_SIZE` (optional; default: `2000`)
- `CHUNK_OVERLAP` (optional; default: `200`)
- `LOG_LEVEL` (optional; default: `INFO`)
- `FUNCTIONS_WORKER_RUNTIME=python`

### Local deployment example

From the repository root:

```powershell
cd d:\GitHub\Home-HITH
python -m pip install -r requirements.txt
func azure functionapp publish <function-app-name> --python
```

If you do not yet have an Azure Function wrapper in the repo, create an HTTP-trigger function named `ProcessAdmitDocuments` and call into `document_processor.py` from the function handler.

### Function endpoint

Your Power Automate flow expects an HTTP POST endpoint that accepts JSON with a `patientId` value:

```json
{ "patientId": "12345" }
```

Set the `processorFunctionUrl` parameter in the imported flow to the function endpoint URL, including the function key if required.

---

## Power Automate Flows

Import the flow definitions from:

- `src/flows/process-admit-documents.json`
- `src/flows/populate-admit-template.json`

Update the connection references and flow parameters after import:

- `sharePointSiteUrl` → your SharePoint site URL
- `processorFunctionUrl` → Azure Function endpoint
- `dataverseEnvironmentUrl` → Dataverse environment URL
- `templateLibrary` and `outputLibrary` for the admit template flow

Validate that the file names and library locations match the values used in SharePoint.

---

## Power Apps Dashboard

1. Build or import a Power Apps canvas app that reads from the `hith_admitdatas` Dataverse table.
2. Create views for admit record status, extracted fields, and processing results.
3. Add filters for `hith_admittemplatepopulated` and date fields.

---

## Validation Checklist

- [ ] Azure Function App created and configured
- [ ] App registration created with Graph and Dataverse permissions
- [ ] SharePoint intake library exists and contains paired documents
- [ ] Dataverse `hith_admitdatas` table is imported and available
- [ ] AI Document Intelligence endpoint and model are configured
- [ ] Power Automate flows imported and parameterized
- [ ] Function endpoint validated with a test POST request
- [ ] Dashboard connects to the Dataverse table successfully

---

## Troubleshooting

- If the flow fails with `401`, verify the Function App URL and function key.
- If the pipeline fails to access SharePoint, confirm the app registration has Graph permissions and the service principal has site access.
- If Dataverse upserts fail, confirm `DATAVERSE_ENVIRONMENT_URL` is correct and the client secret is valid.
- If the AI call fails, verify the Document Intelligence endpoint, key, and model ID.
- Use Application Insights or Function App logs to inspect runtime errors.

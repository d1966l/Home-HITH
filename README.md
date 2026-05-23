# Home-HITH – Admit Process Document Automation

> **Admit process document automation and data processes with dashboard**

Home-HITH automates the intake of paired PDF and MS Word admit documents stored in
SharePoint by using an already-trained Azure AI Document Intelligence model to
extract structured patient data, saving it to Microsoft Dataverse, powering an
AI dashboard, and auto-populating the Admit Template document.

---

## Architecture

```
SharePoint
  │  (PDF + Word admit document pairs)
  │
  ▼
Power Automate Flow                     ← triggered on file creation
  │  process-admit-documents.json
  │
  ▼
Azure Function  ──────────────────────► document_processor.py
  │                                        │
  │   ┌──────────────────────────────┐    │
  │   │  sharepoint_client.py        │◄───┤  download paired docs
  │   │  chunker.py                  │◄───┤  extract & chunk text
  │   │  ai_model_client.py          │◄───┤  call AI model
  │   │  dataverse_client.py         │◄───┤  upsert to Dataverse
  │   └──────────────────────────────┘    │
  │
  ▼
Dataverse  (hith_admitdata table)
  │
  ├──► Power Apps – AI Dashboard          ← real-time admit data view
  │
  └──► Power Automate Flow                ← triggered on new/updated rows
         populate-admit-template.json
           │
           ▼
         SharePoint  (populated HITH_Admit_<patientID>_<date>.docx)
```

---

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `sharepoint_client.py` | `src/python/` | Authenticate to Microsoft Graph and retrieve paired admit documents |
| `chunker.py` | `src/python/` | Extract text from PDF/Word files and split into overlapping chunks |
| `ai_model_client.py` | `src/python/` | Submit documents to Azure AI Document Intelligence; parse extracted fields |
| `dataverse_client.py` | `src/python/` | Upsert `AdmitRecord` data into the Dataverse `hith_admitdata` table |
| `document_processor.py` | `src/python/` | Orchestrate the full pipeline; CLI entry point |
| `admit_data_table.json` | `src/dataverse/` | Dataverse table schema (columns, alternate keys, views) |
| `process-admit-documents.json` | `src/flows/` | Power Automate flow – SharePoint trigger → pipeline |
| `populate-admit-template.json` | `src/flows/` | Power Automate flow – Dataverse trigger → Word template population |
| `ai-dashboard.md` | `src/power-apps/` | AI Dashboard canvas app specification |
| `admit-template.md` | `src/power-apps/` | Admit Template canvas app specification |

---

## Document Pairing Convention

Documents must be stored in the configured SharePoint folder using this naming
convention:

```
<patientID>_facesheet.<pdf|docx>        ← primary document
<patientID>_assessment.<pdf|docx>       ← secondary document
```

For example:
```
patient_12345_facesheet.pdf
patient_12345_assessment.docx
```

The pipeline extracts `12345` as the patient identifier and pairs the two files
automatically.

---

## Setup

### Prerequisites

- Python 3.10+
- Azure subscription with:
  - App Registration (client credentials) with access to Microsoft Graph and Dataverse
  - Azure AI Document Intelligence resource with the trained `admit-documents-model`
- Microsoft 365 / Power Platform environment with:
  - Dataverse instance
  - SharePoint Online site
  - Power Automate (premium connectors)

### 1. Create the Dataverse table

Import `src/dataverse/admit_data_table.json` into your Dataverse environment via
the Power Platform admin centre or the Power Platform CLI:

```bash
pac solution import --path src/dataverse/admit_data_table.json
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in all values
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the pipeline

Process all pending document pairs:

```bash
cd src/python
python document_processor.py
```

Reprocess a single patient:

```bash
python document_processor.py --patient 12345
```

### 5. Import Power Automate flows

Import `src/flows/process-admit-documents.json` and
`src/flows/populate-admit-template.json` into your Power Automate environment.
Update the connection references to point to your SharePoint site, Dataverse
environment, and Azure Function endpoint.

### 6. Create the Admit Template

Upload a Word document named `HITH_Admit_Template.docx` to the `Admit Templates`
library in SharePoint.  Add merge fields as documented in
[`src/power-apps/admit-template.md`](src/power-apps/admit-template.md).

### 7. Build the Power Apps

Follow the specifications in:
- [`src/power-apps/ai-dashboard.md`](src/power-apps/ai-dashboard.md) – AI Dashboard
- [`src/power-apps/admit-template.md`](src/power-apps/admit-template.md) – Admit Template app

---

## Running Tests

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=src/python
```

---

## Environment Variables Reference

See [`.env.example`](.env.example) for all configuration variables.

---

## License

MIT – see [LICENSE](LICENSE).

$Path = "docs\architecture\solution-overview.md"

@"
# Home-HITH Architecture

## Overview

Home-HITH automates admit-document processing using:

- SharePoint Online
- Power Automate
- Azure Functions
- Azure AI Document Intelligence
- Dataverse
- Power Apps

## Data Flow

SharePoint
→ Power Automate
→ Azure Function
→ AI Extraction
→ Dataverse
→ Power Apps
→ Admit Template Generation

## Architecture Diagram

![Architecture](../screenshots/01-architecture-overview.png)

## Processing Pipeline

1. Admit documents arrive in SharePoint.
2. Power Automate detects new files.
3. Azure Function downloads paired documents.
4. Azure AI Document Intelligence extracts structured data.
5. Dataverse stores patient records.
6. Power Apps displays operational dashboards.
7. Admit Template documents are generated automatically.

"@ | Set-Content $Path

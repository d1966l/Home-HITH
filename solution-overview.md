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

```mermaid
flowchart TD

SP[SharePoint Online]
PA[Power Automate]
AF[Azure Function]
AI[Azure AI Document Intelligence]
DV[Dataverse]
APP[Power Apps Dashboard]
DOC[Admit Template Generation]

SP --> PA
PA --> AF
AF --> AI
AI --> DV
DV --> APP
APP --> DOC
```
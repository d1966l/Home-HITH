# Home-HITH Architecture

## Overview

Home-HITH automates admit-document processing using:

- SharePoint Online
- Power Automate
- Azure Functions
- Azure AI Document Intelligence
- Microsoft Dataverse
- Power Apps

---

## Architecture Diagram

![Home-HITH Architecture](../screenshots/01-architecture-overview.png)

*Figure 1. End-to-end Home-HITH admit document automation architecture.*

---

## Business Objective

Home-HITH streamlines the intake and processing of hospital-at-home (HITH) admission documents by automatically extracting patient information from paired PDF and Word documents stored in SharePoint, transforming the data into structured records within Dataverse, and generating completed admit templates for clinical workflows.

---

## Data Flow

```text
SharePoint Online
        │
        ▼
Power Automate
        │
        ▼
Azure Function
        │
        ▼
Azure AI Document Intelligence
        │
        ▼
Microsoft Dataverse
        │
        ├──────────────► Power Apps Dashboard
        │
        ▼
Admit Template Generation
        │
        ▼
Completed HITH Admit Document
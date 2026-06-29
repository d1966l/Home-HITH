$Gallery = "docs\screenshots\README.md"

@"
# Screenshot Gallery

## Architecture

![Architecture](01-architecture-overview.png)

## Solution Architecture

![Architecture](docs/screenshots/01-architecture-overview.png)

For detailed architecture documentation see:

- docs/architecture/solution-overview.md
- docs/deployment/deployment-guide.md
- docs/deployment/environment-variables.md

## Planned Screenshots

| Screenshot | Status |
|------------|--------|
| SharePoint Intake | Pending |
| Power Automate Flow | Pending |
| Azure Function | Pending |
| AI Model | Pending |
| Dataverse | Pending |
| Dashboard | Pending |
| Admit Template | Pending |

"@ | Set-Content $Gallery

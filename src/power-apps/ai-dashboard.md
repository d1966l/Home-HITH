## HITH AI Dashboard – Power Apps Canvas App Specification

### Overview
The AI Dashboard is a Power Apps canvas app that surfaces the admit data stored
in the Dataverse `hith_admitdata` table.  It is designed for intake coordinators,
clinical managers, and administrators who need a live view of incoming patient
admissions.

---

### Screen: Home / KPI Summary

**Data source:** `hith_admitdatas` table

| Control         | Type             | Value / Formula                                                                 |
|-----------------|------------------|---------------------------------------------------------------------------------|
| lbl_total       | Label            | `"Total Admits: " & CountRows(hith_admitdatas)`                                 |
| lbl_pending     | Label            | `"Pending Templates: " & CountRows(Filter(hith_admitdatas, !hith_admittemplatepopulated))` |
| lbl_avg_conf    | Label            | `"Avg AI Confidence: " & Text(Average(hith_admitdatas, hith_confidencescore)*100, "0.0") & "%"` |
| chart_admits    | Column chart     | X-axis: `hith_admitdate` (grouped by week); Y-axis: count of records            |
| chart_insurance | Pie chart        | Grouped by `hith_insurancename`; shows distribution of payer mix                |
| chart_diagnosis | Bar chart        | Top 10 primary diagnoses by frequency                                           |
| btn_refresh     | Button           | `Refresh(hith_admitdatas)`                                                      |

---

### Screen: Patient List

**Data source:** `hith_admitdatas` table  
**Layout:** Gallery control (vertical)

| Control              | Type             | Value / Formula                                                                                   |
|----------------------|------------------|----------------------------------------------------------------------------------------------------|
| gal_patients         | Gallery          | `SortByColumns(hith_admitdatas, "hith_admitdate", Descending)`                                    |
| gal_patients.Name    | Label (row)      | `ThisItem.hith_patientlastname & ", " & ThisItem.hith_patientfirstname`                           |
| gal_patients.DOB     | Label (row)      | `"DOB: " & Text(ThisItem.hith_dateofbirth, DateTimeFormat.ShortDate)`                             |
| gal_patients.Diag    | Label (row)      | `ThisItem.hith_primarydiagnosis`                                                                  |
| gal_patients.Conf    | Label (row)      | `"AI Conf: " & Text(ThisItem.hith_confidencescore*100, "0") & "%"`                                |
| txt_search           | Text input       | Filters gallery: `Filter(hith_admitdatas, StartsWith(hith_patientlastname, txt_search.Text))`      |
| btn_open             | Button (row)     | `Navigate(Screen_PatientDetail, ScreenTransition.Fade, {selectedRecord: ThisItem})`               |

---

### Screen: Patient Detail

**Data source:** `selectedRecord` (passed via navigation context)

Displays all fields from the selected `hith_admitdata` row in a form layout:

- Patient Demographics (name, DOB, gender, address, phone)
- Insurance (insurance name, insurance ID)
- Clinical Information (physician, admit date, primary & secondary diagnoses)
- Care Plan (skilled services, medications, allergies, functional limitations, mental status, prognosis)
- Processing Metadata (source files, AI confidence score, processed-on timestamp)

| Control                 | Type   | Value / Formula                                              |
|-------------------------|--------|--------------------------------------------------------------|
| btn_populate_template   | Button | `Power Automate – Populate Admit Template flow (selected patient)` |
| btn_back                | Button | `Back()`                                                    |

---

### Power Automate Integration

The **Populate Admit Template** button on the Patient Detail screen triggers the
`HITH – Populate Admit Template` Power Automate flow:

```plaintext
PowerAutomateFlows.Run("HITH_PopulateAdmitTemplate", selectedRecord.hith_patientid)
```

---

### Security Roles

| Role                    | Access                                |
|-------------------------|---------------------------------------|
| HITH Intake Coordinator | Read + Create on `hith_admitdata`     |
| HITH Clinical Manager   | Read on `hith_admitdata`              |
| HITH Administrator      | Full access to all tables and flows   |

---

### Connection References

| Logical Name                  | Connector                     |
|-------------------------------|-------------------------------|
| `hith_DataverseConnection`    | Microsoft Dataverse           |
| `hith_PowerAutomateConnection`| Power Automate Management     |

## HITH Admit Template – Power Apps Canvas App Specification

### Overview
The Admit Template app allows intake staff to review AI-extracted admit data and
generate a pre-filled Admit Template document with a single click.

The app reads from the `hith_admitdata` Dataverse table and invokes the
`HITH – Populate Admit Template` Power Automate flow to produce a populated
Word document saved back to SharePoint.

---

### Screen: Template Queue

Lists patients whose Admit Template has **not yet been populated**.

**Data source:** `Filter(hith_admitdatas, !hith_admittemplatepopulated)`

| Control           | Type    | Value / Formula                                                              |
|-------------------|---------|------------------------------------------------------------------------------|
| gal_queue         | Gallery | `SortByColumns(Filter(hith_admitdatas, !hith_admittemplatepopulated), "hith_admitdate", Ascending)` |
| gal_queue.Name    | Label   | `ThisItem.hith_patientlastname & ", " & ThisItem.hith_patientfirstname`      |
| gal_queue.Date    | Label   | `Text(ThisItem.hith_admitdate, DateTimeFormat.ShortDate)`                    |
| gal_queue.Conf    | Label   | `Text(ThisItem.hith_confidencescore * 100, "0") & "% confidence"`            |
| btn_generate      | Button  | Triggers Populate flow for selected patient (see below)                      |
| btn_review        | Button  | `Navigate(Screen_AdmitReview, ScreenTransition.Slide, {rec: ThisItem})`      |

**Generate button logic:**
```plaintext
Set(varIsLoading, true);
PowerAutomateFlows.Run(
    "HITH_PopulateAdmitTemplate",
    gal_queue.Selected.hith_patientid
);
Refresh(hith_admitdatas);
Set(varIsLoading, false);
Notify("Admit Template generated successfully", NotificationType.Success)
```

---

### Screen: Admit Review (pre-generation review)

Allows staff to review and correct AI-extracted values before generating the
template.

| Section              | Fields displayed                                                   |
|----------------------|--------------------------------------------------------------------|
| Patient Demographics | First name, last name, DOB, gender, address, phone                 |
| Insurance            | Insurance name, insurance ID                                       |
| Clinical             | Admit date, physician name, NPI, referring physician               |
| Diagnoses            | Primary diagnosis, secondary diagnoses (editable multi-line text)  |
| Care Plan            | Skilled services, medications, allergies, functional limitations   |
| AI Metadata          | Confidence score (read-only), source files (read-only)             |

All editable fields use a **Form** control bound to the selected `hith_admitdata`
row.  On submit, the form patches Dataverse:

```plaintext
SubmitForm(frm_AdmitReview);
Navigate(Screen_TemplateQueue, ScreenTransition.Back)
```

---

### Admit Template Word Document – Merge Fields

The Word document `HITH_Admit_Template.docx` stored in SharePoint uses the
following merge fields (matched to the `Populate_Word_template` action in the
Power Automate flow):

| Merge Field             | Maps to Dataverse Column            |
|-------------------------|-------------------------------------|
| `«PatientID»`           | `hith_patientid`                    |
| `«PatientFirstName»`    | `hith_patientfirstname`             |
| `«PatientLastName»`     | `hith_patientlastname`              |
| `«DateOfBirth»`         | `hith_dateofbirth`                  |
| `«Gender»`              | `hith_gender`                       |
| `«Address»`             | `hith_address`                      |
| `«PhoneNumber»`         | `hith_phonenumber`                  |
| `«InsuranceID»`         | `hith_insuranceid`                  |
| `«InsuranceName»`       | `hith_insurancename`                |
| `«PrimaryDiagnosis»`    | `hith_primarydiagnosis`             |
| `«PhysicianName»`       | `hith_physicianname`                |
| `«PhysicianNPI»`        | `hith_physiciannpi`                 |
| `«ReferringPhysician»`  | `hith_referringphysician`           |
| `«AdmitDate»`           | `hith_admitdate`                    |
| `«DischargeDate»`       | `hith_dischargedate`                |
| `«FunctionalLimitations»` | `hith_functionallimitations`      |
| `«MentalStatus»`        | `hith_mentalstatus`                 |
| `«Prognosis»`           | `hith_prognosis`                    |

---

### Connection References

| Logical Name                  | Connector              |
|-------------------------------|------------------------|
| `hith_DataverseConnection`    | Microsoft Dataverse    |
| `hith_SharePointConnection`   | SharePoint             |
| `hith_PowerAutomateConnection`| Power Automate         |

---
title: bioworld_poc
app_file: ui/app.py
sdk: gradio
sdk_version: 4.44.1
---
# BioWorld Licensing Rule Engine

## How to Run

1. Open terminal and navigate to the project:
   ```
   cd /Users/shivadityakr/Documents/BIOWORLD-POC/licensing-validator
   ```

2. Activate the virtual environment:
   ```
   source ../myenv/bin/activate
   ```

3. Launch the UI:
   ```
   python ui/app.py
   ```

4. Open the browser at **http://localhost:7860**

5. In the UI:
   - Select **"The Walt Disney Company"** from the licensor dropdown
   - Upload the input file: `config/disney/Styles 16 1.xlsx`
   - Click **"Run Validation"**
   - Browse the style-wise results (each style card shows pass/fail per rule)
   - Click **"Download Report"** to get the full Excel report

---

## Rules and Config File Mapping

All config files are in `config/disney/`.

| Rule | What it checks | Config file | Sheet |
|------|----------------|-------------|-------|
| **R1.1** Mandatory Data | 7 required fields + Property in approved list | `DISNEY PROPERTIES 7.xlsx` | Sheet1 (Disney + Pixar property lists) |
| **R1.2** SKU Suffix | Style # suffix matches property type | `DISNEY PROPERTIES 7.xlsx` | Sheet2 (suffix codes: DSX/DST/DSM/DSC/DCH/DSY) |
| **R2.1** Property-Art | Art Ref # present when Property present | None (logic check) | — |
| **R2.2** Character Mapping | Property exists in hierarchy | `BioWorld Cross Franchise Property Hierarchy_all franchises 10.xlsx` | Disney, Marvel, Lucas sheets |
| **R3.1** Property Rules | Hierarchy + DO NOT USE + property-specific rules | `BioWorld Cross Franchise Property Hierarchy_all franchises 10.xlsx` | Disney, Marvel, Lucas sheets |
| **R3.2** Property Mixing | Property belongs to a known franchise | Same as R3.1 | — |
| **R4.1** Rights & Distribution | Category + Item Type + retailer restrictions | `Copy of Disney_Apparel Accessories_New License Summary_...xlsx` | "Definitions" sheet |
| **R5.1** Packaging | Packaging type, retailer-specific rules | None (logic from Pre-check steps) | — |
| **R5.2** TM Validation | (Disabled) | — | — |

---

## Reference Documents (in `config/disney/temp/`)

| File | Purpose |
|------|---------|
| `Pre-check steps.docx` | Operational checklist — source for property-specific rules and packaging rules |
| `Solution_Definition_Document_rules_pahse_1.docx` | High-level rule engine spec |
| `Module list.xlsx` | Rule-to-lookup mapping table |
| `Overall Data Mapping.docx` | Full rule specification with data flow |

See `MANUAL_TESTING.md` for detailed testing steps and examples.

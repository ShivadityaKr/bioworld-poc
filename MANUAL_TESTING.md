# Manual Testing Guide — BioWorld Licensing Rule Engine

This document provides step-by-step instructions and real examples to manually verify each rule against the actual config files.

---

## Files You Need Open

| # | File | Location | Used by |
|---|------|----------|---------|
| 1 | **Styles (input data)** | `config/disney/Styles 16 1.xlsx` | All rules (input) |
| 2 | **Disney Properties** | `config/disney/DISNEY PROPERTIES 7.xlsx` | R1.1 (Sheet1: approved list), R1.2 (Sheet2: suffix codes) |
| 3 | **NLS Apparel** | `config/disney/Copy of Disney_Apparel Accessories_New License Summary_...xlsx` | R4.1 ("Definitions" sheet: categories + items, "New License Summary" sheet: NLS suffix cross-ref) |
| 4 | **Property Hierarchy** | `config/disney/BioWorld Cross Franchise Property Hierarchy_all franchises 10.xlsx` | R2.2, R3.1, R3.2 (Disney/Marvel/Lucas sheets) |
| 5 | **Pre-check steps** | `config/disney/temp/Pre-check steps.docx` | R3.1 (property-specific rules), R5.1 (packaging rules) — reference doc |

---

## Files Not Currently Used by Rules

| File | Why |
|------|-----|
| `DISNEY PROPERTIES 5.xlsx` (temp) | Older version of Properties file (Sheet1 only, no suffix codes) |
| `Copy of Disney_Home_New License Summary...xlsx` | Home category NLS. Not wired to R4.1 — only Apparel NLS is used |
| PDF files (TM Guideline, Brand Management, etc.) | Relevant to R5.2 TM Validation (disabled). Cannot be parsed |
| `Solution_Definition_Document_rules_pahse_1.docx` (temp) | High-level spec doc — same content as Module list.xlsx |

---

## Test Setup

1. Open terminal → `cd licensing-validator`
2. Activate env → `source ../myenv/bin/activate`
3. Run app → `python ui/app.py`
4. Open browser → `http://localhost:7860`
5. Select "The Walt Disney Company" → Upload `Styles 16 1.xlsx` → Click "Run Validation"

---

## Gate Rule Behavior

R1 is the **gate rule group**. If R1.1 OR R1.2 fails for a style, all rules R2–R5 are **skipped**.

Out of 262 styles: **12 styles pass the R1 gate**. The rest fail at R1 and get R2–R5 skipped.

**R1.1 failure breakdown:**
- 208 styles: Missing required fields (mostly Art Ref #)
- 39 styles: Property not in approved DISNEY PROPERTIES list

---

## R1.1 — Mandatory Data Validation

**What to check:**
1. Are these 7 fields present and non-empty? Style #, Licensor, Property, Art Ref #, Item Type, Customer, Division
2. Is the declared Property in the approved list from `DISNEY PROPERTIES 7.xlsx` Sheet1?

**Config file:** `DISNEY PROPERTIES 7.xlsx` → Sheet1 has Disney properties (column A) and Pixar properties (column C)

### Example 1: PASS — Style `TNUB9L5DSY`

| Field | Value | Present? |
|-------|-------|----------|
| Style # | TNUB9L5DSY | Yes |
| Licensor | Disney | Yes |
| Property | Disney Princess | Yes |
| Art Ref # | (has value) | Yes |
| Item Type | Button | Yes |
| Customer | Box Lunch | Yes |
| Division | Accessories | Yes |

Property check: Open DISNEY PROPERTIES 7.xlsx → Sheet1 → look for "DISNEY PRINCESS" → **Found** (row 19: "19. DISNEY PRINCESS")

**All fields present + property approved → R1.1 should PASS**

### Example 2: FAIL (missing field) — Style `FPY65V2DSC`

Art Ref # is empty → **R1.1 FAIL: "Missing required fields: Art Reference Number"**

### Example 3: FAIL (property not approved) — Style `LRY6WVPDSC`

All 7 fields are present, but Property = "Lilo & Stitch".
Open DISNEY PROPERTIES 7.xlsx → Sheet1 → search for "Lilo & Stitch" → **Not found**.
The file has "48. LILO & STITCH (live action)" but NOT "Lilo & Stitch" by itself.

**Property not in approved list → R1.1 FAIL**

### Properties that fail the approved list check (11 distinct)

| Centric Property | What DISNEY PROPERTIES has instead |
|------------------|-----------------------------------|
| Aristocats | THE ARISTOCATS |
| Cars | CARS, CARS 2, and CARS 3 |
| Disney Classic Characters | (not listed — different concept) |
| Frozen 2 | FROZEN II |
| Kingdom Hearts | KINGDOM HEARTS III / KINGDOM HEARTS FRANCHISE |
| Lilo & Stitch | LILO & STITCH (live action) |
| Mickey Mouse Classic | (not listed — Centric-specific name) |
| Minnie Mouse Classic | (not listed — Centric-specific name) |
| Nightmare Before Christmas | TIM BURTON'S THE NIGHTMARE BEFORE CHRISTMAS |
| The Little Mermaid | THE LITTLE MERMAID (live action) |
| Toy Story | TOY STORY, TOY STORY 2, TOY STORY 3, and TOY STORY 4 |

---

## R1.2 — SKU Suffix Validation

**What to check:** Does the last 3 characters of the Style # match a valid suffix code for the property type?

**Config file:** `DISNEY PROPERTIES 7.xlsx` → Sheet2 has the 6 suffix categories:

| Category | Suffix |
|----------|--------|
| Pixar Properties | DSX |
| Toddler Properties | DST |
| New Movies | DSM |
| Disney Classics | DSC |
| Disney Channel Properties | DCH |
| Standard characters / Princess | DSY |

Also cross-references the NLS for per-property suffix when available.

### Example 1: PASS — Style `TNUB9L5DSY`

- Style # ends with `DSY`
- Property = "Disney Princess" → NLS maps this to suffix `DSY`
- **Match → R1.2 PASS**

### Example 2: PASS — Style `VHU9L9MDSX`

- Style # ends with `DSX`
- Property = "Up" → Pixar property → NLS maps to `DSX`
- **Match → R1.2 PASS**

### Example 3: FAIL — Style `BPY6774FZN`

- Style # ends with `FZN`
- Property = "Frozen 2" → not in DISNEY PROPERTIES Sheet1 (Disney or Pixar list)
- `FZN` is not one of the 6 valid suffix codes (DSX/DST/DSM/DSC/DCH/DSY)
- **Unrecognized suffix → R1.2 FAIL**

(Note: NLS actually maps FROZEN to FZN and FROZEN II to FRZ — these are special suffixes not in the DISNEY PROPERTIES Sheet2 mapping)

---

## R2.1 — Property-Art Cross Check

**What to check:** If "Property" has a value, does "Art Ref #" also have a value?

**Config file:** None — logic check on Styles file.

### Example: PASS — All 12 gate-passing styles

All 12 styles that pass R1 have both Property and Art Ref # filled.

---

## R2.2 — Character Mapping Validation

**What to check:** Does the declared Property exist in the Property Hierarchy file?

**Config file:** `BioWorld Cross Franchise Property Hierarchy_all franchises 10.xlsx` → 3 sheets (Disney, Marvel, Lucas)

### Example 1: PASS — Style `TNUB9L5DSY`

Property = "Disney Princess" → open hierarchy → Disney sheet → **found**

### Example 2: PASS — Style `VHUBCCGDSC`

Property = "Muppets" → Disney sheet → **found**

---

## R3.1 — Property-Specific Rules

**What to check:**
1. Property exists in hierarchy (exact, case-insensitive)
2. Property is NOT flagged "DO NOT USE"
3. Property-specific rules from Pre-check steps apply

**Config file:** `BioWorld Cross Franchise Property Hierarchy_all franchises 10.xlsx`

**Property-specific rules (from Pre-check steps doc):**

| Property | Rule |
|----------|------|
| Nightmare Before Christmas (NBC) | VHS art/item type NOT allowed |
| Tiana | No frog usage allowed |
| Cruella | No spots on coat, no hanging tails on bag |
| Disney Princess | Must have PMS colours call out [REVIEW] |

### Example 1: FAIL [REVIEW] — Style `TNUB9L5DSY`

- Property = "Disney Princess" → found in hierarchy ✓, not DO NOT USE ✓
- But Princess-specific rule triggers: **"Must have PMS colours call out"**
- This is a [REVIEW] item — needs human verification of the artwork
- **R3.1 FAIL: "[REVIEW] Princesses: Must have PMS colours call out"**

### Example 2: FAIL — Style `PKAABHGDSY`

- Property = "Disney Brand Name"
- Search all 3 sheets → **not found** in hierarchy
- **R3.1 FAIL: "Property 'Disney Brand Name' not found"**

### Example 3: PASS — Style `PKU9D6HDSC`

- Property = "Winnie The Pooh" → found in Disney sheet → not DO NOT USE → no specific rules
- **R3.1 PASS**

---

## R3.2 — Property Mixing Validation

**What to check:** Does the Property belong to a known franchise?

**Config file:** Same hierarchy file. The sheet where the property is found = its franchise.

### Example 1: PASS — Style `VHUBCCGDSC`

- Property = "Muppets" → found in Disney sheet → franchise = Disney
- **R3.2 PASS**

### Example 2: FAIL — Style `PKAABHGDSY`

- Property = "Disney Brand Name" → not found in any sheet
- **R3.2 FAIL**

---

## R4.1 — Rights & Distribution Validation

**What to check:**
1. Is "Item Type Category" a licensed category in the NLS Definitions?
2. Is "Item Type" a valid item under that category?
3. Are there retailer restrictions for this property?
4. Is this a specialty-only property?

**Config file:** NLS Apparel → **"Definitions" sheet**

**Retailer restrictions (from Pre-check steps):**
- Kingdom Hearts: only Hot Topic & Box Lunch
- Lilo & Stitch / NBC: specialty only (2025)

### Example 1: PASS — Style `TNUB9L5DSY`

- Item Type Category = "Small Accessories" → **found** in NLS Definitions
- Item Type = "Button" → **found** under Small Accessories
- Property = "Disney Princess" → no retailer restrictions
- **R4.1 PASS**

### Example 2: FAIL — Style `EYG8VV5DSY`

- Item Type Category = "Small Accessories" → **found**
- Item Type = "Eyeglass" → **NOT found** (NLS has "Eyeglasses" not "Eyeglass")
- **R4.1 FAIL: "Item Type 'Eyeglass' not found"**

### Example 3: FAIL — Style `PKU9D6HDSC`

- Item Type Category = "Packaging" → **NOT found** in NLS licensed categories
- **R4.1 FAIL: "Category 'Packaging' is not licensed"**

### Example 4: FAIL — Style `VHUBCCGDSC`

- Item Type Category = "Home Décor" → **NOT found** (NLS has "Home" not "Home Décor")
- **R4.1 FAIL: "Category 'Home Décor' is not licensed"**

### Licensed categories (from NLS Definitions)

Apparel, Bags, Cold Weather, Collectibles, Drinkware, Footwear, Headwear, Home, Hosiery, Jewelry, Kitchen, Luggage, Multiple, Neck/Facewear, Office, Pet, Sleepwear, Small Accessories, Textiles, Underwear, Wallets

---

## R5.1 — Packaging Rule Validation

**What to check:**
1. If Item Type Category is "Packaging": Property and Art Ref # must be present
2. Neck Pillow items trigger a [REVIEW] flag
3. Retailer-specific packaging rules (Walmart hangtag, Spencer's bellyband)
4. If Licensing Status needs review: Property must be present

**Config file:** None — logic from Pre-check steps doc.

### Example 1: FAIL — Style `PKUB8TGDSC`

- Item Type Category = "Packaging", Customer = "Spencers Gifts"
- Spencer's triggers: **"Spencer's requires bellyband packaging"** [REVIEW]
- **R5.1 FAIL**

### Example 2: PASS — Style `TNUB9L5DSY`

- Item Type Category = "Small Accessories" (not Packaging)
- No neck pillow
- **R5.1 PASS**

---

## Summary: Expected Results for All 12 Gate-Passing Styles

| Style # | Property | Customer | R3.1 | R3.2 | R4.1 | R5.1 | Overall | Key Failure |
|---------|----------|----------|------|------|------|------|---------|-------------|
| EYG8VV5DSY | Disney Princess | Disney Stores | FAIL | PASS | FAIL | PASS | FAIL | [REVIEW] PMS colours; Eyeglass not in NLS |
| PKU9D6HDSC | Winnie The Pooh | Box Lunch | PASS | PASS | FAIL | PASS | FAIL | "Packaging" not licensed |
| VHU9L9MDSX | Up | Box Lunch | PASS | PASS | FAIL | PASS | FAIL | "Home Décor" not licensed |
| PKAABHGDSY | Disney Brand Name | Macys | FAIL | FAIL | FAIL | PASS | FAIL | Not in hierarchy; "Packaging" not licensed |
| BNFAJY5DSC | Disney Villains | General Dev | FAIL | FAIL | PASS | PASS | FAIL | Not in hierarchy |
| PKUB8TGDSC | Winnie The Pooh | Spencers | PASS | PASS | FAIL | FAIL | FAIL | "Packaging" not licensed; Spencer's bellyband |
| TNUB9L5DSY | Disney Princess | Box Lunch | FAIL | PASS | PASS | PASS | FAIL | [REVIEW] PMS colours |
| TNUB9L6DSY | Disney Princess | Box Lunch | FAIL | PASS | PASS | PASS | FAIL | [REVIEW] PMS colours |
| TNUB9LCDSY | Disney Princess | Box Lunch | FAIL | PASS | PASS | PASS | FAIL | [REVIEW] PMS colours |
| VHUBCCGDSC | Muppets | Box Lunch | PASS | PASS | FAIL | PASS | FAIL | "Home Décor" not licensed |
| LRYBGMQDSY | Disney Princess | Bioworld Inline | FAIL | PASS | PASS | PASS | FAIL | [REVIEW] PMS colours |
| MPGBJEGDSY | Disney Princess | Walmart | FAIL | PASS | PASS | PASS | FAIL | [REVIEW] PMS colours |

**Note:** R1.1, R1.2, R2.1, R2.2 all PASS for these 12 styles. The failures come from R3.1, R3.2, R4.1, and R5.1.

---

## Quick Checklist Per Style

For any style you want to manually verify:

- [ ] **R1.1**: Open `Styles 16 1.xlsx` → check 7 mandatory fields. Then open `DISNEY PROPERTIES 7.xlsx` Sheet1 → search for the Property name (exact match).
- [ ] **R1.2**: Note the Style # suffix (last 3 chars). Open `DISNEY PROPERTIES 7.xlsx` Sheet2 → if Pixar property must be DSX, if Disney must be DST/DSM/DSC/DCH/DSY.
- [ ] **R2.1**: Property has value → Art Ref # must also have value.
- [ ] **R2.2**: Open Hierarchy file → search all 3 sheets for exact Property name.
- [ ] **R3.1**: Same as R2.2 + check "DO NOT USE" column + check property-specific rules (NBC VHS, Tiana frog, Cruella, Princess PMS).
- [ ] **R3.2**: If found in hierarchy, note the sheet = franchise → PASS.
- [ ] **R4.1**: Open NLS "Definitions" sheet → Item Type Category must be a listed category → Item Type must be under that category (exact match). Check retailer restrictions for KDH/specialty properties.
- [ ] **R5.1**: If Packaging category → needs Property + Art Ref #. Check retailer-specific packaging rules. Check neck pillow luggage requirement.

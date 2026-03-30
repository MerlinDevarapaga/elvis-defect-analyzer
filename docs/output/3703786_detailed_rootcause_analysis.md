# 🔍 Defect Root Cause Analysis Report

> **Ticket ID**: `3703786`
> **Project**: `MSIL_DA2.8`
> **Report Generated**: `2026-03-30 13:00 UTC`

---

## 📋 Defect Summary

| Field | Value |
|-------|-------|
| **Title** | [HMI_VD_UX] [Software update]: In top bar "Settings > General > Software updates" is not matching and "Adjust brightness, contrast and Resolution easily" is not displayed as per Figma design |
| **Priority** | C(3) |
| **Internal Priority** | Not available |
| **State** | Entered |
| **Workflow Step** | Categorizing |
| **Owner** | AjU |
| **Occurrence** | Always |
| **Problem Type** | SW |
| **Milestone** | -- |
| **Test Environment** | Bench - Manual |
| **Test Stage** | SYS Qualification Test |

---

## 🧩 System & Component Information

| Field | Value |
|-------|-------|
| **System** | Software |
| **System SW Rev** | P5_B2-S_C3-A |
| **System HW Rev** | ED3 - 10inch |
| **Functional Group** | HMI IVI |
| **FG SW Rev** | P5_B2-S_C3-A |
| **Component** | Not specified |
| **Sub-Component** | Not specified |

---

## 📝 Problem Description

**TEST SETUP:** ED3 HW

**Devices used with version:**

**SW Details:**
- IOC version: FS_PIY25_04.5_DB25485A
- SOC Version: R7.0_Mainline_ Build # 166
- Build URL: https://artifactory-mb.harman.com/artifactory/MSIL_DA_2.8/MSIL/msil-u-mainline-r07.00/daily_build/msilda28_mainline_userdebug_unsigned_domestic_r07.00/userdebug/166/

**PRECONDITION:**
1. HU should be up and running

**REPRODUCTION STEPS/ACTION:**
1. Go to MSIL settings app
2. Click on General and Click on Software updates
3. Observe the HMI

**OBSERVED:** In top bar "Settings > General > Software updates" is not matching and "Adjust brightness, contrast and Resolution easily" is not displayed as per Figma design

**EXPECTED:** In top bar "Settings > General > Software updates" should be matching and "Adjust brightness, contrast and Resolution easily" should be displayed as per Figma design

**RECOVERY TRIED:** Not available

**Occurrence rate:** Always

**Requirement ID:** Not available

**Exploratory:** No

**ATTACHMENTS:** Added Figma image and current image in the attachments

**Additional Notes:** Added Figma image and current image in the attachments

**Figma link:** https://www.figma.com/design/Woim3iH2f9rt6preS09yxj/DA2.8_IVI_10.25inch_VD_Software_Update_CW22_30_05_2025?node-id=0-1&p=f&t=RfkwmN4MmFVGJo2V-0

---

## 📅 Defect Timeline

| Event | Date |
|-------|------|
| **Ticket Created** | 2025-12-07 |
| **First Response** | 2025-12-07 |
| **First Processing** | Not available |
| **First Integration** | Not available |
| **First Verification** | Not available |
| **First Conclusion** | Not available |
| **First Closed** | Not yet closed |
| **First Reopened** | N/A |
| **Last Closed** | Not yet closed |
| **Last Change** | 2026-03-28 18:56:20 |
| **Planned Fix Date** | Not available |

**Cycle Time Summary**:
- **Creation → First Response**: 0 days (same day)
- **Creation → First Processing**: Not available (ticket has not progressed to processing)
- **Creation → First Verification**: Not available (ticket has not reached verification)
- **Total Lifecycle (Creation → Last Change)**: ~112 days (2025-12-07 → 2026-03-28)

---

## 🔖 Version Tracking

| Field | Value |
|-------|-------|
| **Planned Fixed Version** | Not recorded |
| **Fixed In Version** | Not recorded |
| **Proceed Version** | Not recorded |
| **Integrate Version** | Not recorded |
| **Tested Version** | Not recorded |

---

## 🔬 Verification History

No verification attempts have been recorded for this defect. The ticket is still in the **Categorizing** step and has not yet progressed through the processing, integration, or verification workflow stages.

---

## 🎯 Root Cause Analysis

### Identified Root Cause

The defect is a **UI/UX visual design mismatch** in the HMI IVI Software Update settings screen. The implementation deviates from the approved Figma design specification in two specific ways:

1. **Breadcrumb/top bar mismatch**: The navigation path displayed as "Settings > General > Software updates" in the top bar does not conform to the visual design specification (text, styling, or hierarchy may differ from the Figma mock-up).
2. **Missing descriptive text**: The subtitle/helper text "Adjust brightness, contrast and Resolution easily" is not rendered on the Software Update screen, despite being specified in the Figma design.

The root cause is that the HMI screen layout and content for the Software Update page were not accurately translated from the Figma visual design into the implementation. This is likely due to:
- The screen using a generic or incorrect template that does not include the descriptive subtitle area.
- The breadcrumb text or formatting being hardcoded or auto-generated in a way that doesn't match the design spec.
- Possible oversight during the development of the Software Update settings page, where the developer may have referenced an outdated or incomplete Figma version.

> **Note**: The Cause, BugTaxonomy, and Measures fields in Elvis are empty — no formal root cause has been entered by the team yet, as the ticket is still in the Categorizing stage.

### Root Cause Category

**UI/UX Implementation Gap** — The HMI screen does not match the approved visual design specification (Figma). This falls under the category of a **Design-to-Implementation Fidelity** defect.

### Contributing Factors

- **No formal root cause analysis performed yet** — ticket is stalled in the Categorizing step since December 2025 (over 3 months).
- **Lack of Component/SubComponent assignment** — the Component and SubComponent fields are empty, indicating the defect has not been triaged to a specific code owner.
- **No planned fix version or date** — no version tracking information has been filled in, suggesting the defect is not yet scheduled for a fix.
- **Potential design specification ambiguity** — the described subtitle text ("Adjust brightness, contrast and Resolution easily") appears to be a generic display settings description that may not belong on the Software Update screen, suggesting possible Figma design error or misinterpretation.
- **HMI Handling required note** — the response note indicates HMI team action is needed but has not been taken.

---

## 🛡️ Potential Preventive Actions

| # | Preventive Action | Rationale |
|---|-------------------|-----------|
| 1 | **Implement automated Figma-to-HMI visual regression testing** — Use screenshot comparison tools (e.g., Percy, Applitools) to compare rendered HMI screens against Figma exports during CI/CD. | Catches visual design deviations before they reach system qualification, preventing breadcrumb and layout mismatches from escaping to test. |
| 2 | **Enforce mandatory design review checklist for HMI screens** — Before code merge, require a sign-off checklist verifying top bar, breadcrumbs, subtitles, and layout elements match the Figma spec. | Ensures developers and reviewers explicitly verify each UI element against the design, reducing implementation oversights. |
| 3 | **Centralize HMI string/text resources with Figma sync** — Maintain all display strings (breadcrumbs, subtitles) in a resource file that is synchronized with the Figma design tokens. | Prevents hardcoded or missing UI text by establishing a single source of truth for all display strings. |
| 4 | **Add per-screen UI specification traceability** — Link each HMI screen implementation to its specific Figma node/frame, and validate traceability during code reviews. | Enables any reviewer to quickly verify the implementation against the exact Figma design frame, catching deviations early. |
| 5 | **Establish SLA/escalation for tickets stuck in Categorizing** — Flag tickets that remain in Categorizing/Entered state for more than 2 weeks for escalation. | This ticket has been in Categorizing for over 3 months; an SLA policy would prevent such stagnation. |

---

## 🔧 Potential Corrective Actions

| # | Corrective Action | Type | Priority |
|---|-------------------|------|----------|
| 1 | **Update the Software Update HMI screen** to match the Figma design — fix the top bar breadcrumb text/styling and add the missing subtitle text "Adjust brightness, contrast and Resolution easily". | Immediate Fix | High |
| 2 | **Triage and assign the ticket** — move from Categorizing to Processing, assign a Component/SubComponent, and set a PlannedFixedVersion and target date. | Process Action | High |
| 3 | **Verify the Figma spec accuracy** — confirm with the UX team that the subtitle text "Adjust brightness, contrast and Resolution easily" is indeed intended for the Software Update screen (it reads more like a Display settings subtitle). | Design Validation | Medium |
| 4 | **Audit other HMI Settings screens** against their Figma specs to identify and fix any similar breadcrumb or subtitle mismatches proactively. | Broader Fix | Medium |
| 5 | **Fill in the Cause, BugTaxonomy, and Measures fields** in Elvis once the fix is implemented, to maintain complete defect tracking records. | Process Improvement | Low |

---

## 📊 Risk Assessment

| Dimension | Rating | Justification |
|-----------|--------|---------------|
| **Recurrence Likelihood** | High | No automated visual regression testing is in place. Without process changes, similar Figma-to-implementation mismatches will continue to occur across other HMI screens in the Settings app. |
| **Customer Impact** | Low | This is a cosmetic/UX fidelity issue — the Software Update functionality itself is not impaired. However, it reflects poorly on product quality and design consistency. |
| **Detection Difficulty** | Low | The defect is easily detectable through manual visual comparison with the Figma design. No complex test setup or edge-case triggering is required — it reproduces always. |

---

## 📎 References

- **Elvis Ticket**: 3703786
- **Related Tickets**: None referenced
- **Merge Request**: None referenced
- **Detected By**: Not available
- **Responsible Group**: 387
- **Figma Design**: https://www.figma.com/design/Woim3iH2f9rt6preS09yxj/DA2.8_IVI_10.25inch_VD_Software_Update_CW22_30_05_2025?node-id=0-1&p=f&t=RfkwmN4MmFVGJo2V-0
- **Build Artifact**: https://artifactory-mb.harman.com/artifactory/MSIL_DA_2.8/MSIL/msil-u-mainline-r07.00/daily_build/msilda28_mainline_userdebug_unsigned_domestic_r07.00/userdebug/166/

---

*This report was auto-generated by the Defect RCA Agent on 2026-03-30 13:00 UTC.*

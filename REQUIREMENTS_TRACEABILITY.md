# Requirements traceability

The final Challenge 6 brief establishes the four scoped paths and judging scenarios. Card A and Card C summaries offer supporting detail. The pasted project request adds the zero-cost requirement, expanded fixtures and operator features.

| Challenge requirement | Implementation | Verification |
| --- | --- | --- |
| One platform for four hosts | Versioned JSON workflow schema, generic processing and review endpoints, adapter-specific business output | Workflow version API test and browser builder test |
| A — exact time and site for a complete order | Raw and normalized values, literal evidence verification, column-ordered CSV/TMS preview | `test_complete_transport_and_exact_export` and local model evaluation |
| A — site contact missing | Required-field validation, editable draft, review, simulated send and reply | `test_mandatory_gaps_and_reply` and actual local-model smoke |
| A — bare appointment “8” | AM/PM validator, null normalized value, corrected after fictional reply | `test_mandatory_gaps_and_reply` and browser dispatcher test |
| A — review before transmission or export | Versioned draft review and snapshot approval, no external sending interface | Browser dispatcher test, stale draft and approval checks |
| A — contradictions, changes and duplicates | Preserve source evidence, block conflicts, manual handling of out-of-scope requests, message ID uniqueness | Conflict, unsupported and duplicate tests |
| B — answer flyer inquiry and clarify size | Synthetic price/format catalogue, conditional review path, same conversation tools | `test_printing_deterministic_price_and_reviewed_sheet` |
| B — owner checks design and order | Dimension and DPI validation, deterministic price calculation, owner role, XLSX | Printing test and XLSX reread |
| C — faithful party, property and mortgage facts | Per-page attachment quotes, separate registered and current lenders and balances | `test_mortgage_calculation_and_drafts` and model evaluation |
| C — working and two drafts | Decimal interest worksheet, illustrative DOCX templates, lawyer review and source package | Mortgage test and DOCX reread |
| D — low vision, practical one-page plan, staff edit | Candidate-stated needs, onboarding sections, unverified costs, staff edit and PDF export | Accommodation test, PDF parse and browser staff edit |
| D — missing employer provisions | Required employer field and explicit gap | Accommodation test and local model evaluation |
| Common — fictional data and no live actions | Seeded scenarios stored in SQLite, simulated messages, loopback endpoints, local exports | Fixture inventory, organisation isolation, upload and reset tests |
| Project — minimum 78 scenarios and fifth example | 78 card scenarios, 1 custom fixture and 15+ trucking conversations | Fixture inventory test and seeded scenario endpoint |
| Project — local model and offline demo | Cloud-disabled Ollama with explicit model health, constrained JSON, bounded retry, deterministic alternate mode | Timeout/malformed local response tests, actual model evaluation and browser network filtering |
| Project — local reference management | Scoped versioned PDF/DOCX/TXT/CSV/XLSX extraction and manual scan warning | Attachment restrictions and organisation isolation tests |

Host sandbox field lists, Grandieu order sheet and price list, FBW precedents and Enabled Talent's prep pack were unavailable. Corresponding exports and references are synthetic equivalents.

The PDF briefs supplied host and event requirements. The pasted request authorised local implementation, dependency installation, testing and Git commits. Event logistics in the briefs were used to shape the five-minute rehearsal.

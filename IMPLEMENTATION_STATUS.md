# Implementation status

The local application, workflow engine, model integration and all four challenge demonstrations are implemented. The SQLite seed contains 78 challenge scenarios and one configuration-only organisation. The app runs on loopback and startup, shutdown, reset, seed and evaluation scripts are present.

| Area | Status |
| --- | --- |
| Environment | Standalone Ollama 0.40.17, Qwen3 4B, Python and frontend dependencies installed on the Mac. |
| Shared engine | Scoped intake, message deduplication, attachment text, source-backed fields, deterministic validation, revisioned review, local exports and audit history. |
| Ontario Bulk | Complete, missing contact, ambiguous appointment, contradiction, duplicate and manual-handling cases. |
| Studio by Grandieu | Synthetic rates and real synthetic PNG art with measured dimensions and DPI. Owner review and XLSX export. |
| FBW Law | Fictional source specimens, registered and current lender distinctions, Decimal working and two illustrative drafts for lawyer review. |
| Enabled Talent | One-page workplace plan, missing-provision flag, staff edit and local PDF export. |
| Configuration | Versioned Workflow Builder and a running Harbour Repair example. |
| Verification | Backend and browser checks plus real Ollama extraction and offline smoke tests. See [test results](TEST_RESULTS.md). |

The host-specific supporting packs and sandbox mappings were unavailable. The demo uses synthetic references, price rules, print artwork, mortgage documents, illustrative legal drafts and provisional export mappings. Uploaded reference files provide scoped text context. Official production pricing, template mappings and sandbox connections remain dependent on the authorised host materials.

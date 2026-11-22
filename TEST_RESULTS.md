# Verification results

Run on November 21, 2026 on a MacBook Pro with Apple M5 Pro, 48 GB RAM, arm64 macOS 27.2, Python 3.14, Node 26, Ollama 0.40.17 and `qwen3:4b`.

| Check | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q` | 30 passed. API, fixture seed/reset, field validation, isolation, deduplication, attachments, draft approvals, record revisions and local exports. |
| `npm --prefix frontend run build` | TypeScript check and production bundle passed. |
| `npm --prefix frontend test` | 5 passed in installed Chrome. Dispatcher clarification and ZIP download, staff plan editing, new workflow creation and processing, mobile navigation, and actual printing artwork preview. |
| `.venv/bin/python -m scripts.smoke_local` | Actual Ollama inference and clarification generation for the Ontario Bulk missing-contact scenario through reply, approval and ZIP export. Model-backed outputs also prepared for printing, mortgage, accessibility and the fifth workflow. |
| Document checks | Read back the reviewed XLSX and illustrative DOCX in tests. Rendered and visually inspected the actual transport summary and one-page accessibility PDF. |
| Network isolation | App, model and browser tests ran under a loopback-only macOS sandbox profile. An external connection was denied by the OS with `EPERM`. |

## Actual model benchmark

`python -m scripts.evaluate_local` compared a sample of 14 fictional initial inputs, including all four hosts and a free-form trucking email, plus 8 reply calls. Expected values are independent of the model. Columns separate Ollama with quote verification from the production pipeline that also checks explicitly labelled source values.

| Metric | Model-only | Pipeline |
| --- | ---: | ---: |
| Initial field exact match | 150/152 (98.7%) | 150/152 (98.7%) |
| Critical initial field exact match | 78/79 (98.7%) | 78/79 (98.7%) |
| Missing detection precision | 6/8 (75.0%) | 6/8 (75.0%) |
| Missing detection recall | 6/6 (100%) | 6/6 (100%) |
| Ambiguity detection accuracy | 171/171 (100%) | 171/171 (100%) |
| Ambiguity detection recall | 2/2 (100%) | 2/2 (100%) |
| Conflict classification after reply sequences | 7/7 (100%) | 7/7 (100%) |
| Whole-record exact match, including expected gaps | 13/14 (92.9%) | 13/14 (92.9%) |

Across 22 Ollama calls, median wall time was 5.12 s, mean 4.57 s and range 0.70–7.11 s. The free-form trucking case missed service type and appointment required. Both omissions became blocking issues. The independent literal check recovered the missing site-contact reply in two labelled cases. The sample is small and mostly structured synthetic input. These results do not establish accuracy on real host traffic.

The audit uses actual model timings and excludes deterministic browser test data from model accuracy. Some dependency warnings appeared during Pytest and bundling without affecting the reported results.

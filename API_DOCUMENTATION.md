# Relay AI API

FastAPI serves [local endpoint index](http://127.0.0.1:8000/docs). The browser proxies `/api` through Vite on localhost. All data is JSON except uploads and downloads.

| Method and path | Use |
| --- | --- |
| GET `/api/health` | Get selected mode, installed local models and availability. |
| PUT `/api/settings` | Set `mode` and `model`. |
| GET, POST `/api/workflows` | List current configurations or save a new version. |
| GET `/api/workflows/{org}/versions` | Read saved versions. |
| GET `/api/scenarios` | List fictional scenarios and their request IDs. |
| POST `/api/scenarios/reset` | Restore seeded requests. |
| POST `/api/intake` | Submit organisation, channel, sender, subject, body and optional message/thread/reply IDs. |
| POST `/api/intake/eml` | Multipart `org` and `file`. |
| GET `/api/orgs/{org}/requests` | List scoped request summaries. |
| GET `/api/orgs/{org}/requests/{id}` | Get the conversation, evidence, validation state and review history. |
| GET `/api/orgs/{org}/metrics` | Get database-derived status, volume, timing and audit activity. |
| GET, POST `/api/orgs/{org}/references` | List or upload scoped references. Uploaded form fields are `file` and optional `kind`. |
| GET `/api/orgs/{org}/documents/{id}` | Download a scoped original. |

Operations appended to the request-detail path:

| Method and suffix | Use |
| --- | --- |
| POST `/read`, `/process`, `/validate` | Mark as read, process outstanding source chunks or revalidate. |
| PATCH `/fields/{key}` | Correct a field with `value`, `reason` and `revision`. |
| POST, PATCH `/draft` | Generate or edit a draft. Edits require `text`, `revision`, `draft_id` and `draft_version`. |
| POST `/draft/approve`, `/draft/send` | Review and simulate transmission. Supply the reviewer role and current record and draft version. |
| POST `/duplicate` | Replay a seeded duplicate message and confirm it is ignored. |
| POST `/reply` | Inject the next prerecorded reply when available. |
| POST, PATCH `/output` | Prepare the current output or edit the accommodation plan. |
| POST `/review` | Record `revision`, `role`, optional `comment`, and `approve`, `reject` or `return`. |
| POST `/export` | Return a ZIP and write approved files into the default export root or an existing absolute `directory`. |
| POST `/attachments` | Upload a multipart `file` to the request. |

A duplicate message ID returns the existing request and a duplicate flag. Stale revisions, conflicting thread association, unresolved review issues, and missing approvals return a conflict response. Local inference failures return HTTP 503 and keep the chosen mode.

# Carbon Guard admin dashboard (owner: Ameegha)

React 18 + Vite, plain JavaScript and CSS. It uses only the backend API in
[`../API_CONTRACT.md`](../API_CONTRACT.md). All HTTP calls are in `src/api.js`.

```bat
copy .env.example .env      (VITE_API_URL=http://127.0.0.1:8000)
npm install
npm run dev                 (http://localhost:5173)
npm test                    (unit tests)
npm run build               (production files in dist\)
```

| Page | File | API |
|---|---|---|
| Login (admins only) | `src/pages/Login.jsx` | `/auth/login`, `/auth/me` |
| Overview: stats, status/activity bars, impact report | `src/pages/Overview.jsx` | `/admin/stats`, `/admin/reports` |
| Review queue with filters, search, paging | `src/pages/Submissions.jsx` | `/admin/submissions` |
| Submission review: photo, map, AI, satellite, GPS, flags, related duplicates, approve/reject/manual review with confirmation and notes | `src/pages/SubmissionDetail.jsx` | `/admin/submissions/{id}` + actions |
| Users with search; user profile with trust and credit history, deactivate | `src/pages/Users.jsx`, `UserDetail.jsx` | `/admin/users`, `/admin/users/{id}` |
| Fraud and duplicate flags | `src/pages/FraudLogs.jsx` | `/admin/fraud-flags` |
| Green Credit rules | `src/pages/CreditRules.jsx` | `/admin/credit-rules` |
| Verification settings | `src/pages/Settings.jsx` | `/admin/config` |
| Audit log | `src/pages/AuditLog.jsx` | `/admin/audit-logs` |

Shared pieces: `src/components/` (status badge, loading/error with retry, empty state, pager, confirmation
dialog), `src/useLoad.js` (loading helper), `src/format.js` (labels, dates, numbers).

Testing status: unit tests (`src/api.test.js`) and an integration test against a live backend
(`src/integration.test.js`, see SETUP_GUIDE.md) pass. Every page still needs a **visual click-through** in a browser,
including a phone-width check. Record it in `../PROJECT_STATUS.md`.

# BRP Cyber Frontend

Objective Gate and Governance dashboard for enterprise orchestration readiness.

## Setup
1. Install dependencies
```bash
npm install
```
2. Configure environment
```bash
cp .env.example .env.local
```
3. Run dev server
```bash
npm run dev
```

## Environment
- `NEXT_PUBLIC_API_BASE_URL`: backend base URL
- `NEXT_PUBLIC_CONTROL_PLANE_BEARER`: control-plane Bearer token (`control_plane:read`) for governance panel

## Required API Endpoints
- `GET /enterprise/objective-gate-dashboard`
- `GET /enterprise/objective-gate/{tenant_id}`
- `GET /enterprise/objective-gate-history/{tenant_id}`
- `GET /enterprise/objective-gate-remediation/{tenant_id}`
- `GET /control-plane/governance/dashboard`

Frontend reads backend URL/token from `NEXT_PUBLIC_*` env vars.

# ADR-0001: Platform Baseline for BRP-Cyber

- Date: 2026-03-06
- Status: Accepted

## Context
ต้องมี baseline ที่รองรับ Red/Blue/Purple orchestration, multi-tenant isolation, และต้นทุนเริ่มต้นต่ำสำหรับการทดสอบ feasibility.

## Decision
1. ใช้ FastAPI เป็น backend control/data API
2. ใช้ PostgreSQL (TimescaleDB) สำหรับ tenant + security events time-series
3. ใช้ Redis เป็น cache/state และรองรับการขยายเป็น stream broker ระยะถัดไป
4. ใช้ LangGraph ใน orchestration phase
5. เริ่มด้วย Docker Compose local/staging และย้ายไป Kubernetes เมื่อ scale
6. ใช้ Red mode แบบ simulation/emulation ที่ได้รับอนุญาตเท่านั้น

## Consequences
- ได้ระบบเริ่มต้นที่ deploy ง่ายและต้นทุนต่ำ
- ต้องเสริม queue durability (Kafka) เมื่อผ่าน MVP phase กลาง
- ต้องเพิ่ม policy governance และ audit controls ต่อเนื่องก่อน production

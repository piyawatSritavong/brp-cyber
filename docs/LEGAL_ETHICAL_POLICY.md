# BRP-Cyber Legal & Ethical Operating Policy (MVP)

## Purpose
กำหนดข้อบังคับขั้นต่ำเพื่อให้ระบบ Red/Blue/Purple ดำเนินการอย่างถูกต้องตามกฎหมายและปลอดภัยต่อผู้ใช้

## Mandatory Rules
1. Red Team mode ใช้เฉพาะ `authorized simulation/emulation` ภายในขอบเขตลูกค้าที่อนุญาต
2. ห้ามใช้ระบบไปโจมตีทรัพยากรที่ไม่อยู่ใน allowlist
3. ทุก automation action ต้อง log พร้อม `tenant_id`, `correlation_id`, `trace_id`, `reason_code`
4. Auto-block ต้องตรวจ allowlist ก่อนเสมอ
5. ต้องมี kill-switch ระดับระบบเพื่อหยุด action อัตโนมัติทันที
6. ข้อมูลข้าม tenant ถูกห้ามโดยเด็ดขาด (no cross-tenant data access)

## Responsibility
- ลูกค้าต้องยืนยันขอบเขตการทดสอบเป็นลายลักษณ์อักษร
- ผู้ให้บริการต้องมี audit log, retention policy, incident response process

## Enforcement
หากพบการละเมิด policy ระบบต้องบันทึกเหตุการณ์และระงับ automation ที่เกี่ยวข้องทันที

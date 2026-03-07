# External Audit Publication Runbook

## Objective
จัดการเหตุขัดข้องระหว่างเผยแพร่ external audit pack ไป immutable target

## Common Failure Cases
1. `blocked_invalid_pack`
- ความหมาย: pack verify ไม่ผ่านและ policy บังคับห้าม publish
- แก้: รัน `verify_external_audit_pack.py` กับ manifest, แก้ไฟล์ที่ hash mismatch, generate pack ใหม่

2. `audit_pack_publication_s3_bucket_not_configured`
- ความหมาย: โหมด `s3` แต่ bucket ยังไม่ตั้งค่า
- แก้: ตั้งค่า `CONTROL_PLANE_AUDIT_PACK_PUBLICATION_S3_BUCKET` และ credentials

3. `Object Lock` / retention errors
- ความหมาย: bucket policy หรือ object lock ไม่รองรับ
- แก้: ตรวจ bucket versioning + object lock config + IAM permissions (`s3:PutObjectRetention`)

## Recovery Steps
1. ตรวจ status ล่าสุด
```bash
python scripts/external_audit_publication_status.py --limit 20
```
2. รันแบบ dry-run เพื่อตรวจ metadata ก่อน
```bash
python scripts/publish_external_audit_pack.py --dry-run
```
3. เมื่อผ่านค่อย publish จริง
```bash
python scripts/publish_external_audit_pack.py
```
4. เก็บหลักฐาน publication object และ metadata object เข้ารายงานประจำสัปดาห์

## Operational Guardrail
- เปิด `CONTROL_PLANE_AUDIT_PACK_PUBLICATION_REQUIRE_VALID_PACK=true` ใน production
- ใช้ object lock สำหรับ target S3 เสมอเมื่อเป็นเส้นทาง evidence หลัก

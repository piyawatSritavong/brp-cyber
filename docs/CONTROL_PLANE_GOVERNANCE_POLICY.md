# Control Plane Governance Policy

## Objective
บังคับใช้นโยบาย action เสี่ยงใน control-plane แบบ policy-as-code และติดตามผลผ่าน governance dashboard

## Policy Mode
- `CONTROL_PLANE_POLICY_MODE=permissive`:
  - อนุญาต action แต่บันทึก policy warning
- `CONTROL_PLANE_POLICY_MODE=enforce`:
  - ปฏิเสธ action ที่ละเมิด rule (`policy_denied`)

## Current Rules
1. `tenant_status_update`
- ถ้า `bypass_objective_gate=true` ต้องมี scope `control_plane:override`
- ถ้า override ต้องมี `change_ticket` เมื่อ policy บังคับ
- ถ้า promote เป็น `production` ต้องมี `change_ticket` เมื่อ policy บังคับ

2. `tenant_rotate_key`
- ต้องมี `reason` ที่มีความหมายเมื่อ policy บังคับ

## Governance Observability
- `GET /control-plane/governance/policy`
- `GET /control-plane/governance/dashboard?limit=`
- `POST /control-plane/governance/attest?limit=`
- `GET /control-plane/governance/attestation-status?limit=`
- `GET /control-plane/governance/attestation-verify?limit=`
- `POST /control-plane/governance/attestation-export?destination_dir=`

Dashboard จะสรุป:
- policy warnings / denies
- override actions
- production promotions
- risky actors (risk score ตามพฤติกรรม)

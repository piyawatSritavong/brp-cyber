# Load Test Harness (Phase 5)

จุดประสงค์: วัด throughput, failure rate, SLO snapshot และ cost per 10k events ต่อ tenant

## Run
```bash
cd backend
python3 scripts/loadtest_enterprise.py \
  --base-url http://localhost:8000 \
  --tenant-id 11111111-1111-1111-1111-111111111111 \
  --requests 10000
```

## Output
- `requests`, `failures`, `duration_seconds`, `rps`
- `estimated_cost_per_10k_events_usd`
- `slo_snapshot` จาก `/enterprise/slo/{tenant_id}`

## Notes
- Cost value เป็น baseline estimate จาก token meter ที่กำหนดใน config
- สำหรับ production benchmark ควรยิงพร้อมกันหลาย tenant และหลาย worker instance

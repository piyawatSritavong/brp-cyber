# Kubernetes Profile (Phase 5+)

ไฟล์นี้เป็น baseline deployment สำหรับ production-like multi-node profile

## Apply Order
```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f worker-deployment.yaml
kubectl apply -f worker-hpa.yaml
kubectl apply -f worker-keda-scaledobject.yaml
kubectl apply -f autoscaler-reconcile-cronjob.yaml
```

## Notes
- ใช้ HPA (CPU) เป็น fallback
- ใช้ KEDA (Redis Streams lag) สำหรับ queue-driven scaling
- CronJob เรียก API autoscaler reconcile loop ทุก 1 นาที

## Validation
```bash
PYTHONPATH=backend python backend/scripts/validate_k8s_autoscaling_profile.py
PYTHONPATH=backend python backend/scripts/loadtest_matrix.py --environment prod-like --reconcile-autoscaler
```

- คำสั่งแรกไว้ตรวจ wiring ของ Deployment/HPA/ScaledObject/CronJob บน cluster ที่ deploy แล้ว
- คำสั่งที่สองไว้เก็บ benchmark evidence แบบ multi-tenant concurrent พร้อม markdown/json sidecar

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

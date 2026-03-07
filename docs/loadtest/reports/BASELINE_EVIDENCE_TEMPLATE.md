# Load Test Evidence Report (Template)

- Date: `<YYYY-MM-DD>`
- Environment: `<local/staging/prod-like>`
- API Version/Commit: `<sha>`

## Traffic Tiers
| Tier | Requests | Workers | Notes |
|---|---:|---:|---|
| T1 | 10,000 | 4 | baseline |
| T2 | 50,000 | 12 | sustained |
| T3 | 100,000 | 24 | stress |

## Results
| Tier | Throughput (RPS) | Failure Rate | Avg Latency (s) | Cost/10k Events (USD) | Availability |
|---|---:|---:|---:|---:|---:|
| T1 | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` |
| T2 | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` |
| T3 | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` |

## Queue + Autoscaling
- Queue total lag peak: `<value>`
- Desired workers peak: `<value>`
- Scale actions count: `<value>`
- Cooldown suppressions: `<value>`

## Observations
1. `<observation>`
2. `<observation>`

## Action Items
1. `<improvement action>`
2. `<improvement action>`

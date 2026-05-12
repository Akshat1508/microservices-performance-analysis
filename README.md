# Microservices Performance Analysis 📊

A hands-on distributed systems benchmarking project that evaluates how a production-grade Kubernetes microservices deployment behaves under load — measuring CPU, memory, and network performance across single-node and multi-node cloud architectures.

---

## 🧭 Project Overview

This project progressively scales a microservices workload from a **single Azure VM** to a **multi-node Kubernetes cluster**, benchmarking performance at each stage using real observability tooling. The goal is to quantify the gains from horizontal scaling under controlled, reproducible load conditions.

**Load Levels Tested:** Low (10 users) · Medium (50 users) · High (200 users)

---

## 🏗️ Architecture

### Phase 1 — Single-Node Deployment (Azure)
- Single Ubuntu VM acting as both Kubernetes control plane and worker node
- All 11 microservices scheduled on one machine
- Baseline metrics captured; cross-node network traffic = 0 (all intra-host)
- CPU spikes significantly under high load with no headroom

### Phase 2 — Multi-Node Deployment (Azure)
- Second Azure VM (`worker-node-1`) joined to the cluster via K3s agent
- Kubernetes Scheduler redistributed pods across both nodes automatically
- CPU pressure on primary node dropped significantly
- Inter-node network traffic (private VNet) confirmed via Grafana node exporter

---

## 🛠️ Tech Stack

| Tool | Role |
|------|------|
| **K3s** | Lightweight, production-grade Kubernetes distribution |
| **Helm** | Kubernetes package manager for deploying third-party charts |
| **Google Boutique Demo** | 11-microservice app in Go, Python, C#, Node.js over gRPC |
| **Prometheus** | Time-series metrics scraping (CPU, memory, network) |
| **Grafana** | Dashboard visualization connected to Prometheus |
| **Locust** | Python-based distributed load testing tool |

---

## 📁 Repository Structure

```
microservices-performance-analysis/
├── README.md
├── locustfile.py                        # Load test script defining HTTP user behavior
├── locust-reports/
│   ├── Locust_Single_Node_Low_Load.html
│   ├── Locust_Single_Node_Medium_Load.html
│   ├── Locust_Single_Node_High_Load.html
│   ├── Locust_Multi_Node_Low_Load.html
│   ├── Locust_Multi_Node_Medium_Load.html
│   └── Locust_Multi_Node_High_Load.html
└── images/
    └── benchmarks/
        ├── single-low-cpu.png
        ├── single-low-cpu-quota.png
        ├── single-low-memory.png
        ├── single-low-memory-quota.png
        ├── single-low-network.png
        ├── single-low-dashboard.png
        ├── single-medium-cpu.png
        ├── single-medium-cpu-quota.png
        ├── single-medium-memory.png
        ├── single-medium-memory-quota.png
        ├── single-medium-network.png
        ├── single-medium-dashboard.png
        ├── single-high-cpu.png
        ├── single-high-cpu-quota.png
        ├── single-high-memory.png
        ├── single-high-memory-quota.png
        ├── single-high-network.png
        ├── single-high-dashboard.png
        ├── multi-low-cpu.png
        ├── multi-low-cpu-quota.png
        ├── multi-low-memory.png
        ├── multi-low-memory-quota.png
        ├── multi-low-network.png
        ├── multi-low-dashboard.png
        ├── multi-medium-cpu.png
        ├── multi-medium-cpu-quota.png
        ├── multi-medium-memory.png
        ├── multi-medium-memory-quota.png
        ├── multi-medium-network.png
        ├── multi-medium-dashboard.png
        ├── multi-high-cpu.png
        ├── multi-high-cpu-quota.png
        ├── multi-high-memory.png
        ├── multi-high-memory-quota.png
        ├── multi-high-network.png
        └── multi-high-dashboard.png
```

---

## 🚀 Setup & Reproduction

> **Prerequisites:** Azure account with VM creation permissions · Windows machine with PowerShell · SSH key downloaded from Azure

### Step 1 — SSH into Your Azure VM (Windows PowerShell)

Windows OpenSSH strictly requires private key files to be protected from group access. Run PowerShell **as Administrator**:

```powershell
# Define path to your downloaded Azure key
$KeyPath = "$env:USERPROFILE\Downloads\azure-key.pem"

# Strip all inherited folder permissions
icacls $KeyPath /inheritance:r

# Grant read-only access to your current Windows user only
icacls $KeyPath /grant:r "$($env:USERNAME):R"

# Connect to your primary VM
ssh -i $KeyPath azureuser@<MANAGER_PUBLIC_IP>
```

### Step 2 — Install K3s (on the Azure VM)

```bash
# Install K3s control plane
curl -sfL https://get.k3s.io | sh -

# Verify cluster is up
sudo k3s kubectl get nodes
```

### Step 3 — Deploy the Boutique App (11 Microservices)

```bash
# Apply all deployment and service manifests
sudo k3s kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/microservices-demo/main/release/kubernetes-manifests.yaml

# Watch pods until all show "Running"
sudo k3s kubectl get pods -o wide --watch
```

### Step 4 — Install Helm & Deploy the Observability Stack

```bash
# Install Helm
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh

# Add Prometheus community repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Create monitoring namespace and deploy the full stack
sudo k3s kubectl create namespace monitoring
sudo k3s helm install observability prometheus-community/kube-prometheus-stack --namespace monitoring
```

**Retrieve the Grafana admin password:**
```bash
sudo k3s kubectl get secret --namespace monitoring observability-grafana \
  -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
```
> Username defaults to `admin`

### Step 5 — Expose Services & Tunnel Locally

**On the Azure VM** — forward both services to all interfaces (run in background):
```bash
sudo k3s kubectl port-forward svc/frontend 8080:80 --address 0.0.0.0 &
sudo k3s kubectl port-forward svc/observability-grafana 3000:80 -n monitoring --address 0.0.0.0 &
```

**On your local Windows machine** — open a new PowerShell window and create the SSH tunnel:
```powershell
ssh -i "$env:USERPROFILE\Downloads\azure-key.pem" `
    -L 8080:localhost:8080 `
    -L 3000:localhost:3000 `
    -L 8089:localhost:8089 `
    azureuser@<MANAGER_PUBLIC_IP>
```

| Service | Local URL |
|---------|-----------|
| Frontend UI | http://localhost:8080 |
| Grafana | http://localhost:3000 |
| Locust UI | http://localhost:8089 |

### Step 6 — Install Locust & Run Load Tests

```bash
sudo apt-get install -y python3-pip
pip3 install locust

# Start the Locust web UI (access at http://localhost:8089)
locust -f locustfile.py
```

**Or run headless directly from CLI:**

```bash
# Low Load — 10 users, 2/sec ramp-up, 3 minutes
locust -f locustfile.py --headless -u 10 -r 2 --run-time 3m \
  --host=http://localhost:8080 --csv=benchmark_low_load

# Medium Load — 50 users, 5/sec ramp-up, 3 minutes
locust -f locustfile.py --headless -u 50 -r 5 --run-time 3m \
  --host=http://localhost:8080 --csv=benchmark_medium_load

# High Load — 200 users, 10/sec ramp-up, 3 minutes
locust -f locustfile.py --headless -u 200 -r 10 --run-time 3m \
  --host=http://localhost:8080 --csv=benchmark_high_stress
```

---

## 📈 Scaling to Multi-Node (Phase 2)

### Step 1 — Get the Cluster Join Token (on manager VM)

```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```

### Step 2 — Join the Worker Node (on worker-node-1)

```bash
curl -sfL https://get.k3s.io | \
  K3S_URL=https://<MANAGER_PRIVATE_IP>:6443 \
  K3S_TOKEN=<COPIED_NODE_TOKEN> sh -
```

### Step 3 — Force Pod Redistribution (back on manager)

```bash
# Verify both nodes show "Ready"
sudo k3s kubectl get nodes

# Delete all pods to trigger automatic rescheduling across both nodes
sudo k3s kubectl delete pods --all

# Confirm pods are now spread across both VMs
sudo k3s kubectl get pods -o wide
```

---

## 📊 Benchmark Results

### Phase 1: Single-Node

#### Low Load (10 Users)
| Metric | Screenshot |
|--------|-----------|
| CPU Usage | ![](images/benchmarks/single-low-cpu.png) |
| CPU Quota | ![](images/benchmarks/single-low-cpu-quota.png) |
| Memory Usage | ![](images/benchmarks/single-low-memory.png) |
| Memory Quota | ![](images/benchmarks/single-low-memory-quota.png) |
| Network I/O | ![](images/benchmarks/single-low-network.png) |
| Locust Dashboard | ![](images/benchmarks/single-low-dashboard.png) |

#### Medium Load (50 Users)
| Metric | Screenshot |
|--------|-----------|
| CPU Usage | ![](images/benchmarks/single-medium-cpu.png) |
| CPU Quota | ![](images/benchmarks/single-medium-cpu-quota.png) |
| Memory Usage | ![](images/benchmarks/single-medium-memory.png) |
| Memory Quota | ![](images/benchmarks/single-medium-memory-quota.png) |
| Network I/O | ![](images/benchmarks/single-medium-network.png) |
| Locust Dashboard | ![](images/benchmarks/single-medium-dashboard.png) |

#### High Load (200 Users)
| Metric | Screenshot |
|--------|-----------|
| CPU Usage | ![](images/benchmarks/single-high-cpu.png) |
| CPU Quota | ![](images/benchmarks/single-high-cpu-quota.png) |
| Memory Usage | ![](images/benchmarks/single-high-memory.png) |
| Memory Quota | ![](images/benchmarks/single-high-memory-quota.png) |
| Network I/O | ![](images/benchmarks/single-high-network.png) |
| Locust Dashboard | ![](images/benchmarks/single-high-dashboard.png) |

---

### Phase 2: Multi-Node

#### Low Load (10 Users)
| Metric | Screenshot |
|--------|-----------|
| CPU Usage | ![](images/benchmarks/multi-low-cpu.png) |
| CPU Quota | ![](images/benchmarks/multi-low-cpu-quota.png) |
| Memory Usage | ![](images/benchmarks/multi-low-memory.png) |
| Memory Quota | ![](images/benchmarks/multi-low-memory-quota.png) |
| Network I/O | ![](images/benchmarks/multi-low-network.png) |
| Locust Dashboard | ![](images/benchmarks/multi-low-dashboard.png) |

#### Medium Load (50 Users)
| Metric | Screenshot |
|--------|-----------|
| CPU Usage | ![](images/benchmarks/multi-medium-cpu.png) |
| CPU Quota | ![](images/benchmarks/multi-medium-cpu-quota.png) |
| Memory Usage | ![](images/benchmarks/multi-medium-memory.png) |
| Memory Quota | ![](images/benchmarks/multi-medium-memory-quota.png) |
| Network I/O | ![](images/benchmarks/multi-medium-network.png) |
| Locust Dashboard | ![](images/benchmarks/multi-medium-dashboard.png) |

#### High Load (200 Users)
| Metric | Screenshot |
|--------|-----------|
| CPU Usage | ![](images/benchmarks/multi-high-cpu.png) |
| CPU Quota | ![](images/benchmarks/multi-high-cpu-quota.png) |
| Memory Usage | ![](images/benchmarks/multi-high-memory.png) |
| Memory Quota | ![](images/benchmarks/multi-high-memory-quota.png) |
| Network I/O | ![](images/benchmarks/multi-high-network.png) |
| Locust Dashboard | ![](images/benchmarks/multi-high-dashboard.png) |

---

## 📄 Locust Reports

Full HTML reports (with request stats, response times, failures, and charts) are available in the [`locust-reports/`](locust-reports/) folder.

| Phase | Load | Report |
|-------|------|--------|
| Single-Node | Low (10 users) | [Locust_Single_Node_Low_Load.html](locust-reports/Locust_Single_Node_Low_Load.html) |
| Single-Node | Medium (50 users) | [Locust_Single_Node_Medium_Load.html](locust-reports/Locust_Single_Node_Medium_Load.html) |
| Single-Node | High (200 users) | [Locust_Single_Node_High_Load.html](locust-reports/Locust_Single_Node_High_Load.html) |
| Multi-Node | Low (10 users) | [Locust_Multi_Node_Low_Load.html](locust-reports/Locust_Multi_Node_Low_Load.html) |
| Multi-Node | Medium (50 users) | [Locust_Multi_Node_Medium_Load.html](locust-reports/Locust_Multi_Node_Medium_Load.html) |
| Multi-Node | High (200 users) | [Locust_Multi_Node_High_Load.html](locust-reports/Locust_Multi_Node_High_Load.html) |

> **Note:** GitHub doesn't render HTML files inline — download and open them in a browser for the full interactive report.

---

## 🔑 Key Findings

- **Horizontal scaling works**: Adding a second node significantly reduced CPU pressure on the primary node under identical load
- **Network traffic is proof**: Grafana confirmed high inter-node packet transfer between the two VMs' private IPs, validating real cross-server pod communication
- **K3s is production-ready**: The lightweight distribution handled full workload scheduling and pod redistribution without any manual intervention
- **Observability is essential**: Without Prometheus + Grafana, the CPU reduction after scaling would be invisible — the dashboards made the impact quantifiable

---

## 🔧 Troubleshooting

**Port already in use after reconnecting:**
```bash
sudo fuser -k 8080/tcp
sudo fuser -k 3000/tcp
```

**Deallocating VMs to stop billing:**
Azure Portal → Virtual Machines → select instance → **Stop** → confirm state shows `Stopped (deallocated)`

---

## 🗺️ Roadmap

- [x] Phase 1: Single-node Azure deployment
- [x] Phase 2: Multi-node Azure cluster
- [ ] Phase 3: Multi-cloud deployment (Azure + GCP/AWS)
- [ ] Phase 4: Edge topology benchmarking

---

## 🧰 References

- [K3s Documentation](https://docs.k3s.io/)
- [Helm](https://helm.sh/)
- [Google Cloud Boutique Demo](https://github.com/GoogleCloudPlatform/microservices-demo)
- [Kube-Prometheus-Stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [Locust](https://locust.io/)

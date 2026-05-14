# Microservices Performance Analysis 📊

A hands-on distributed systems benchmarking project that evaluates how a production-grade Kubernetes microservices deployment behaves under load — measuring CPU, memory, and network performance across single-node, multi-node, and multi-cloud architectures.

---

## 🧭 Project Overview

This project progressively scales a microservices workload from a **single Azure VM** to a **multi-node Kubernetes cluster**, and finally to a **multi-cloud topology spanning Azure and GCP**, benchmarking performance at each stage using real observability tooling. The goal is to quantify the gains from horizontal and geographic scaling under controlled, reproducible load conditions.

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

### Phase 3 — Multi-Cloud Deployment (Azure + GCP)
- K3s cluster spanned across two cloud providers over public WAN
- Manager node on Azure; edge/worker node on Google Cloud Platform (GCP)
- Cross-cloud pod communication tunneled via Flannel VXLAN overlay network
- Frontend pinned to GCP node via Kubernetes NodeSelector to simulate edge serving

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
| **Azure** | Primary cloud — manager node host |
| **GCP** | Secondary cloud — worker/edge node host |

---

## 📁 Repository Structure

```
microservices-performance-analysis/
├── README.md
├── locustfile.py
├── locust-reports/
│   ├── Locust_Single_Node_Low_Load.html
│   ├── Locust_Single_Node_Medium_Load.html
│   ├── Locust_Single_Node_High_Load.html
│   ├── Locust_Multi_Node_Low_Load.html
│   ├── Locust_Multi_Node_Medium_Load.html
│   ├── Locust_Multi_Node_High_Load.html
│   ├── Locust_Multi_Cloud_Low_Load.html
│   ├── Locust_Multi_Cloud_Medium_Load.html
│   └── Locust_Multi_Cloud_High_Load.html
└── images/
    └── benchmarks/
        ├── single-low-*.png          (6 files)
        ├── single-medium-*.png       (6 files)
        ├── single-high-*.png         (6 files)
        ├── multi-low-*.png           (6 files)
        ├── multi-medium-*.png        (6 files)
        ├── multi-high-*.png          (6 files)
        ├── Multicloud-Low-*.png      (5 files)
        ├── Multicloud-Medium-*.png   (5 files)
        └── Multicloud-High-*.png     (5 files)
```

---

## 🚀 Setup & Reproduction

> **Prerequisites:** Azure + GCP accounts · Windows machine with PowerShell · SSH keys for each cloud

### Step 1 — SSH into Your Azure VM (Windows PowerShell)

Windows OpenSSH strictly requires private key files to be protected from group access. Run PowerShell **as Administrator**:

```powershell
$KeyPath = "$env:USERPROFILE\Downloads\azure-key.pem"
icacls $KeyPath /inheritance:r
icacls $KeyPath /grant:r "$($env:USERNAME):R"
ssh -i $KeyPath azureuser@<MANAGER_PUBLIC_IP>
```

### Step 2 — Install K3s (on the Azure VM)

```bash
curl -sfL https://get.k3s.io | sh -
sudo k3s kubectl get nodes
```

### Step 3 — Deploy the Boutique App (11 Microservices)

```bash
sudo k3s kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/microservices-demo/main/release/kubernetes-manifests.yaml
sudo k3s kubectl get pods -o wide --watch
```

### Step 4 — Install Helm & Deploy the Observability Stack

```bash
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
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

**On the Azure VM:**
```bash
sudo k3s kubectl port-forward svc/frontend 8080:80 --address 0.0.0.0 &
sudo k3s kubectl port-forward svc/observability-grafana 3000:80 -n monitoring --address 0.0.0.0 &
```

**On your local Windows machine:**
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

### Step 6 — Run Load Tests

```bash
sudo apt-get install -y python3-pip
pip3 install locust
locust -f locustfile.py
```

**Headless CLI:**
```bash
locust -f locustfile.py --headless -u 10 -r 2 --run-time 3m --host=http://localhost:8080 --csv=benchmark_low_load
locust -f locustfile.py --headless -u 50 -r 5 --run-time 3m --host=http://localhost:8080 --csv=benchmark_medium_load
locust -f locustfile.py --headless -u 200 -r 10 --run-time 3m --host=http://localhost:8080 --csv=benchmark_high_stress
```

---

## 📈 Scaling to Multi-Node (Phase 2)

```bash
# On manager — get join token
sudo cat /var/lib/rancher/k3s/server/node-token

# On worker-node-1 — join the cluster
curl -sfL https://get.k3s.io | \
  K3S_URL=https://<MANAGER_PRIVATE_IP>:6443 \
  K3S_TOKEN=<COPIED_NODE_TOKEN> sh -

# On manager — force rescheduling
sudo k3s kubectl get nodes
sudo k3s kubectl delete pods --all
sudo k3s kubectl get pods -o wide
```

---

## ☁️ Multi-Cloud Setup (Phase 3 — Azure + GCP)

### Firewall Ports to Open (on both clouds)

| Port | Protocol | Purpose |
|------|----------|---------|
| 6443 | TCP | K3s API Server |
| 10250 | TCP | Kubelet metrics |
| 8472 | UDP | Flannel VXLAN overlay (cross-cloud pod networking) |

### Join GCP Node to Azure Cluster

SSH into the GCP VM and run:
```bash
curl -sfL https://get.k3s.io | \
  K3S_URL=https://<AZURE_MANAGER_PUBLIC_IP>:6443 \
  K3S_TOKEN=<COPIED_NODE_TOKEN> sh -s - \
  --node-external-ip=<GCP_VM_PUBLIC_IP>
```

### Pin Frontend to GCP (Edge Serving)

Run on the Azure manager:
```bash
# Label the GCP node as edge
sudo k3s kubectl label nodes <GCP_NODE_NAME> node-role.kubernetes.io/edge=true

# Pin frontend deployment to the edge node
sudo k3s kubectl patch deployment frontend -p \
  '{"spec": {"template": {"spec": {"nodeSelector": {"node-role.kubernetes.io/edge": "true"}}}}}'

# Confirm frontend pods migrated to GCP node
sudo k3s kubectl get pods -o wide
```

---

## 📊 Benchmark Results

### Phase 1: Single-Node (Azure)

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

### Phase 2: Multi-Node (Azure)

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

### Phase 3: Multi-Cloud (Azure + GCP)

#### Low Load (10 Users)
| Metric | Screenshot |
|--------|-----------|
| CPU Usage | ![](images/benchmarks/Multicloud-Low-CPU.png) |
| CPU Quota | ![](images/benchmarks/Multicloud-Low-CPU-Quota.png) |
| Memory Usage | ![](images/benchmarks/Multicloud-Low-Memory.png) |
| Memory Quota | ![](images/benchmarks/Multicloud-Low-Memory-Quota.png) |
| Network I/O | ![](images/benchmarks/Multicloud-Low-Network.png) |
| Locust Dashboard | ![](images/benchmarks/Multicloud-Low-Dashboard.png) |

#### Medium Load (50 Users)
| Metric | Screenshot |
|--------|-----------|
| CPU Usage | ![](images/benchmarks/Multicloud-Medium-CPU.png) |
| CPU Quota | ![](images/benchmarks/Multicloud-Medium-CPU-Quota.png) |
| Memory Usage | ![](images/benchmarks/Multicloud-Medium-Memory.png) |
| Memory Quota | ![](images/benchmarks/Multicloud-Medium-Memory-Quota.png) |
| Network I/O | ![](images/benchmarks/Multicloud-Medium-Network.png) |
| Locust Dashboard | ![](images/benchmarks/Multicloud-Medium-Dashboard.png) |

#### High Load (200 Users)
| Metric | Screenshot |
|--------|-----------|
| CPU Usage | ![](images/benchmarks/Multicloud-High-CPU.png) |
| CPU Quota | ![](images/benchmarks/Multicloud-High-CPU-Quota.png) |
| Memory Usage | ![](images/benchmarks/Multicloud-High-Memory.png) |
| Memory Quota | ![](images/benchmarks/Multicloud-High-Memory-Quota.png) |
| Network I/O | ![](images/benchmarks/Multicloud-High-Network.png) |
| Locust Dashboard | ![](images/benchmarks/Multicloud-High-Dashboard.png) |

---

## 📄 Locust Reports

Full HTML reports are available in the [`locust-reports/`](locust-reports/) folder.

| Phase | Load | Report |
|-------|------|--------|
| Single-Node | Low | [Locust_Single_Node_Low_Load.html](locust-reports/Locust_Single_Node_Low_Load.html) |
| Single-Node | Medium | [Locust_Single_Node_Medium_Load.html](locust-reports/Locust_Single_Node_Medium_Load.html) |
| Single-Node | High | [Locust_Single_Node_High_Load.html](locust-reports/Locust_Single_Node_High_Load.html) |
| Multi-Node | Low | [Locust_Multi_Node_Low_Load.html](locust-reports/Locust_Multi_Node_Low_Load.html) |
| Multi-Node | Medium | [Locust_Multi_Node_Medium_Load.html](locust-reports/Locust_Multi_Node_Medium_Load.html) |
| Multi-Node | High | [Locust_Multi_Node_High_Load.html](locust-reports/Locust_Multi_Node_High_Load.html) |
| Multi-Cloud | Low | [Locust_Multi_Cloud_Low_Load.html](locust-reports/Locust_Multi_Cloud_Low_Load.html) |
| Multi-Cloud | Medium | [Locust_Multi_Cloud_Medium_Load.html](locust-reports/Locust_Multi_Cloud_Medium_Load.html) |
| Multi-Cloud | High | [Locust_Multi_Cloud_High_Load.html](locust-reports/Locust_Multi_Cloud_High_Load.html) |

> **Note:** GitHub doesn't render HTML files inline — download and open in a browser for the full interactive report.

---

## 🔑 Key Findings

- **Horizontal scaling works**: Adding a second node significantly reduced CPU pressure on the primary node under identical load
- **Multi-cloud is viable**: Spanning the cluster across Azure and GCP over public WAN using Flannel VXLAN worked reliably, with inter-cloud pod communication confirmed via Grafana
- **Network traffic is proof**: High inter-node packet transfer rates between cloud providers confirmed real cross-cloud pod communication
- **K3s is production-ready**: The lightweight distribution handled full workload scheduling, rescheduling, and cross-cloud pod distribution without manual intervention
- **Observability is essential**: Without Prometheus + Grafana, performance differences across phases would be invisible

---

## 🔧 Troubleshooting

**Port already in use after reconnecting:**
```bash
sudo fuser -k 8080/tcp
sudo fuser -k 3000/tcp
```

**Deallocating VMs to stop billing:**
Azure Portal / GCP Console → Virtual Machines → select instance → **Stop** → confirm deallocated state

---

## 🗺️ Roadmap

- [x] Phase 1: Single-node Azure deployment
- [x] Phase 2: Multi-node Azure cluster
- [x] Phase 3: Multi-cloud deployment (Azure + GCP)
- [ ] Phase 4: Edge topology benchmarking

---

## 🧰 References

- [K3s Documentation](https://docs.k3s.io/)
- [Helm](https://helm.sh/)
- [Google Cloud Boutique Demo](https://github.com/GoogleCloudPlatform/microservices-demo)
- [Kube-Prometheus-Stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [Locust](https://locust.io/)

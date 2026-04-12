# Industrial Equipment Monitoring — Troubleshooting Guide

This document covers every problem encountered during the build of this
project and how each one was fixed.

---

## Problem 1 — Python venv fails to create

### Error message
```
The virtual environment was not created successfully because ensurepip
is not available.
```

### Cause
Ubuntu does not install the venv module with Python by default.

### Fix
```
sudo apt install python3-venv -y
python3 -m venv venv
source venv/bin/activate
```

---

## Problem 2 — scipy fails to install

### Error message
```
ERROR: Could not find a version that satisfies the requirement scipy
```

### Cause
scipy does not yet support Python 3.14. The project does not actually
require scipy — only numpy is needed for statistical calculations.

### Fix
Remove scipy from the install command. Install without it:
```
pip install confluent-kafka prometheus-client boto3 numpy \
  python-dotenv pytest pytest-cov pytest-mock
```

---

## Problem 3 — pip install fails with no matching distribution

### Error message
```
ERROR: No matching distribution found for pytest
```

### Cause
pip version was outdated and could not resolve packages for Python 3.14.

### Fix
Upgrade pip first, then install packages:
```
pip install --upgrade pip
pip install confluent-kafka prometheus-client boto3 numpy \
  python-dotenv pytest pytest-cov pytest-mock
```

---

## Problem 4 — docker compose command not found

### Error message
```
docker: 'compose' is not a docker command
```

### Cause
The Docker Compose plugin was not installed separately on Ubuntu 24.

### Fix
Download and install Docker Compose manually:
```
sudo curl -L \
  "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose

sudo chmod +x /usr/local/bin/docker-compose
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
docker-compose --version
```

---

## Problem 5 — docker-compose crashes with distutils error

### Error message
```
ModuleNotFoundError: No module named 'distutils'
```

### Cause
The apt version of docker-compose is broken on Ubuntu 24 because
Python 3.12 removed the distutils module.

### Fix
Remove the broken apt version and use the binary downloaded in Problem 4:
```
sudo apt remove docker-compose -y
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## Problem 6 — Prometheus shows 0 results for all queries

### Symptom
Typing any metric name in Prometheus returns Result series: 0.

### Cause
On Ubuntu, Docker containers cannot reach the host machine using
host.docker.internal. Prometheus was configured with that address
and could not reach the consumer metrics endpoint on port 8000.

### Fix — two steps required

Step 1: Update prometheus.yml with your actual laptop IP.
Get your IP:
```
hostname -I | awk '{print $1}'
```

Edit monitoring/prometheus.yml and replace host.docker.internal
with your IP address. Example:
```
targets: ["192.168.8.153:8000"]
```

Restart Prometheus:
```
docker-compose restart prometheus
```

Step 2: Allow port 8000 through the Ubuntu firewall:
```
sudo ufw allow 8000
```

Verify Prometheus can now reach the target by going to:
http://localhost:9090/targets

The anomaly-consumer target should show state UP.

---

## Problem 7 — git push fails with error

### Error message
```
error: failed to push some refs to origin
```

### Cause
The remote repository had a file (README or licence) that the local
repository did not have. The histories diverged.

### Fix
Pull with unrelated histories allowed, then push:
```
git pull origin Main --allow-unrelated-histories
git push -u origin Main
```

---

## Problem 8 — git branch name mismatch

### Symptom
```
fatal: couldn't find remote ref main
```

### Cause
GitHub created the default branch as Main (capital M) but git commands
used main (lowercase).

### Fix
Check your local branch name:
```
git branch
```

Use the exact name shown when pushing:
```
git push -u origin Main
```

---

## Problem 9 — Terraform vCPU limit exceeded

### Error message
```
api error VcpuLimitExceeded: You have requested more vCPU capacity
than your current vCPU limit of 1 allows
```

### Cause
New AWS accounts have a default vCPU limit of 1 for t3 instances.
This project requires a minimum of 8 vCPUs to run all instances.

### Fix
Request a vCPU limit increase from AWS:
1. Go to https://aws.amazon.com/contact-us/ec2-request
2. Select EC2 service limit increase
3. Choose region eu-west-1
4. Request 8 vCPUs for on-demand standard instances
5. State you are a cloud engineering student
6. AWS typically approves within 24 hours

While waiting for approval, destroy the partial infrastructure
to avoid charges:
```
cd infrastructure
terraform destroy -auto-approve
```

---

## Problem 10 — Terraform partially created resources then failed

### Symptom
Terraform apply failed midway. Some resources were created, some were not.
Running apply again shows errors about existing resources.

### Fix
Always run destroy first to clean up partial state, then apply again:
```
terraform destroy -auto-approve
terraform apply -auto-approve
```

---

## Problem 11 — Consumer shows no output after starting

### Symptom
Running the consumer shows the startup message but nothing else happens.
No anomaly warnings appear.

### Cause
This is correct behaviour. The consumer is waiting for messages.
It will show output only after the producer starts sending data.

### Fix
Start the producer in a separate terminal tab:
```
source venv/bin/activate
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python3 -m simulator.producer
```

Switch back to the consumer terminal. Anomaly warnings will appear
within 30 seconds.

---

## Problem 12 — Grafana shows Welcome page with no dashboards

### Symptom
Grafana opens but shows only the welcome screen. No dashboards visible.

### Cause
Either the Prometheus data source was not configured or the dashboard
was not imported.

### Fix — two steps

Step 1: Add Prometheus as a data source:
- Menu → Connections → Data sources → Add data source → Prometheus
- URL: http://prometheus:9090
- Click Save and test
- Should show: Successfully queried the Prometheus API

Step 2: Import the dashboard:
- Menu → Dashboards → New → Import
- Paste the dashboard JSON
- Click Load then Import

---

## General tips

Always activate the virtual environment before running Python commands:
```
source venv/bin/activate
```

Always check Docker containers are running before starting the producer
or consumer:
```
docker-compose ps
```

All containers should show status Up or healthy.

To stop everything cleanly:
```
docker-compose down
```

To stop everything and delete all data (full reset):
```
docker-compose down -v
```

To see logs from a specific container:
```
docker-compose logs kafka-1 --tail=50
docker-compose logs grafana --tail=50
docker-compose logs prometheus --tail=50
```

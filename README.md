# Traffic Simulator – FortiGate Administrator Labs

A lightweight **Ubuntu GUI traffic simulator** designed for **FortiGate Administrator (FortiOS 7.6)** training and hands-on security labs.

This tool generates **benign, controlled network traffic** that allows students and instructors to practice detection, visibility, and policy enforcement using Fortinet security features.

---

## 🎯 Purpose

The Traffic Simulator is built for **defensive security education**, not offensive activity.

It helps demonstrate and validate:

- Antivirus (AV)
- Web Filtering
- Application Control
- Intrusion Prevention System (IPS)
- Indicators of Compromise (IOC / Threat Feeds)
- DoS policies and traffic shaping
- Logging and visibility in FortiGate and FortiAnalyzer

All traffic is generated using **simple HTTPS requests (`curl`)** and is intended **only for controlled lab environments**.

---

## ✨ Key Features

- 🖥️ **Simple GUI (Tkinter)** – no browser or heavy frameworks
- 🎯 **Named targets** with expected FortiGuard category
- ✍️ **Editable target field** (select preset or type IP manually)
- 🔁 **One-shot or loop mode**
- 📜 **Live execution logs** inside the GUI
- 🔌 **Network interface selector**
- 📦 **Scenario import/export (JSON)**
- 🛡️ **Ethical guardrails** using allow-lists via configuration file

---

## 🚦 Traffic Types Generated

### 1️⃣ Virus Download
Used to validate:
- Antivirus
- SSL Inspection
- Logging

Intended for **test files (e.g. EICAR)** in a lab environment.

---

### 2️⃣ Application Traffic
Simulates real-world **application categories**:

- **Video / Streaming**  
  YouTube, Twitch, Vimeo

- **Cloud & SaaS**  
  AWS, Microsoft login, Google Drive, Dropbox

- **Instant Messaging / Collaboration**  
  WhatsApp Web, Discord, Slack, Telegram

Used mainly for:
- Application Control
- SSL Inspection
- DNS Filtering

---

### 3️⃣ Web Testing
Generates HTTPS requests to test:
- Web Filter categories
- Policy enforcement
- Logging and reporting

Default destinations:
- `www.hak5.org`
- `www.fortinet.com`
- `www.cnn.com`
- `www.bbc.com`
- `www.facebook.com`
- `www.instagram.com`

---

### 4️⃣ IPS Test
- Sends HTTP requests with custom paths and User-Agents
- Designed to trigger **custom IPS signatures**
- No exploitation payloads included

---

### 5️⃣ IOC Beacon
- Periodic HTTP beaconing to a target IP
- Used to demonstrate:
  - IOC blocking
  - External Connectors
  - Threat Feeds

---

### 6️⃣ Controlled Load
- Generates **rate-limited HTTP traffic**
- Used to demonstrate:
  - DoS policies
  - Traffic shaping
- **Not a flood**, safe for lab environments

---

## 🖥️ Requirements (Ubuntu)

### Mandatory packages
```bash
sudo apt update
sudo apt install -y python3 python3-tk curl iproute2

## License

This project is licensed under the Creative Commons
Attribution–NonCommercial 4.0 International License (CC BY-NC 4.0).

✔ Allowed:
- Educational use
- Personal labs
- Research
- Workshops in academic environments (with prior consent from the Author)

❌ Not allowed without permission:
- Commercial use
- Paid services
- Bundling into products
- Resale or redistribution for profit

For commercial licensing, contact the author.

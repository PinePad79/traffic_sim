# 🧪 FortiGate IPS Lab Guide  
## Traffic Simulator – Hands-On (FortiOS 7.6)

---

## 🎯 Objetivo del laboratorio

Al finalizar este laboratorio, el estudiante será capaz de:

- Crear **firmas IPS custom**
- Aplicar un **IPS Sensor** a una firewall policy
- Generar **tráfico controlado** desde el Traffic Simulator
- Interpretar correctamente los **logs de IPS**
- Entender la diferencia entre **detección (pass)** y **bloqueo (block)**

---

## 🧩 Arquitectura del Lab (simple)

```
Traffic Simulator (Ubuntu)
        |
        |  HTTP / HTTPS
        v
     FortiGate
        |
        v
 Destination Server (HTTP)
```

---

## 🔹 PARTE 1 – Preparar el servidor destino (5 minutos)

### Opción recomendada: Python HTTP Server

En el **host destino (Linux)** ejecuta:

```bash
mkdir -p ~/lab_http/{exploit-test,beacon}
echo "Exploit test endpoint" > ~/lab_http/exploit-test/index.html
echo "Beacon endpoint" > ~/lab_http/beacon/index.html

cd ~/lab_http
sudo python3 -m http.server 80
```

### Validación rápida

```bash
curl http://<SERVER-IP>/exploit-test
curl http://<SERVER-IP>/beacon
```

Si el servidor responde texto, el endpoint está listo para el laboratorio.

---

## 🔹 PARTE 2 – Crear firmas IPS custom (FortiGate CLI)

### 🔴 Firma 1 – Exploitation (HTTP Path)

```bash
config ips custom
    edit "LAB-EXPLOIT-HTTP-PATH"
        set severity high
        set signature "F-SBID(
            --name "LAB-EXPLOIT-HTTP-PATH";
            --service HTTP;
            --pattern "/exploit-test";
            --context uri;
            --no_case;
        )"
        set action block
    next
end
```

---

### 🔴 Firma 2 – Exploitation (User-Agent)

```bash
config ips custom
    edit "LAB-EXPLOIT-USER-AGENT"
        set severity high
        set signature "F-SBID(
            --name "LAB-EXPLOIT-USER-AGENT";
            --service HTTP;
            --pattern "Lab-Traffic-Sim";
            --context header;
            --no_case;
        )"
        set action block
    next
end
```

---

### 🟠 Firma 3 – IOC Beacon

```bash
config ips custom
    edit "LAB-IOC-BEACON"
        set severity medium
        set signature "F-SBID(
            --name "LAB-IOC-BEACON";
            --service HTTP;
            --pattern "/beacon";
            --context uri;
            --no_case;
        )"
        set action block
    next
end
```

---

## 🔹 PARTE 3 – Crear el IPS Sensor

```bash
config ips sensor
    edit "IPS-LAB-TRAINING"
        config entries
            edit 1
                set rule "LAB-EXPLOIT-HTTP-PATH"
            next
            edit 2
                set rule "LAB-EXPLOIT-USER-AGENT"
            next
            edit 3
                set rule "LAB-IOC-BEACON"
            next
        end
    next
end
```

---

## 🔹 PARTE 4 – Crear / Editar la Firewall Policy

1. Ir a **Policy & Objects → Firewall Policy**
2. Crear o editar una policy desde:
   - **Source**: Traffic Simulator
   - **Destination**: Server
3. Activar:
   - ✅ **IPS** = `IPS-LAB-TRAINING`
   - ✅ **Log Allowed Traffic** = All Sessions
4. Guardar la policy

---

## 🔹 PARTE 5 – Ejecutar pruebas desde el Traffic Simulator

### Orden recomendado en clase

1. **IPS Test**
2. **IOC Beacon**
3. **Tráfico Apps**
4. **Web Testing**
5. **Controlled Load**

---

## 📊 Tabla de correlación: Botón → IPS → Log esperado

| Botón en GUI | Firma IPS | Acción | Log esperado |
|-------------|----------|--------|--------------|
| IPS Test | LAB-EXPLOIT-HTTP-PATH | Block | URI `/exploit-test` detectado |
| IPS Test | LAB-EXPLOIT-USER-AGENT | Block | Header `Lab-Traffic-Sim` |
| IOC Beacon | LAB-IOC-BEACON | Block | Repetitive beaconing |
| Tráfico Apps | N/A (App Control) | Allow | Application category detected |
| Web Testing | N/A (Web Filter) | Allow / Block | Category-based logs |
| Controlled Load | (opcional) | Allow | Session / rate visibility |

---

## 🔍 Dónde ver los logs

### En FortiGate
- **Log & Report → Security Events → Intrusion Prevention**
- Revisar:
  - Signature name
  - Severity
  - Action (block)
  - Source / Destination IP
  - URL o Header detectado

### En FortiAnalyzer (si aplica)
- IPS Events
- Timeline
- Event correlation

---

## 🔄 Script de RESET del LAB (rápido)

Guárdalo como **`reset_lab.sh`** y ejecútalo vía CLI/SSH:

```bash
#!/bin/bash
echo "Resetting IPS lab..."

config ips sensor
    delete "IPS-LAB-TRAINING"
end

config ips custom
    delete "LAB-EXPLOIT-HTTP-PATH"
    delete "LAB-EXPLOIT-USER-AGENT"
    delete "LAB-IOC-BEACON"
end

diagnose log delete all

echo "Lab reset completed."
```

⚠️ **Nota para estudiantes:** este script elimina los logs IPS.

---

## 🧠 Tips pedagógicos (recomendados)

- Cambia inicialmente las firmas a `action pass`
- Ejecuta el tráfico y revisa logs
- Cambia luego a `action block`
- Compara resultados
- Discute en clase:
  - “¿Esto es realmente un exploit?”
  - “¿Puede ser un false positive?”
- Introduce el concepto de **detección vs prevención**

---

## ✅ Resultado esperado

El estudiante:
- Comprende cómo funciona **IPS en la práctica**
- Aprende a crear y validar firmas custom
- Interpreta correctamente logs de seguridad
- Entiende riesgos de **false positives**
- Gana confianza operando FortiGate en escenarios reales

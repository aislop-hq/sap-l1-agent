---
title: ICM / Web Dispatcher Issues
keywords: [ICM, HTTP, HTTPS, web dispatcher, SMICM, port, connection refused, 503, 500, SSL, certificate]
sap_note: 1201898
risk: MEDIUM
action: restart_icm
fix_command: "sapcontrol -nr {NR} -function RestartService"
verify_command: "sapcontrol -nr {NR} -function GetProcessList"
---

# ICM / Web Dispatcher Issues

## Overview

The Internet Communication Manager (ICM) handles all HTTP/HTTPS traffic to
the SAP instance — Fiori apps, OData services, Web GUI, and RFC over HTTP.
When ICM fails or becomes unresponsive, all web-based access to SAP stops
while SAP GUI (DIAG protocol) may still work.

## Symptoms

- Users cannot access Fiori launchpad or Web GUI
- HTTP requests return 503 Service Unavailable or connection refused
- Transaction SMICM shows ICM status YELLOW or RED
- `GetProcessList` shows `icman` as YELLOW or GRAY
- SAP GUI works normally (indicates DIAG protocol is fine, only HTTP affected)

## Diagnosis Steps

### 1. Check ICM process status

```bash
sapcontrol -nr <NR> -function GetProcessList
```

Look for the `icman` process. If GRAY → ICM is completely down.
If YELLOW → ICM is overloaded or partially failed.

### 2. Check ICM thread status

In SMICM → Goto → Threads. Look for:
- All threads in "waiting" = ICM is idle (possibly not receiving requests)
- All threads "running" = ICM is overloaded
- Thread count = 0 → ICM process is crashed

### 3. Read ICM trace

```bash
tail -200 /usr/sap/<SID>/work/dev_icm
```

Common error patterns:
- `SSL handshake failed` → certificate issue
- `bind() failed for port XXXX` → port conflict
- `max_conn reached` → too many concurrent connections
- `worker thread pool exhausted` → need more ICM threads

### 4. Test port connectivity

```bash
curl -k https://localhost:443<NR>/sap/bc/ping
# Should return HTTP 200 if ICM is healthy
```

## Remediation

### Restart ICM only (without full instance restart)

```bash
sapcontrol -nr <NR> -function RestartService
```

Or from SMICM → Administration → ICM → Restart (soft restart).

### Fix SSL certificate issues

If certificates are expired:
1. Check in STRUST → SSL Server Standard
2. Renew and import the certificate
3. Restart ICM

### Increase ICM threads

If thread exhaustion is the issue, adjust in the instance profile:
```
icm/max_threads = 40    # default is often 20
icm/max_conn = 500      # max concurrent connections
```

## Risk Assessment

**MEDIUM** — restarting ICM briefly interrupts all HTTP connections (1-2 seconds)
but does not affect SAP GUI users or batch jobs. However, if the root cause is
not addressed, ICM will crash again.

## Related SAP Notes

- SAP Note 1201898: ICM troubleshooting guide
- SAP Note 510007: ICM configuration parameters
- SAP Note 2aborrecall: SSL/TLS certificate management in STRUST

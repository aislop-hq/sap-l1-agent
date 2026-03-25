---
title: Instance Down — Full Outage
keywords: [instance, down, GRAY, dispatcher, stopped, start, outage, StartService, GetSystemInstanceList, crash]
sap_note: 2318837
risk: HIGH
action: escalate
fix_command: ""
verify_command: ""
---

# Instance Down — Full Outage

## Overview

When an SAP ABAP application server instance is completely down, all processes
(dispatcher, work processes, ICM, gateway) are stopped and the instance shows
status GRAY in sapcontrol. This is the most severe L1 incident type as it
represents a full outage for all users connected to that application server.

An instance-down scenario requires immediate escalation. While L1 can perform
initial diagnosis, the restart decision must involve L2 Basis, application
owners, and potentially change management depending on the environment.

**CRITICAL:** Do NOT restart production instances without explicit approval
from the on-call L2 Basis administrator and application owner.

## Symptoms

- `sapcontrol -nr <NR> -function GetSystemInstanceList` shows the instance
  with `dispstatus = GRAY`
- `sapcontrol -nr <NR> -function GetProcessList` shows all processes as
  `Stopped` with empty PID fields
- Users report "connection refused" or "system unavailable" errors
- SAP logon pad shows the instance as unreachable
- Monitoring system (SolMan, Focused Run) triggers GRAY alert

## Diagnosis Steps

### 1. Confirm instance status

```bash
sapcontrol -nr <NR> -function GetSystemInstanceList
```

Expected output for a down instance:
```
hostname, instanceNr, httpPort, httpsPort, startPriority, features, dispstatus
sap-host, 00, 50013, 50014, 1, ABAP|GATEWAY, GRAY
```

### 2. Check individual process status

```bash
sapcontrol -nr <NR> -function GetProcessList
```

All processes will show `GRAY` / `Stopped`. If some processes are GREEN
and others GRAY, this is a partial failure — see the "Partial Instance
Failure" section below.

### 3. Check OS-level health

Before attempting any restart, verify the host is healthy:

```bash
# Is the host reachable?
ping -c 3 <hostname>

# CPU and memory
top -bn1 | head -20

# Disk space — a full filesystem is a common cause of instance crashes
df -h

# Check if the OS killed SAP processes (OOM killer)
dmesg | grep -i "out of memory\|oom\|killed process" | tail -20

# Check if SAP processes are truly gone
ps aux | grep -i "dw\.\|disp+work\|sapstart"
```

### 4. Read the dispatcher trace

The dispatcher trace usually contains the crash reason:

```bash
tail -200 /usr/sap/<SID>/work/dev_disp
```

Common crash reasons:
- `ENOMEM` / memory allocation failure → OS memory exhaustion
- `Signal 9 (SIGKILL)` → OOM killer terminated the process
- `Signal 11 (SIGSEGV)` → kernel or dispatcher bug
- `bind() failed` → port conflict (another process using the SAP port)
- `shared memory` errors → `/dev/shm` too small or IPC limits exceeded

### 5. Check system log (if instance was recently running)

```bash
sapcontrol -nr <NR> -function ReadLogFile dev_disp 500
```

## Root Cause Categories

| Category              | Indicators                              | Frequency |
|-----------------------|-----------------------------------------|-----------|
| OS out of memory      | dmesg shows OOM, swap exhausted         | Common    |
| Filesystem full       | df -h shows 100%, trace write failures  | Common    |
| Kernel/dispatcher bug | SIGSEGV in dev_disp                     | Rare      |
| Manual stop           | Clean "shutdown" in dev_disp            | Check SM21|
| Power/hardware        | Host unreachable, no SSH                | Rare      |
| Port conflict         | bind() errors in dev_disp               | After OS patch |
| Shared memory         | shmat/shmget errors                     | After OS change|

## Remediation

### DO NOT restart without authorization

For production systems:
1. Notify the on-call L2 Basis administrator
2. Get explicit approval from the application owner
3. Verify no maintenance or patching is in progress
4. Check the change calendar — is this a planned outage?

### Pre-restart checklist

Before issuing a start command:
- [ ] Host is pingable and SSH works
- [ ] `df -h` shows adequate free space on all SAP-relevant filesystems
- [ ] `free -h` shows adequate available memory
- [ ] `dmesg` shows no ongoing hardware errors
- [ ] No port conflicts for SAP ports (50000+NR*100 range)
- [ ] Check `/dev/shm` has adequate space for SAP shared memory

### Start the instance (after approval)

```bash
sapcontrol -nr <NR> -function Start
```

Monitor startup:
```bash
sapcontrol -nr <NR> -function GetProcessList
# Wait for all processes to show GREEN
```

Typical startup time: 2-5 minutes for a standard ABAP instance.

### Post-restart verification

1. All processes GREEN in `GetProcessList`
2. Users can log in via SAP GUI
3. Batch jobs (SM37) are running
4. No error messages in SM21 system log
5. ICM status is green (SMICM)

## Partial Instance Failure

If only some processes are down (e.g., ICM stopped but dispatcher running):
- This is NOT a full outage — handle as a targeted process restart
- Use `sapcontrol -nr <NR> -function RestartService` for individual services
- Do NOT use `Start` / `Stop` for partial failures

## Risk Assessment

**HIGH** — a full instance restart impacts all connected users, terminates
active transactions, and kills running batch jobs. Data loss is possible if
update processes are interrupted. Always coordinate with stakeholders.

## Related SAP Notes

- SAP Note 2318837: Procedure for SAP instance restart after crash
- SAP Note 927637: Startup problems with SAP instances
- SAP Note 1514966: Understanding SAP process types and states

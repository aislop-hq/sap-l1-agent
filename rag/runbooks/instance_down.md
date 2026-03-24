---
title: Instance Down
keywords: [instance, down, GRAY, dispatcher, stopped, start]
sap_note: 2318837
risk: HIGH
---

# Instance Down

## Symptoms
- `sapcontrol -nr <NR> -function GetSystemInstanceList` shows GRAY status
- `GetProcessList` shows all processes as Stopped
- Users cannot connect to the instance

## Diagnosis
1. Run `GetSystemInstanceList` to confirm instance status
2. Run `GetProcessList` to check individual process states
3. Check OS-level: is the host reachable? Disk space? Memory?
4. Check `/usr/sap/<SID>/work/dev_disp` for dispatcher crash reason

## Remediation
- **Escalate** — instance restart requires coordination
- Verify OS health before attempting restart
- Use `sapcontrol -nr <NR> -function Start` only after OS checks pass
- Notify application team and users before restart

## Risk
HIGH — full instance restart impacts all connected users and batch jobs.

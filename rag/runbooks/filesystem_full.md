---
title: Filesystem Full
keywords: [filesystem, disk, full, cleanup, rotate, dev_w, trace]
sap_note: 2399996
risk: MEDIUM
---

# Filesystem Full

## Symptoms
- `df -h` shows /usr/sap/<SID>/work at >90% usage
- Old trace files (dev_w*.old, dev_disp.old) consuming significant space
- Application may slow down or fail to write new traces

## Diagnosis
1. Run `df -h` to confirm which filesystem is full
2. Run `ls -lh /usr/sap/<SID>/work/` to identify large old files
3. Check age of .old trace files — anything >30 days is safe to remove

## Remediation
- Remove old trace files: `rm /usr/sap/<SID>/work/dev_*.old`
- Rotate current logs if they are excessively large
- Consider setting up automated log rotation via cron

## Risk
MEDIUM — removing old trace files is safe, but verify no active investigation needs them.

---
title: Filesystem Full — Work Directory
keywords: [filesystem, disk, full, cleanup, rotate, dev_w, trace, df, disk space, /usr/sap, work directory]
sap_note: 2399996
risk: MEDIUM
action: cleanup_filesystem
fix_command: "find /usr/sap/{SID}/work -name '*.old' -mtime +30 -delete"
verify_command: "df -h /usr/sap/{SID}/work"
---

# Filesystem Full — Work Directory

## Overview

SAP ABAP application servers write continuous trace output to the work directory
(`/usr/sap/<SID>/work/`). Over time, these trace files — especially `dev_w*`,
`dev_disp`, `dev_rd`, and their `.old` rotated copies — can consume tens of
gigabytes. When the filesystem reaches >90% usage, the instance may fail to
write new traces, leading to unpredictable behavior including work process
crashes, failed batch jobs, and inability to create short dumps.

This is one of the most common preventable Basis incidents and typically
indicates missing or misconfigured log rotation.

## Symptoms

- Monitoring alert: filesystem usage >90% on `/usr/sap/<SID>/work`
- `df -h` confirms the mount point is critically full
- `ls -lh /usr/sap/<SID>/work/` reveals large `.old` trace files dating
  back weeks or months
- Users may see "no space left on device" errors in transactions
- New short dumps (ST22) fail to be written — the dump counter shows gaps
- Batch jobs (SM37) fail with file I/O errors

## Diagnosis Steps

### 1. Confirm filesystem usage

```bash
df -h /usr/sap/<SID>/work
```

Critical thresholds:
- **>85%**: Warning — schedule cleanup
- **>90%**: Critical — clean up immediately
- **>95%**: Emergency — instance stability at risk

### 2. Identify space consumers

```bash
ls -lhS /usr/sap/<SID>/work/
```

Sort by size (`-S`) to find the largest files. Common offenders:

| File pattern       | Description                    | Safe to delete?           |
|--------------------|--------------------------------|---------------------------|
| `dev_w*.old`       | Rotated work process traces    | Yes, if >7 days old       |
| `dev_disp.old`     | Rotated dispatcher trace       | Yes, if >7 days old       |
| `dev_rd.old`       | Rotated reader trace           | Yes, if >7 days old       |
| `dev_w*` (current) | Active work process traces     | No — truncate only        |
| `*.trc`            | SQL trace files (ST05)         | Yes, after analysis       |
| `core.*`           | OS core dumps                  | Yes, after dump analysis  |
| `snap.*`           | ABAP short dump raw files      | Yes, if archived in ST22  |

### 3. Check file ages

```bash
find /usr/sap/<SID>/work/ -name "*.old" -mtime +30 -ls
```

Files older than 30 days are almost always safe to remove. Files older than
7 days are safe unless there is an active investigation referencing them.

### 4. Check if log rotation is configured

Look for a cron job or SAP-provided rotation script:

```bash
crontab -l -u <sid>adm | grep -i "log\|rotate\|cleanup"
```

If no rotation exists, this is the root cause and must be fixed permanently.

## Remediation

### Immediate: Remove old trace files

```bash
cd /usr/sap/<SID>/work
rm -f dev_w*.old dev_disp.old dev_rd.old
```

This typically frees 5-20 GB depending on how long rotation has been broken.

### Immediate: Remove core dumps

```bash
find /usr/sap/<SID>/work -name "core.*" -delete
```

Core dumps can be 2-4 GB each and are only needed for kernel debugging.

### Permanent: Set up log rotation

Add to `<sid>adm` crontab:

```bash
# Rotate SAP traces weekly, keep 4 copies
0 2 * * 0 /usr/sap/<SID>/work/cleanup.sh
```

Or use SAP's built-in parameter to control trace file size:
- Profile parameter `rdisp/TRACE_LOGGING` = `on` (enables automatic rotation)
- Profile parameter `rdisp/max_trace_filesize` = `52428800` (50 MB max per trace)

## Post-Cleanup Verification

After cleanup, verify:
1. `df -h` shows usage below 80%
2. SAP instance is writing traces normally: `tail -f /usr/sap/<SID>/work/dev_w0`
3. No errors in SM21 system log related to I/O failures

## Risk Assessment

**MEDIUM** — removing `.old` files is safe and routine. However, removing files
from an active investigation or deleting current (non-`.old`) trace files can
destroy diagnostic evidence. Always check with L2 before deleting files during
an ongoing incident.

## Related SAP Notes

- SAP Note 2399996: Filesystem monitoring best practices for SAP systems
- SAP Note 16: Trace files in SAP work directory
- SAP Note 1438410: Automatic cleanup of trace files

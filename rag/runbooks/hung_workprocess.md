---
title: Hung Work Process
keywords: [WP, STOPPED, SIGSEGV, RestartService]
sap_note: 1234567
risk: LOW
---

# Hung Work Process

## Symptoms
- Work process shows status STOPPED in SM50/sapcontrol ABAPGetWPTable
- SIGSEGV or other signal in dev_w* trace file
- Users report transaction timeouts

## Diagnosis
1. Run `sapcontrol -nr <NR> -function ABAPGetWPTable` to identify the stopped WP
2. Read the corresponding `dev_w<N>` trace file for the crash signature
3. Check if a specific function module or program triggered the crash

## Remediation
- Restart the individual work process via `sapcontrol -nr <NR> -function RestartService`
- If the crash is reproducible, investigate the ABAP code in the offending function module
- Apply SAP Note 1234567 if the crash matches the known SIGSEGV pattern

## Risk
LOW — restarting a single work process does not affect other users or processes.

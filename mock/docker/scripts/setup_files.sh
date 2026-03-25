#!/bin/bash
# Populate /usr/sap/DEV/work/ with scenario-specific trace files.
# Called at container start. Reads SAP_SCENARIO env var.

set -e

SCENARIO="${SAP_SCENARIO:-1}"
WORK="/usr/sap/DEV/work"

mkdir -p "$WORK"

# ── Scenario 1: Hung Work Process ───────────────────────────────────────
write_scenario_1() {
    cat > "$WORK/dev_w0" <<'EOF'
trc file: "dev_w0", trc level: 1, component: "ABAP"
M  normal operation, no errors
EOF

    cat > "$WORK/dev_w1" <<'EOF'
trc file: "dev_w1", trc level: 1, component: "ABAP"
M  normal operation, no errors
EOF

    cat > "$WORK/dev_w2" <<'EOF'
***LOG Q0I=> SigISegv, signal 11 received  [dpnpcheck.c   723]
***LOG Q04=> SIGSEGV caught in Z_CUSTOM_FM
***LOG Q0I=> work process WP02 is being restarted
trc file: "dev_w2", trc level: 1, component: "ABAP"
M  ***LOG R19=> SIGSEGV in function module Z_CUSTOM_FM (program SAPLZ_CUSTOM)
M  ABAP dump: SYSTEM_DUMP / SIGSEGV
EOF

    cat > "$WORK/dev_disp" <<'EOF'
trc file: "dev_disp", trc level: 1
M  Dispatcher running normally
EOF
}

# ── Scenario 2: Filesystem Full ─────────────────────────────────────────
write_scenario_2() {
    cat > "$WORK/dev_w0" <<'EOF'
trc file: "dev_w0", trc level: 1, component: "ABAP"
M  normal operation
EOF

    cat > "$WORK/dev_w1" <<'EOF'
trc file: "dev_w1", trc level: 1, component: "ABAP"
M  normal operation
EOF

    # Create large-ish .old files (small but present for ls to show)
    for f in dev_w0.old dev_w1.old dev_w2.old dev_disp.old dev_rd.old; do
        dd if=/dev/zero of="$WORK/$f" bs=1K count=1 2>/dev/null
    done

    cat > "$WORK/dev_disp" <<'EOF'
trc file: "dev_disp", trc level: 1
M  Dispatcher running normally
EOF
}

# ── Scenario 3: ABAP Dump TIME_OUT ──────────────────────────────────────
write_scenario_3() {
    cat > "$WORK/dev_w0" <<'EOF'
trc file: "dev_w0", trc level: 1, component: "ABAP"
M  ***LOG R15=> ABAP runtime error TIME_OUT occurred
M  ABAP Program: ZREPORT_HEAVY
M  Source: ZREPORT_HEAVY line 1042
M  Error: TIME_OUT — program exceeded maximum runtime
M  Long running SELECT on table VBAK without proper WHERE clause
M  User: ZBATCHUSER  Client: 001
M  No checkpoint/commit found in main loop
EOF

    cat > "$WORK/dev_w1" <<'EOF'
trc file: "dev_w1", trc level: 1, component: "ABAP"
M  normal operation
EOF

    cat > "$WORK/dev_disp" <<'EOF'
trc file: "dev_disp", trc level: 1
M  Dispatcher running normally
EOF
}

# ── Scenario 4: Instance Down ───────────────────────────────────────────
write_scenario_4() {
    cat > "$WORK/dev_w0" <<'EOF'
trc file: "dev_w0", trc level: 1, component: "ABAP"
M  process terminated
EOF

    cat > "$WORK/dev_disp" <<'EOF'
trc file: "dev_disp", trc level: 1
M  *** ERROR => dispatcher terminated by signal 9 (SIGKILL)
M  *** possible OOM killer intervention
EOF
}

# ── Write files for selected scenario ───────────────────────────────────
echo "[setup] Writing files for scenario $SCENARIO"

case "$SCENARIO" in
    1) write_scenario_1 ;;
    2) write_scenario_2 ;;
    3) write_scenario_3 ;;
    4) write_scenario_4 ;;
    *) echo "[setup] Unknown scenario $SCENARIO, defaulting to 1"; write_scenario_1 ;;
esac

chown -R devadm:devadm "$WORK" 2>/dev/null || true
echo "[setup] Done — /usr/sap/DEV/work/ populated"

---
name: rtk
description: Use this skill whenever the user asks you to run shell commands in the terminal, especially git, cargo, docker, kubectl, or other CLI tools that may produce large outputs. This skill provides instructions for prefixing commands with the `rtk` CLI proxy to filter and compress outputs, saving 60-90% tokens. Apply it even if the user just says "run tests", "check status", or "show logs" without explicitly mentioning rtk.
---

<!-- rtk-instructions v2 -->
# RTK — Token-Optimized CLI

**rtk** is a CLI proxy that filters and compresses command outputs, saving 60-90% tokens.

## Rule

Always prefix shell commands with `rtk`:

```bash
# Instead of:              Use:
git status                 rtk git status
git log -10                rtk git log -10
cargo test                 rtk cargo test
docker ps                  rtk docker ps
kubectl get pods           rtk kubectl pods
```

## Meta commands (use directly)

```bash
rtk gain              # Token savings dashboard
rtk gain --history    # Per-command savings history
rtk discover          # Find missed rtk opportunities
rtk proxy <cmd>       # Run raw (no filtering) but track usage
```
<!-- /rtk-instructions -->

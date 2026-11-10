# Existing private Linux CPU sandbox controls

This is a control qualification program, not a signed original-owner worker,
private-project execution grant, model trainer or scientific first-use route.
It reuses the sealed runtime from private-project run42799893920/sourcec0dc5857,
existing Ubuntu24.04 user namespaces and the existing user-systemd manager.
No new service/daemon/controller, user account, OS package or billing change.

The only dependency added is a rootless bubblewrap binary in a NEW directory.
Its exact Ubuntu apt-cache metadata identity, archive filename/size/SHA256 are
frozen before HTTPS download from the official Ubuntu archive. Bytes must
match before dpkg-deb data extraction; package installation hooks are never run.
Setuid/setgid binaries and unsupported mandatory security features are rejected.
The host package database, AppArmor/user-namespace settings and existing
research worktrees are untouched. Missing capabilities fail; no privileged or
weaker fallback is attempted.

The frozen recipe uses mandatory user/PID/network/IPC/mount namespace isolation,
new session, parent-death handling, all capabilities dropped, no-new-privileges,
blocked nested user namespaces, read-only system/runtime mounts, fresh private
proc/dev/tmp/scratch and no host home, Windows drives, WSL interop or GPU devices.
Only non-sensitive fake passwd/group records are mounted for the sandbox user;
no host identity files, profile, token, signing key or controller DB is mounted.
The child environment is built from an explicit allowlist and cleared again by
bubblewrap. The source does not accept a candidate-supplied command or mount.

An exported libseccomp BPF profile denies namespace/mount/ptrace/key/module/
process-memory/performance/io_uring escape surfaces. clone3 returns ENOSYS for
a filtered traditional clone fallback; traditional clone cannot create namespaces.
Only Unix/IPv4/IPv6 socket families are allowed; VSOCK and packet/other families
are denied. A fresh network namespace prevents host/network reachability.
Actual BPF enforcement is independently checked by the static control probe.

The whole process tree enters an existing user-systemd transient scope. The
launcher independently reads actual cgroup2 memory.max=4GiB, memory.swap.max=0,
pids.max=64 and cpu.max=one CPU BEFORE exec. A missing manager, delegation,
controller, security feature or mismatched limit fails before the probe.
No existing process is moved into the scope or has its limits changed.

The trusted static probe tests host-file canary invisibility, host network
invisibility, no host/Windows/GPU paths, read-only runtime, private writable
scratch, visible-process environment cleanliness, capabilities/no-new-privileges,
blocked VSOCK and nested user namespaces. Only after those checks does it import
the exact public CPU Torch/pytest packages and execute one CPU tensor smoke.
No private project code, candidate patch, original world/checkpoint or GPU is run.

Receipt binds source, runtime/wheel-lock custody, Ubuntu package/binary, seccomp
filter, complete recipe, kernel/libc and critical system-library hashes and all
actual controls. Runtime custody is rechecked after the probe. This receipt is
NOT recognized as original signed worker evidence: signed_worker_qualified and
scientific_first_use remain false. Private payloads, real dual signatures,
required platforms, full candidate regression, durable terminal receipts and
original owner schema/policy admission remain separate mandatory qualifications.

# Private CPU runtime custody, without worker authority

The existing private Hybrid runner has working Ubuntu-24.04 WSL2 namespaces,
but its system Python3.12.3 lacks Torch/pytest. The current native intent
contract requires Python3.11.11; project CPU requirements pin torch2.5.1+cpu
and pytest8.3.4. Private GitHub-hosted jobs are blocked by account billing.

`python -B -m f139.private_cpu_runtime --root <new-absolute-directory>
--source-sha <qualified-source>` provisions only an unprivileged Linux runtime.
It never runs project code, candidate commands, models, GPU work, original
owner actions, queues or controllers. It never replaces system Python,
creates users/services, changes billing, requests a credential or changes the
research checkout. Existing paths are rejected, not overwritten or replayed.

Python is the upstream python-build-standalone20241219 x86_64 Linux install-only
3.11.11 archive. Its upstream SHA256 is fetched and frozen BEFORE downloading,
extracting or executing the binary. Download bytes and redirect origin are
checked. All tar paths, modes, file types and internal links are validated
before writing any extracted Python files; link parents/traversal/privilege
bits and collisions fail closed. This uses a portable runtime, not an OS
package installation or substitute interpreter identity.

The resolver downloads only wheels for the exact CPU project requirements
from the project's existing PyTorch CPU/PyPI indexes. Every resolved wheel is
validated, hashed and pinned in a complete requirements.lock BEFORE install.
GPU dependency packages, malformed/duplicate metadata, traversal, oversized
artifacts and symlinks are rejected. Installation uses no index, no dependency
resolution, no compilation and require-hashes; a separate local pip check
verifies dependency completeness. No inherited API/HMAC or netrc/keyring
credential enters provisioning subprocesses, and pip user caches are disabled.

A new0700 directory, >=8GiB available disk and >=6GiB Linux available memory
are mandatory. The trusted provisioning process lowers its own priority and
pins its CPU affinity to one already-allowed CPU. Downloads/commands are bounded;
existing research process affinity, priority, environments and system policies
are untouched. Resolver and installer output is captured, not a secret source.

The receipt binds qualified source, upstream artifact identity/hash, exact
observed Python/package versions, all wheel hashes, the offline lock and every
runtime file/link/mode. Cold verification independently recomputes custody.
Input/artifact/lock/runtime drift fails closed. Receipt schema is distinct from
signed native-worker receipts; worker_execution_authorized,
signed_worker_qualified and scientific_first_use MUST remain false. Runtime
provisioning is not namespace/filesystem/process/resource containment proof,
private signed dispatch, live lane admission, scientific acceptance or RSI.

Actual candidate execution still requires a separately qualified isolated
credential-free worker, private payload custody and original signed authorization.
The current FORGE original owner remains on source2c7caad5 with two lanes.
The provisioning command is not wired into its research tick or startup.

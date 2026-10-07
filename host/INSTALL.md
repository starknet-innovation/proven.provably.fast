# Installing the proven runner on the evaluator host

Only while no Stwo challenge job is RUNNING (any SSH login kills a running job), as root:

1. A frozen copy of this branch at `/opt/provably-fast/proven/<commit>`, root-owned and
   read-only, with `/opt/provably-fast/proven/current` pointing at it.
2. The Stwo reference binary for Linux: `entries/stwo-chain/build.sh` against a proving checkout
   at 6e80156f, with the host's pinned toolchain. The recursion statement's generator and inner
   verifier use it.
3. The sandbox user and state: `useradd --system --no-create-home proven`, then
   `/var/lib/provably-fast/proven/{queue,done,work,results}` owned by root, `work` writable by
   `proven` through the runner's chown.
4. `provably-fast-proven-runner.{service,timer}` in /etc/systemd/system, then
   `systemctl enable --now provably-fast-proven-runner.timer`.

A request is a file in the queue: `{"url": "https://github.com/team/entry", "commit": "<full hash>"}`,
optionally with `"entry"`, the entry's directory inside the repository. The runner takes the challenge
operator's host lock without waiting, so it never overlaps a job; while the operator runs, each
cycle prints `SKIPPED HOST_BUSY`.

Per request: clone at the commit (refused over 4 GB, or with under 100 GB free on the host), fetch
crates as `proven` with the network, build as `proven` without it, make the repository read-only,
then judge as root with every entrant command run as `proven` (no network, empty `/tmp`,
`/var/tmp` and `/dev/shm` of its own; needs `unshare`, `setpriv` and `mount`). The verdict goes to
a root-owned file, then to `results/oracle.jsonl` marked official; the request's files are deleted.
A failure at any step is recorded as that request's FAIL and the queue moves on. Results stay on
the host until a maintainer copies them into the repository.

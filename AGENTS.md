# Development checkout

Use the existing canonical checkout for this repository. Preserve active work,
branches used by upstream pull requests, and all uncertain or operational data.
Do not create extra worktrees or reset/clean another writer's changes.

Keep dependencies, compilation, downloaded datasets and test caches outside the
source checkout. On a Windows source-only drive, use a separate local cache
drive. Keep one writer per Git identity, one stable environment per repository,
and at most 30 GB of regenerable repository build output. Temporary proof
checkouts need an owner, purpose and closure; review them within 24 hours,
without automatic deletion. No auxiliary branch or worktree is authorized for
future tasks by this document.

`scripts/development-cache.ps1 -CacheRoot <absolute-path> -DryRun` checks
the destination without creating files. Dot-source it without `-DryRun` to set
process-local cache paths. See the Windows development section in README.md.
The host's shared runner and storage policy remain authoritative; this helper
does not change global settings or authorize cleanup. Do not remove datasets,
backups, credentials, models or unknown content as compilation cache.

Run tests offline with synthetic fixtures. Do not download live DATASUS data,
start production services, create shared databases, or exercise paid providers
for a source consolidation gate. Keep pytest output/temp data outside this
checkout. Report unrun live-provider and recovery checks separately.

Before retiring old generated output, establish exact path, regenerability,
source revision, absence of consumers and preserved unique state. Stop on a
policy rejection; do not retry the same deletion through another mechanism.
Temporary proof checkouts have a single owner and must be closed explicitly.

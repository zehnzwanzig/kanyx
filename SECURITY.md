# Security

Kanyx is an offline-first desktop application. Workspace files can contain private card contents and attachments.

- **Only import `.kanyx` files from people you trust.** The application checks archive integrity and file paths, but an archive is not a trusted identity or a digital signature.
- Preserve an independent copy of the `data/` folder or periodically export a full `.kanyx` workspace.
- Treat the USB stick as sensitive storage; Kanyx does not encrypt its database or attachment files.
- Report potential vulnerabilities privately to the repository maintainer using GitHub's private vulnerability reporting feature, if enabled. Otherwise open an issue without publishing exploit details or private data.
- Kanyx is designed for one local user/workspace. Concurrent access to the same workspace is not a supported workflow.

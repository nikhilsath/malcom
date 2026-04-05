---
title: Link a Custom Domain
slug: link-custom-domain
summary: How to publish a workspace under a custom public hostname using the proxy domain settings.
tags:
  - article-type/how-to
  - area/workspace-settings
  - workflow/domain-setup
  - audience/admin
  - verification-date/2026-04-04
created_by_agent: fact-doc-writer
updated_by_agent: fact-doc-writer
created_at: 2026-04-04T20:50:00Z
updated_at: 2026-04-05T12:30:00Z
---

# Link a Custom Domain

This guide documents the operational steps to configure workspace proxy settings for a custom public hostname.

<details>
<summary>Article metadata</summary>

- **title:** Link a Custom Domain
- **slug:** link-custom-domain
- **summary:** How to publish a workspace under a custom public hostname using the proxy domain settings.
- **tags:** article-type/how-to, area/workspace-settings, workflow/domain-setup, audience/admin
- **created_at:** 2026-04-04T20:50:00Z
- **updated_at:** 2026-04-05T12:30:00Z

</details>

## Scope

This article covers configuring proxy settings through the workspace settings flow and validating that the selected hostname resolves to your public entrypoint.

Out of scope: DNS provider account setup, TLS certificate issuance details, and reverse-proxy implementation specifics outside this repository.

## Prerequisites

- You have administrative access to the workspace settings (UI or API).
- You can update DNS records for the hostname you plan to use.

## Procedure

1. Reserve a public hostname in your DNS provider for the workspace (for example, `app.example.com`).
2. Point the hostname at the public endpoint that will front the workspace (this might be a load balancer, reverse proxy, or hosting provider). Configure an A record or CNAME as appropriate for your environment.
3. In the workspace settings UI, open the **Public proxy domain** (proxy) section or fetch current settings via `GET /api/v1/settings`.
4. Set `proxy.domain` to your hostname (for example, `app.example.com`).
5. Confirm `proxy.http_port` and `proxy.https_port` match the inbound ports your proxy will use (defaults are 80 and 443).
6. Enable runtime sync by setting `proxy.enabled` to `true` and save the settings (the UI Save action issues `PATCH /api/v1/settings`).

If you prefer the API, submit a `PATCH /api/v1/settings` payload containing the `proxy` group with the updated fields.

## Expected result

After saving with `proxy.enabled` set to `true`, the workspace persists the `proxy` values and the runtime proxy sync can use `proxy.domain`, `proxy.http_port`, and `proxy.https_port` for generated runtime state.

## Verification

- From a machine with public DNS resolution, query the hostname:

  curl -I https://app.example.com

- You should receive an HTTP response from the publicly reachable proxy that fronts the workspace. If TLS is used, ensure the proxy has a valid certificate for the hostname.

## Sources

- Internal code evidence: `backend/services/domain_proxy.py` and `ui/scripts/settings.js`.

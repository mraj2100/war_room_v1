# SmartDashboard v2.0 — Release Notes & Known Issues

## Feature Summary
SmartDashboard v2.0 introduces a fully redesigned dashboard experience with customizable widget layouts,
new real-time analytics charts, dark mode support, and an upgraded payment/subscription flow.

## Changes in This Release
- **Widget Engine v2**: Users can now drag, resize, and customize dashboard widgets. Built on new
  React-based rendering engine replacing the legacy AngularJS renderer.
- **Real-time Charts**: Chart rendering migrated from Chart.js v2 to Chart.js v4 with live data polling.
- **Dark Mode**: System-level dark mode detection + manual toggle added.
- **Payment Flow Upgrade**: Migrated payment processor from Stripe v1 to Stripe v2 API.
  New webhook handling for subscription upgrades/downgrades.
- **Mobile Optimization**: Responsive layout revamp for iOS and Android WebView.
- **API v2 Endpoints**: Backend REST endpoints upgraded from v1 to v2 schema. v1 compatibility
  shim included but marked deprecated.

## Known Issues at Launch
1. **Widget state persistence** — Widget layout may not persist across hard refreshes in some browsers.
   Workaround: Use the "Save Layout" button manually. Fix ETA: v2.0.1 (1 week).
2. **Stripe webhook latency** — Webhook confirmation delays of up to 90 seconds observed in staging
   under high load. May cause payment status to appear "pending" temporarily.
3. **Android WebView rendering** — Tab-switching in the Android WebView triggers a full re-render.
   Performance impact under investigation.
4. **API v1 shim** — Third-party integrations using v1 endpoints may see increased latency (~50ms added)
   due to the translation layer. Full v1 deprecation planned for v2.1.

## Rollback Plan
- Feature flag `smartdashboard_v2` can be toggled per-tenant via admin console.
- Full rollback to v1.9.4 available via CI/CD pipeline (estimated 15-minute deployment).
- Database schema changes are backward-compatible; no migration rollback needed.

## Risk Assessment at Launch
- **High**: Payment flow migration — Stripe v2 has different error handling. Limited production testing.
- **Medium**: Mobile WebView performance — Android 13 compatibility not fully tested.
- **Low**: Dark mode toggle — Isolated UI change, no backend dependency.

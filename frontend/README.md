# TrustVault frontend

TrustVault's frontend is a React single-page application built with Vite. It includes the login and registration form, document workspace, sharing dialog, user directory, Activity History, and Security & Audit views.

## Development

From this directory, install the dependencies and start the Vite development server with npm install followed by npm run dev.

The API base URL can be set with VITE_API_URL. Without it, the app uses the configured TrustVault Render API URL in src/api.js. Do not put secrets in frontend environment variables; Vite embeds them in client-side assets.

## Checks

Run npm test, npm run lint, and npm run build from this directory.

The tests use Node's built-in test runner for the frontend utility modules. There is no browser DOM test framework configured, so React interaction and viewport behavior require browser testing.
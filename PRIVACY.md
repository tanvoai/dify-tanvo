# Privacy Policy: Tanvo plugin for Dify

Effective date: 2026-10-10. Maintainer: Tanvo, support@tanvo.ai.

## What the plugin sends

The plugin connects Dify to Tanvo (https://tanvo.ai), an AI image, video and music service. When a tool runs, it sends over HTTPS to the Tanvo API (https://tanvo.ai/api/v1) only what that tool needs:

- your Tanvo API key, in the Authorization header, to identify your account;
- the prompt and settings passed to the tool (model, aspect ratio, duration, look, details and so on);
- any images or video clips passed to the tool. The plugin downloads them from your Dify server and uploads them to Tanvo's storage (Cloudflare R2, through a short-lived upload link) so the model can use them.

These inputs may contain personal data if you include it, for example faces in photos or names in prompts.

Tanvo passes the prompt and inputs to the model provider that runs the chosen model, then returns links to the results on media.tanvo.ai. The plugin downloads the results and hands them to Dify as files.

## What the plugin collects, stores or logs

The plugin itself does not collect, store or log user data. It has no database, analytics or telemetry. Dify keeps the API key in its encrypted credential store, and keeps workflow runs and generated files according to your deployment's settings.

## Third parties

The only recipient is Tanvo, under its privacy policy: https://tanvo.ai/privacy-policy. Tanvo shares prompts and inputs with the model providers that run the models, as that policy describes. Prompts and uploads are checked by automated moderation. Tanvo does not sell personal data.

## Retention and deletion

Tanvo keeps your runs (prompts, inputs and results) in your account history until you delete them or your account; deleted files are removed from storage within 30 days. To stop all transmission, remove the credential in Dify or revoke the key at https://tanvo.ai/settings/apikeys.

## Contact

support@tanvo.ai

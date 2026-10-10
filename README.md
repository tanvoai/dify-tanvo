# Tanvo for Dify

Generate images, videos and songs from Dify workflows, chatflows and agents with [Tanvo](https://tanvo.ai/?utm_source=dify&utm_medium=referral): Nano Banana, Seedream, GPT Image, Qwen and Grok Imagine for images; Kling, Veo, Seedance, Wan, LTX and MiniMax for video, most with sound; Suno V6 for songs. Or run one of Tanvo's 80 ready-made apps (pet portraits, figurines, old photo restoration, tattoo designs, trend videos, birthday songs) with the same tuned looks as the website.

Source: https://github.com/tanvoai/dify-tanvo

## Tools

| Tool | What it does |
|---|---|
| Generate Image | Text to image, or edit and combine reference images |
| Generate Video | Text to video, or animate a start image, with an optional end image and sound |
| Generate Song | A song in two takes: describe it, sing your own lyrics, or go instrumental |
| Run App | One of Tanvo's apps with a preset look, on your photos or clips |
| List Apps | Every app with its looks and the photos it needs (for agents, before Run App) |
| Get Generation | The status and files of a run started earlier |

Every tool returns the files (as Dify files), a JSON summary, and the variables `generation_id`, `status` and `urls`.

## Setup

1. Sign in at [tanvo.ai](https://tanvo.ai/?utm_source=dify&utm_medium=referral). New accounts start with free credits.
2. Create an API key under [Settings, API keys](https://tanvo.ai/settings/apikeys?utm_source=dify&utm_medium=referral).
3. In Dify, install Tanvo from the Marketplace, open **Tools → Tanvo → Authorize**, paste the key and save. The key is checked with a free call.

## Usage

- **Workflow**: add a Tanvo tool node, pass the prompt (and any files from a Start node or an earlier node), and choose the model and settings in the node. Use the `files` output in later nodes or the End node.
- **Agent**: add the tools; the agent writes the prompt. For apps it can call List Apps first.
- **Settings**: "Model default" leaves a setting to the model. Not every model takes every aspect ratio, resolution or length; if one does not, the error lists what it accepts.
- **Long videos**: tools wait up to `wait_seconds` (at most 240). If a video is not done by then, the tool returns `status` and `generation_id`; call Get Generation with that id to fetch it.

Runs use your Tanvo credits at the same prices as the website (the model list shows the cost at default settings). Failed runs cost nothing.

## Connection requirements

The Dify server needs outbound HTTPS (port 443) to `tanvo.ai`, `media.tanvo.ai` and Cloudflare R2 (`*.r2.cloudflarestorage.com`, for uploading input files). To pass input files, the plugin must be able to read them from Dify, so self-hosted Dify needs `FILES_URL` set.

## Privacy

Prompts, settings and attached files are sent to Tanvo to generate the results; the plugin stores nothing itself. See [PRIVACY.md](PRIVACY.md) and https://tanvo.ai/privacy-policy.

## Support

Issues: https://github.com/tanvoai/dify-tanvo/issues, or support@tanvo.ai.

Also from Tanvo: the [ComfyUI nodes](https://github.com/tanvoai/ComfyUI-Tanvo), the [n8n node](https://github.com/tanvoai/n8n-nodes-tanvo), the [MCP server](https://github.com/tanvoai/tanvo-mcp) and the [Python](https://github.com/tanvoai/tanvo-python) and [JavaScript](https://github.com/tanvoai/tanvo-js) clients.

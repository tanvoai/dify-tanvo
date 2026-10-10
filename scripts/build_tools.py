"""Writes tools/*.yaml from Tanvo's live model catalogue, so the model lists and their settings stay current:
python scripts/build_tools.py   (needs `tanvo` and `pyyaml`)"""
from __future__ import annotations

import sys
from pathlib import Path

import tanvo
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKIP_INPUTS = {"audio"}  # models that need an audio track (talking avatars) are not offered yet


def t(en: str, zh: str | None = None) -> dict:
    return {"en_US": en, "zh_Hans": zh or en}


def param(name, type_, label, human, *, form="form", required=False, llm=None, **extra) -> dict:
    p = {"name": name, "type": type_, "required": required, "form": form, "label": label, "human_description": human}
    if llm:
        p["llm_description"] = llm
    p.update(extra)
    return p


def select(name, label, human, values, default="auto", labels=None, **kw) -> dict:
    opts = [{"value": str(v), "label": t((labels or {}).get(v, str(v)))} for v in values]
    return param(name, "select", label, human, options=opts, default=str(default), **kw)


def union(models, key) -> list:
    seen = []
    for m in models:
        for v in m.options.get(key) or []:
            if v not in seen:
                seen.append(v)
    return seen


def model_select(models, default) -> dict:
    labels = {m.id: f"{m.name} (about {m.credits_at_defaults} credits)" for m in models}
    return select("model", t("Model", "模型"), t("Which model to run. Prices are in credits at the model's default settings.", "用哪个模型。价格是默认设置下的积分。"),
                  [m.id for m in models], default=default, labels=labels)


def wait_param() -> dict:
    return param("wait_seconds", "number", t("Wait (seconds)", "等待（秒）"),
                 t("How long to wait for the result, up to 240. If the run is still going, the tool returns its generation_id for Get Generation.",
                   "最多等多久，最长 240 秒。还没完成就返回 generation_id，之后用 Get Generation 取结果。"),
                 default=240, min=0, max=240)


def tool(name, label, human, llm, params) -> dict:
    return {
        "identity": {"name": name, "author": "tanvo", "label": label},
        "description": {"human": human, "llm": llm},
        "parameters": params,
        "extra": {"python": {"source": f"tools/{name}.py"}},
    }


def main() -> None:
    c = tanvo.Client()  # the catalogue needs no key
    images = [m for m in c.models("image")]
    videos = [m for m in c.models("video") if not SKIP_INPUTS & set(m.inputs)]
    auto = t("Model default", "模型默认")

    def settings(models, key, label, human):
        values = ["auto"] + union(models, key)
        return select(key, label, human, values, labels={"auto": auto["en_US"]})

    tools = {
        "generate_image": tool(
            "generate_image", t("Generate Image", "生成图片"),
            t("Text to image, or edit and combine images, on Nano Banana, Seedream, GPT Image, Qwen and Grok Imagine.", "文生图，或编辑、合成图片。"),
            "Generates or edits an image with Tanvo. Give a detailed prompt; pass reference images to edit or combine them. Returns the image files, their URLs and a generation_id.",
            [
                param("prompt", "string", t("Prompt", "提示词"), t("What to make, or what to change in the images.", "要生成什么，或要怎么改图。"), form="llm", required=True,
                      llm="A detailed description of the image, or of the edit to make to the reference images."),
                param("images", "files", t("Reference images", "参考图"), t("Optional images to edit or combine.", "可选：要编辑或合成的图片。"), form="llm",
                      llm="Optional images to edit or combine, in order."),
                model_select(images, "nano-banana-2"),
                settings(images, "aspect", t("Aspect ratio", "画面比例"), t("Not every model takes every ratio; the error lists the ones it does.", "不是每个模型都支持所有比例，报错会列出支持的。")),
                settings(images, "resolution", t("Resolution", "分辨率"), t("Output resolution.", "输出分辨率。")),
                settings(images, "format", t("Format", "格式"), t("File format.", "文件格式。")),
                wait_param(),
            ],
        ),
        "generate_video": tool(
            "generate_video", t("Generate Video", "生成视频"),
            t("Text to video, or animate a start frame (with an optional end frame), on Kling, Veo, Seedance, Wan, LTX and MiniMax, most with sound.", "文生视频，或让首帧动起来（可设尾帧），多数模型带声音。"),
            "Generates a short video with Tanvo from a prompt describing the shot (subject, action, camera, sound), optionally starting from an image. Videos take one to several minutes: if status is not SUCCEEDED, call Get Generation with the generation_id. A successful submission is not a finished video.",
            [
                param("prompt", "string", t("Prompt", "提示词"), t("The shot: subject, action, camera and sound.", "镜头：主体、动作、运镜和声音。"), form="llm", required=True,
                      llm="The shot to generate: subject, action, camera movement, lighting and sound."),
                param("start_image", "file", t("Start image", "首帧"), t("Optional image to animate.", "可选：让这张图动起来。"), form="llm", llm="Optional image the video starts from."),
                param("end_image", "file", t("End image", "尾帧"), t("Optional image to end on (models that support it).", "可选：结束画面（部分模型支持）。"), form="llm"),
                model_select(videos, "kling-3-0"),
                settings(videos, "aspect", t("Aspect ratio", "画面比例"), t("Not every model takes every ratio.", "不是每个模型都支持所有比例。")),
                settings(videos, "resolution", t("Resolution", "分辨率"), t("Output resolution.", "输出分辨率。")),
                param("duration", "number", t("Duration (seconds)", "时长（秒）"), t("Leave empty for the model's default; each model takes a few fixed lengths.", "留空用模型默认；每个模型只支持几种固定时长。"),
                      min=3, max=30),
                select("audio", t("Sound", "声音"), t("Sound with the video, on models that can make it. Model default is on for most.", "是否带声音（部分模型支持）。"),
                       ["auto", "on", "off"], labels={"auto": auto["en_US"], "on": "On", "off": "Off"}),
                select("tier", t("Quality tier", "质量档位"), t("Veo 3.1 only: Lite, Fast or Quality.", "仅 Veo 3.1：Lite、Fast 或 Quality。"), ["auto"] + union(videos, "tier"), labels={"auto": auto["en_US"]}),
                wait_param(),
            ],
        ),
        "generate_song": tool(
            "generate_song", t("Generate Song", "生成歌曲"),
            t("A song in two takes on Suno V6: describe it, sing your own lyrics, or go instrumental.", "用 Suno V6 写歌，两个版本：描述、自己的歌词或纯音乐。"),
            "Generates a song with Tanvo (two takes). In Describe mode the prompt describes the song (who it is for, mood, details); in Lyrics mode the prompt is the lyrics to sing. Returns the audio files, titles, lyrics and a generation_id.",
            [
                param("prompt", "string", t("Prompt", "提示词"), t("The song, or its lyrics in Lyrics mode.", "歌曲描述，Lyrics 模式下是歌词。"), form="llm", required=True,
                      llm="What the song is about and for whom, or the full lyrics in Lyrics mode."),
                select("mode", t("Mode", "模式"), t("Describe: the prompt describes the song. Lyrics: the prompt is the lyrics. Instrumental: no vocals.", "Describe：描述歌曲。Lyrics：提示词就是歌词。Instrumental：纯音乐。"),
                       ["Describe", "Lyrics", "Instrumental"], default="Describe"),
                param("style", "string", t("Style", "风格"), t("Genre, instruments and voice, e.g. acoustic pop, hand claps, warm female vocal.", "曲风、乐器和人声。"), form="llm",
                      llm="Optional genre, instruments and voice."),
                param("title", "string", t("Title", "标题"), t("Optional song title.", "可选：歌名。"), form="llm"),
                wait_param(),
            ],
        ),
        "run_app": tool(
            "run_app", t("Run App", "运行应用"),
            t("Run one of Tanvo's ready-made apps (pet portraits, figurines, old photo restoration, tattoo designs, trend videos, birthday songs) with its tuned preset looks.", "运行 Tanvo 的现成应用（宠物肖像、手办、老照片修复、纹身设计、热门视频、生日歌），用调好的预设风格。"),
            "Runs a Tanvo app on the given photos with one of its preset looks. Use List Apps first to find the app id, its looks and how many photos it needs. Put names and personal details in details.",
            [
                param("app", "string", t("App", "应用"), t("The app id, e.g. ai-pet-portrait-generator. List Apps shows them all.", "应用 id，例如 ai-pet-portrait-generator。List Apps 会列出全部。"),
                      form="llm", required=True, llm="The app id from List Apps, e.g. ai-pet-portrait-generator."),
                param("look", "string", t("Look", "风格"), t("The look id, e.g. royal. Empty uses the app's first look.", "风格 id，例如 royal。留空用第一个。"), form="llm",
                      llm="Optional look id from List Apps; empty means the app's first look."),
                param("photos", "files", t("Photos", "照片"), t("The photos (or clips) the app asks for, in order.", "应用需要的照片（或视频片段），按顺序。"), form="llm",
                      llm="The photos or video clips the app needs, in the order List Apps gives."),
                param("details", "string", t("Details", "补充信息"), t("Optional: who or what it is for, e.g. a name or an inside joke.", "可选：给谁做的，比如名字、梗。"), form="llm",
                      llm="Optional personal details to include, such as a name."),
                wait_param(),
            ],
        ),
        "list_apps": tool(
            "list_apps", t("List Apps", "应用列表"),
            t("Tanvo's ready-made apps with their looks and the photos each needs.", "Tanvo 的现成应用、风格和需要的照片。"),
            "Lists Tanvo apps: id, kind (image, video or music), what it does, the photos it needs and its preset looks. Use before Run App.",
            [select("kind", t("Kind", "类型"), t("Which apps to list.", "列出哪类应用。"), ["all", "image", "video", "music"], default="all", form="llm",
                    llm="Optional: image, video, music or all.")],
        ),
        "get_generation": tool(
            "get_generation", t("Get Generation", "获取生成结果"),
            t("The status and files of a run started earlier, waiting for it to finish if needed.", "查询之前的运行状态和文件，必要时等待完成。"),
            "Fetches a Tanvo run by generation_id, waiting up to wait_seconds for it to finish. Use it when a generate tool returned a status other than SUCCEEDED.",
            [
                param("generation_id", "string", t("Generation ID", "生成 ID"), t("The generation_id a generate tool returned.", "生成工具返回的 generation_id。"),
                      form="llm", required=True, llm="The generation_id returned earlier."),
                wait_param(),
            ],
        ),
    }
    for name, data in tools.items():
        (ROOT / "tools" / f"{name}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=200))
    print(f"{len(images)} image models, {len(videos)} video models -> tools/*.yaml", file=sys.stderr)


if __name__ == "__main__":
    main()

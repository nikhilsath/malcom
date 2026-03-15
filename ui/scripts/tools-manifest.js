export const toolsManifest = Object.freeze([
  {
    "id": "convert-audio",
    "name": "Convert - Audio",
    "description": "Convert audio files between supported formats for downstream processing.",
    "pageHref": "tools/convert-audio.html"
  },
  {
    "id": "convert-video",
    "name": "Convert - Video",
    "description": "Convert video files into delivery-ready formats for automation pipelines.",
    "pageHref": "tools/convert-video.html"
  },
  {
    "id": "grafana",
    "name": "Grafana",
    "description": "Open-source dashboards and reporting for operational logs, with room to wire retained events into richer incident and trend reports.",
    "pageHref": "tools/grafana.html"
  },
  {
    "id": "llm-deepl",
    "name": "Local LLM",
    "description": "Run a locally hosted language model through configurable OpenAI-compatible or LM Studio endpoints.",
    "pageHref": "tools/llm-deepl.html"
  },
  {
    "id": "ocr-transcribe",
    "name": "OCR/Transcribe",
    "description": "Extract text from images and transcribe spoken content into structured output.",
    "pageHref": "tools/ocr-transcribe.html"
  },
  {
    "id": "smtp",
    "name": "SMTP",
    "description": "Run an SMTP listener on the selected machine so automations can accept email traffic.",
    "pageHref": "tools/smtp.html"
  }
]);

if (typeof window !== "undefined") {
  window.TOOLS_MANIFEST = toolsManifest;
}

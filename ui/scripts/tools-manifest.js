export const toolsManifest = Object.freeze([
  {
    "id": "convert-audio",
    "name": "Convert - Audio",
    "description": "Convert audio files between formats using a locally installed ffmpeg runtime.",
    "pageHref": "tools/convert-audio.html",
    "inputs": [
      {
        "key": "input_file",
        "label": "Input File Path",
        "type": "string",
        "required": true
      },
      {
        "key": "output_format",
        "label": "Output Format",
        "type": "select",
        "required": true,
        "options": [
          "mp3",
          "wav",
          "ogg",
          "flac",
          "aac",
          "m4a"
        ]
      },
      {
        "key": "output_filename",
        "label": "Output Filename",
        "type": "string",
        "required": false
      }
    ],
    "outputs": [
      {
        "key": "output_file_path",
        "label": "Output File Path",
        "type": "string"
      }
    ]
  },
  {
    "id": "coqui-tts",
    "name": "Coqui TTS",
    "description": "Generate speech audio from workflow text using a locally installed Coqui TTS runtime.",
    "pageHref": "tools/coqui-tts.html",
    "inputs": [
      {
        "key": "text",
        "label": "Text to Speak",
        "type": "text",
        "required": true
      },
      {
        "key": "output_filename",
        "label": "Output Filename",
        "type": "string",
        "required": false
      },
      {
        "key": "speaker",
        "label": "Speaker Override",
        "type": "string",
        "required": false
      },
      {
        "key": "language",
        "label": "Language Override",
        "type": "string",
        "required": false
      }
    ],
    "outputs": [
      {
        "key": "audio_file_path",
        "label": "Audio File Path",
        "type": "string"
      }
    ]
  },
  {
    "id": "llm-deepl",
    "name": "Local LLM",
    "description": "Run a locally hosted language model through configurable OpenAI-compatible or LM Studio endpoints.",
    "pageHref": "tools/llm-deepl.html",
    "inputs": [
      {
        "key": "system_prompt",
        "label": "System Prompt",
        "type": "text",
        "required": false
      },
      {
        "key": "user_prompt",
        "label": "User Prompt",
        "type": "text",
        "required": true
      },
      {
        "key": "model_identifier",
        "label": "Model Identifier Override",
        "type": "string",
        "required": false
      }
    ],
    "outputs": [
      {
        "key": "response_text",
        "label": "Response Text",
        "type": "string"
      },
      {
        "key": "model_used",
        "label": "Model Used",
        "type": "string"
      }
    ]
  },
  {
    "id": "smtp",
    "name": "SMTP",
    "description": "Send an email through an external SMTP relay from within a workflow step.",
    "pageHref": "tools/smtp.html",
    "inputs": [
      {
        "key": "relay_host",
        "label": "Relay Host",
        "type": "string",
        "required": true
      },
      {
        "key": "relay_port",
        "label": "Relay Port",
        "type": "number",
        "required": true
      },
      {
        "key": "relay_security",
        "label": "Security",
        "type": "select",
        "required": false,
        "options": [
          "none",
          "starttls",
          "tls"
        ]
      },
      {
        "key": "relay_username",
        "label": "Username",
        "type": "string",
        "required": false
      },
      {
        "key": "relay_password",
        "label": "Password",
        "type": "string",
        "required": false
      },
      {
        "key": "from_address",
        "label": "From Address",
        "type": "string",
        "required": true
      },
      {
        "key": "to",
        "label": "To",
        "type": "string",
        "required": true
      },
      {
        "key": "subject",
        "label": "Subject",
        "type": "string",
        "required": true
      },
      {
        "key": "body",
        "label": "Body",
        "type": "text",
        "required": true
      }
    ],
    "outputs": [
      {
        "key": "status",
        "label": "Status",
        "type": "string"
      },
      {
        "key": "message",
        "label": "Message",
        "type": "string"
      }
    ]
  }
]);

if (typeof window !== "undefined") {
  window.TOOLS_MANIFEST = toolsManifest;
}

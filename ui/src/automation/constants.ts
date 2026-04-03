import type { TriggerType } from "./types";

export const AUTOMATION_TRIGGER_LABELS: Record<TriggerType, string> = {
  manual: "Manual",
  schedule: "Schedule",
  inbound_api: "Inbound API",
  smtp_email: "SMTP email"
};

export const SCRIPT_LANGUAGE_LABELS: Record<"python" | "javascript", string> = {
  python: "Python",
  javascript: "JavaScript"
};

export const SCRIPT_LANGUAGE_TEMPLATES: Record<"python" | "javascript", string> = {
  python: [
    "def run(context, script_input=None):",
    "    payload = context.get('payload', {})",
    "    return script_input or payload",
    ""
  ].join("\n"),
  javascript: [
    "function run(context, scriptInput) {",
    "  const payload = context?.payload ?? {};",
    "  return scriptInput || payload;",
    "}",
    ""
  ].join("\n")
};

export const AUTOMATION_PROMPT_TOKEN_TARGET_OPTIONS = [
  { value: "user", label: "User prompt" },
  { value: "system", label: "System prompt" }
] as const;

export const GOOGLE_SERVICE_ORDER = ["gmail", "drive", "calendar", "sheets"] as const;

export const GOOGLE_SERVICE_LABELS: Record<string, string> = {
  gmail: "Gmail",
  drive: "Drive",
  calendar: "Calendar",
  sheets: "Sheets"
};

export const SMTP_TEMPLATE_HINTS = [
  "{{payload.smtp.from}}",
  "{{payload.smtp.to}}",
  "{{payload.smtp.subject}}",
  "{{payload.smtp.body}}"
];

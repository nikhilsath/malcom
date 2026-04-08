import { describe, expect, it } from "vitest";
import { buildDataFlowTokens } from "../data-flow";
import type { AutomationStep, ConnectorActivityDefinition, ScriptLibraryItem, ToolManifestEntry } from "../types";

const toolsManifest: ToolManifestEntry[] = [
  {
    id: "smtp",
    name: "SMTP",
    description: "Send mail",
    pageHref: "tools/smtp.html",
    inputs: [],
    outputs: [
      { key: "status", label: "Status", type: "string" },
      { key: "message", label: "Message", type: "string" }
    ]
  }
];

const connectorActivityCatalog: ConnectorActivityDefinition[] = [
  {
    provider_id: "google",
    activity_id: "gmail_send_email",
    service: "gmail",
    operation_type: "write",
    label: "Send email",
    description: "Send an email",
    required_scopes: [],
    input_schema: [],
    output_schema: [
      { key: "message_id", label: "Message ID", type: "string" }
    ],
    execution: {}
  }
];

const scriptLibrary: ScriptLibraryItem[] = [
  {
    id: "script_seed_change_delimiter",
    name: "Change Delimiter",
    description: "Split text on one delimiter and join it with another.",
    language: "python",
    sample_input: "{}",
    expected_output: JSON.stringify({ text: "Transformed text.", line_count: "Number of lines.", from: "Source delimiter.", to: "Target delimiter." })
  },
  {
    id: "script_no_output",
    name: "No Output Script",
    description: "Returns nothing declared.",
    language: "python",
    sample_input: "{}",
    expected_output: "{}"
  }
];

describe("buildDataFlowTokens", () => {
  it("returns baseline workflow tokens", () => {
    const tokens = buildDataFlowTokens([], null, toolsManifest, connectorActivityCatalog);
    const values = tokens.map((token) => token.token);
    expect(values).toContain("{{automation.id}}");
    expect(values).toContain("{{automation.name}}");
    expect(values).toContain("{{timestamp}}");
    expect(values).toContain("{{payload}}");
  });

  it("includes prior step outputs and excludes current step outputs", () => {
    const steps: AutomationStep[] = [
      {
        id: "step-http",
        type: "outbound_request",
        name: "HTTP fetch",
        config: {
          response_mappings: [
            { key: "customer_id", path: "data.customer.id" }
          ]
        }
      },
      {
        id: "step-tool",
        type: "tool",
        name: "SMTP notify",
        config: { tool_id: "smtp", tool_inputs: {} }
      },
      {
        id: "step-connector",
        type: "connector_activity",
        name: "Send via connector",
        config: { activity_id: "gmail_send_email", activity_inputs: {} }
      }
    ];

    const tokens = buildDataFlowTokens(steps, "step-tool", toolsManifest, connectorActivityCatalog);
    const values = tokens.map((token) => token.token);

    expect(values).toContain("{{steps.step-http.customer_id}}");
    expect(values).toContain("{{steps.step-http.response_body_json}}");
    expect(values).not.toContain("{{steps.step-tool.status}}");
    expect(values).not.toContain("{{steps.step-connector.message_id}}");
  });

  it("generates specific tokens for script steps with expected_output", () => {
    const steps: AutomationStep[] = [
      {
        id: "step-script",
        type: "script",
        name: "Change delimiter step",
        config: { script_id: "script_seed_change_delimiter", script_input_template: "" }
      },
      {
        id: "step-next",
        type: "log",
        name: "Write result",
        config: {}
      }
    ];

    const tokens = buildDataFlowTokens(steps, "step-next", toolsManifest, connectorActivityCatalog, scriptLibrary);
    const values = tokens.map((token) => token.token);

    expect(values).toContain("{{steps.step-script.text}}");
    expect(values).toContain("{{steps.step-script.line_count}}");
    expect(values).toContain("{{steps.step-script.from}}");
    expect(values).toContain("{{steps.step-script.to}}");
    expect(values).not.toContain("{{steps.step-script.result}}");
  });

  it("only emits base token for script steps with empty expected_output", () => {
    const steps: AutomationStep[] = [
      {
        id: "step-script",
        type: "script",
        name: "No output script",
        config: { script_id: "script_no_output", script_input_template: "" }
      },
      {
        id: "step-next",
        type: "log",
        name: "Write result",
        config: {}
      }
    ];

    const tokens = buildDataFlowTokens(steps, "step-next", toolsManifest, connectorActivityCatalog, scriptLibrary);
    const values = tokens.map((token) => token.token);

    expect(values).toContain("{{steps.step-script}}");
    // No field-specific tokens beyond the base
    const scriptFieldTokens = values.filter((v) => v.startsWith("{{steps.step-script."));
    expect(scriptFieldTokens).toHaveLength(0);
  });

  it("falls back to base token when script is not in library", () => {
    const steps: AutomationStep[] = [
      {
        id: "step-script",
        type: "script",
        name: "Unknown script",
        config: { script_id: "script_unknown_id", script_input_template: "" }
      },
      {
        id: "step-next",
        type: "log",
        name: "Next step",
        config: {}
      }
    ];

    const tokens = buildDataFlowTokens(steps, "step-next", toolsManifest, connectorActivityCatalog, scriptLibrary);
    const values = tokens.map((token) => token.token);

    expect(values).toContain("{{steps.step-script}}");
    const scriptFieldTokens = values.filter((v) => v.startsWith("{{steps.step-script."));
    expect(scriptFieldTokens).toHaveLength(0);
  });
});

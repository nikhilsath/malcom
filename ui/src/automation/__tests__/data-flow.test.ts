import { describe, expect, it } from "vitest";
import { buildDataFlowTokens } from "../data-flow";
import type { AutomationStep, ConnectorActivityDefinition, ToolManifestEntry } from "../types";

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
});

export const CONNECTORS_APIS_STATE_KEY = "malcom.playwright.connectors-apis";

export const cloneJson = <T>(value: T): T => JSON.parse(JSON.stringify(value));

export const mergeJson = (base: Record<string, unknown>, override: Record<string, unknown>) => {
  const output = cloneJson(base);

  for (const [key, value] of Object.entries(override)) {
    if (Array.isArray(value)) {
      output[key] = cloneJson(value);
      continue;
    }

    if (value && typeof value === "object" && !Array.isArray(value)) {
      const baseValue = output[key];
      output[key] = mergeJson(
        (baseValue && typeof baseValue === "object" && !Array.isArray(baseValue)) ? baseValue as Record<string, unknown> : {},
        value as Record<string, unknown>
      );
      continue;
    }

    output[key] = value;
  }

  return output;
};

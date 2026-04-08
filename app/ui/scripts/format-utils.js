export const formatDateTime = (value, fallback = "Never") => {
  if (!value) {
    return fallback;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return fallback;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
};

export const formatIntervalMinutes = (value) => {
  if (!value) {
    return "Not set";
  }

  if (value % 60 === 0) {
    const hours = value / 60;
    return `${hours} ${hours === 1 ? "hour" : "hours"}`;
  }

  return `${value} ${value === 1 ? "minute" : "minutes"}`;
};

export const formatSize = (value) => {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "Unknown";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  return `${(value / 1024).toFixed(1)} KB`;
};

/**
 * Creates a lazy-loading element map from a key-to-id mapping.
 * Each property is resolved via getElementById on first access and cached,
 * avoiding 60+ eager DOM queries at module load time.
 *
 * @param {Record<string, string>} idMap - Object mapping property names to element IDs
 * @returns {Record<string, Element | null>} Proxy object with lazy element resolution
 */
export const createElementMap = (idMap) => {
  const cache = Object.create(null);
  return new Proxy(Object.create(null), {
    get(target, key) {
      if (typeof key !== "string" || !(key in idMap)) {
        return undefined;
      }
      if (!(key in cache)) {
        cache[key] = document.getElementById(idMap[key]);
      }
      return cache[key];
    },
    has(target, key) {
      return key in idMap;
    }
  });
};

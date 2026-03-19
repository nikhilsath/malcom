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

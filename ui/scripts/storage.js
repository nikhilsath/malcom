const storageForm = document.getElementById("tools-storage-form");
const storageTypeInputs = Array.from(document.querySelectorAll('input[name="storageType"]'));
const storageSyncInput = document.getElementById("tools-storage-sync-input");
const storageNameInput = document.getElementById("tools-storage-name-input");
const storageLocalSection = document.getElementById("tools-storage-local-section");
const storageCloudSection = document.getElementById("tools-storage-cloud-section");
const storageCloudProviderInput = document.getElementById("tools-storage-cloud-provider-input");
const storageCloudEndpointField = document.getElementById("tools-storage-cloud-endpoint-field");
const storageValidateButton = document.getElementById("tools-storage-validate-button");
const storageFeedback = document.getElementById("tools-storage-form-feedback");

const storageOverviewStatusValue = document.getElementById("tools-storage-overview-status-value");
const storageOverviewStatusCopy = document.getElementById("tools-storage-overview-status-copy");
const storageSummaryTargetValue = document.getElementById("tools-storage-summary-target-value");
const storageSummaryProviderValue = document.getElementById("tools-storage-summary-provider-value");
const storageSummarySyncValue = document.getElementById("tools-storage-summary-sync-value");

const storagePreviewNameValue = document.getElementById("tools-storage-preview-name-value");
const storagePreviewTargetValue = document.getElementById("tools-storage-preview-target-value");
const storagePreviewLocationValue = document.getElementById("tools-storage-preview-location-value");
const storagePreviewTransferValue = document.getElementById("tools-storage-preview-transfer-value");
const storagePreviewAccessValue = document.getElementById("tools-storage-preview-access-value");

const storageLocalPathInput = document.getElementById("tools-storage-local-path-input");
const storageLocalReadOnlyInput = document.getElementById("tools-storage-local-readonly-input");
const storageCloudBucketInput = document.getElementById("tools-storage-cloud-bucket-input");
const storageCloudPrefixInput = document.getElementById("tools-storage-cloud-prefix-input");
const storageCloudRegionInput = document.getElementById("tools-storage-cloud-region-input");

const toTitleCase = (value) => value
  .split("-")
  .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
  .join(" ");

const setFeedback = (message, tone = "") => {
  storageFeedback.textContent = message;
  storageFeedback.className = tone
    ? `api-form-feedback api-form-feedback--${tone}`
    : "api-form-feedback";
};

const getStorageType = () => {
  const selectedInput = storageTypeInputs.find((input) => input.checked);
  return selectedInput ? selectedInput.value : "local";
};

const getProviderLabel = () => {
  const storageType = getStorageType();

  if (storageType === "local") {
    return "Filesystem";
  }

  const selectedOption = storageCloudProviderInput.options[storageCloudProviderInput.selectedIndex];
  return selectedOption ? selectedOption.textContent : "Cloud storage";
};

const syncVisibility = () => {
  const storageType = getStorageType();
  const useCloudStorage = storageType === "cloud";
  const useCustomEndpoint = useCloudStorage && storageCloudProviderInput.value === "custom";

  storageLocalSection.hidden = useCloudStorage;
  storageCloudSection.hidden = !useCloudStorage;
  storageCloudEndpointField.hidden = !useCustomEndpoint;
};

const syncSummary = () => {
  const storageType = getStorageType();
  const providerLabel = getProviderLabel();
  const transferModeLabel = toTitleCase(storageSyncInput.value);

  storageOverviewStatusValue.textContent = storageType === "cloud" ? "Cloud storage" : "Local storage";
  storageOverviewStatusCopy.textContent = storageType === "cloud"
    ? "Connect an external storage provider and use a bucket, container, or endpoint as the automation input."
    : "Accept files from a path on this instance and stage them for retention or sync.";

  storageSummaryTargetValue.textContent = storageType === "cloud" ? "Cloud" : "Local";
  storageSummaryProviderValue.textContent = providerLabel;
  storageSummarySyncValue.textContent = transferModeLabel;

  storagePreviewNameValue.textContent = storageNameInput.value.trim() || "Untitled storage input";
  storagePreviewTargetValue.textContent = storageType === "cloud" ? providerLabel : "Local filesystem";
  storagePreviewLocationValue.textContent = storageType === "cloud"
    ? `${storageCloudBucketInput.value.trim() || "bucket"}/${storageCloudPrefixInput.value.trim() || ""} (${storageCloudRegionInput.value.trim() || "region unset"})`
    : storageLocalPathInput.value.trim() || "Path not set";
  storagePreviewTransferValue.textContent = transferModeLabel;
  storagePreviewAccessValue.textContent = storageType === "cloud"
    ? "Credentialed access"
    : storageLocalReadOnlyInput.checked ? "Read only" : "Read / write";
};

const validateStorageForm = () => {
  const storageType = getStorageType();

  if (!storageNameInput.value.trim()) {
    return "Connection name is required.";
  }

  if (storageType === "local" && !storageLocalPathInput.value.trim()) {
    return "Local path is required for local storage.";
  }

  if (storageType === "cloud" && !storageCloudBucketInput.value.trim()) {
    return "Bucket or container is required for cloud storage.";
  }

  if (storageType === "cloud" && storageCloudProviderInput.value === "custom") {
    const cloudEndpointInput = document.getElementById("tools-storage-cloud-endpoint-input");

    if (!cloudEndpointInput.value.trim()) {
      return "Custom endpoint URL is required for a custom cloud provider.";
    }
  }

  return "";
};

const handleStorageFormUpdate = () => {
  syncVisibility();
  syncSummary();
  setFeedback("");
};

storageTypeInputs.forEach((input) => {
  input.addEventListener("change", handleStorageFormUpdate);
});

storageSyncInput.addEventListener("change", handleStorageFormUpdate);
storageNameInput.addEventListener("input", handleStorageFormUpdate);
storageLocalPathInput.addEventListener("input", handleStorageFormUpdate);
storageLocalReadOnlyInput.addEventListener("change", handleStorageFormUpdate);
storageCloudProviderInput.addEventListener("change", handleStorageFormUpdate);
storageCloudBucketInput.addEventListener("input", handleStorageFormUpdate);
storageCloudPrefixInput.addEventListener("input", handleStorageFormUpdate);
storageCloudRegionInput.addEventListener("input", handleStorageFormUpdate);

storageValidateButton.addEventListener("click", () => {
  const validationError = validateStorageForm();

  if (validationError) {
    setFeedback(validationError, "error");
    return;
  }

  setFeedback("Connection details look complete for the selected storage type.", "success");
});

storageForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const validationError = validateStorageForm();

  if (validationError) {
    setFeedback(validationError, "error");
    return;
  }

  syncSummary();
  setFeedback("Storage input saved to the current workspace preview.", "success");
});

syncVisibility();
syncSummary();

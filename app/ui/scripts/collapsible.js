export const bindCollapsibleSection = ({
  toggleId,
  bodyId,
  symbolId,
  srLabelId,
  expandedLabel,
  collapsedLabel,
  expandedSymbol = "-",
  collapsedSymbol = "+",
  onExpand,
  onCollapse,
  onToggle
}) => {
  const toggle = document.getElementById(toggleId);
  const body = document.getElementById(bodyId);
  const symbol = document.getElementById(symbolId);
  const srLabel = srLabelId ? document.getElementById(srLabelId) : null;

  if (!(toggle instanceof HTMLButtonElement) || !(body instanceof HTMLElement) || !(symbol instanceof HTMLElement)) {
    return null;
  }

  const applyState = (expanded) => {
    toggle.setAttribute("aria-expanded", String(expanded));
    body.hidden = !expanded;
    symbol.textContent = expanded ? expandedSymbol : collapsedSymbol;

    if (expandedLabel && collapsedLabel) {
      const nextLabel = expanded ? expandedLabel : collapsedLabel;
      toggle.setAttribute("aria-label", nextLabel);
      if (srLabel instanceof HTMLElement) {
        srLabel.textContent = nextLabel;
      }
    }
  };

  const getExpandedState = () => toggle.getAttribute("aria-expanded") === "true";

  const handleToggle = () => {
    const nextExpanded = !getExpandedState();
    applyState(nextExpanded);
    if (nextExpanded) {
      onExpand?.();
    } else {
      onCollapse?.();
    }
    onToggle?.(nextExpanded);
  };

  const initialExpanded = body.hidden ? false : getExpandedState();
  applyState(initialExpanded);
  toggle.addEventListener("click", handleToggle);

  return {
    get expanded() {
      return getExpandedState();
    },
    setExpanded(nextExpanded) {
      applyState(nextExpanded);
    },
    destroy() {
      toggle.removeEventListener("click", handleToggle);
    }
  };
};

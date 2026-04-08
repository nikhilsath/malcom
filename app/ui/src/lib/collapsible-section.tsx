import { useState } from "react";
import type { ReactNode } from "react";

type CollapsibleSectionClasses = {
  section?: string;
  sectionCollapsed?: string;
  toggle?: string;
  label?: string;
  symbol?: string;
  body?: string;
  bodyCollapsed?: string;
};

export type CollapsibleSectionProps = {
  id: string;
  label: string;
  children: ReactNode;
  defaultCollapsed?: boolean;
  description?: string;
  classes?: CollapsibleSectionClasses;
};

const mergeClassNames = (...values: Array<string | undefined | false>) => values.filter(Boolean).join(" ");

export const CollapsibleSection = ({
  id,
  label,
  children,
  defaultCollapsed = false,
  classes
}: CollapsibleSectionProps) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const collapseLabel = collapsed ? `Expand ${label}` : `Collapse ${label}`;

  return (
    <section
      id={id}
      className={mergeClassNames(
        classes?.section || "card",
        collapsed && classes?.sectionCollapsed
      )}
    >
      <button
        id={`${id}-collapse-toggle`}
        type="button"
        className={classes?.toggle || "section-collapse-top-strip"}
        aria-expanded={!collapsed}
        aria-controls={`${id}-body`}
        aria-label={collapseLabel}
        onClick={() => setCollapsed((current) => !current)}
      >
        <span id={`${id}-collapse-top-label`} className={classes?.label || "section-collapse-top-strip__label"}>
          {label}
        </span>
        <span id={`${id}-collapse-symbol`} className={classes?.symbol || "section-collapse-top-strip__symbol"} aria-hidden="true">
          {collapsed ? "+" : "-"}
        </span>
        <span id={`${id}-collapse-label`} className="sr-only">
          {collapseLabel}
        </span>
      </button>
      <div
        id={`${id}-body`}
        className={mergeClassNames(classes?.body, collapsed && classes?.bodyCollapsed)}
        hidden={collapsed}
      >
        {children}
      </div>
    </section>
  );
};

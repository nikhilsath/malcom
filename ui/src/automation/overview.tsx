import React from 'react';

type Automation = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger_type: string;
  step_count: number;
};

type AutomationOverviewPageProps = {
  automations: Automation[];
  onSelectAutomation: (automationId: string) => void;
  onCreateAutomation: () => void;
};

export const AutomationOverviewPage = ({
  automations,
  onSelectAutomation,
  onCreateAutomation,
}: AutomationOverviewPageProps) => {
  return (
    <div className="automation-overview">
      <div className="page-header">
        <h2 className="page-title">Automations Overview</h2>
        <p className="page-description">
          Monitor your automations and create new ones.
        </p>
        <div className="header-actions">
          <button
            className="primary-action-button"
            onClick={onCreateAutomation}
          >
            Create Automation
          </button>
        </div>
      </div>
      <div className="automation-grid">
        {automations.map((automation) => (
          <div
            key={automation.id}
            className="automation-card"
            onClick={() => onSelectAutomation(automation.id)}
          >
            <h3>{automation.name}</h3>
            <p>{automation.description}</p>
            <div className="card-footer">
              <span>{automation.trigger_type}</span>
              <span>{automation.step_count} steps</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

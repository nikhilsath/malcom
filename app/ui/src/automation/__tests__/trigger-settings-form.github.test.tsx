import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { TriggerSettingsForm } from '../trigger-settings-form';

const defaultValue = {
  name: 'Test',
  description: '',
  enabled: true,
  trigger_type: 'github' as const,
  trigger_config: {
    github_owner: 'octocat',
    github_repo: 'hello-world',
    github_events: ['push'],
    github_secret: 's3cr3t',
  },
};

test('renders github fields and serializes patches', () => {
  const patches: any[] = [];
  const onPatch = (p: any) => patches.push(p);

  render(
    <TriggerSettingsForm
      idPrefix="tst"
      triggerTypeOptions={[]}
      value={defaultValue as any}
      onPatch={onPatch}
    />
  );

  const owner = screen.getByLabelText(/Repository owner/i) as HTMLInputElement;
  expect(owner.value).toBe('octocat');

  const repo = screen.getByLabelText(/Repository name/i) as HTMLInputElement;
  expect(repo.value).toBe('hello-world');

  const events = screen.getByLabelText(/Events/i) as HTMLInputElement;
  expect(events.value).toContain('push');

  // change owner
  fireEvent.change(owner, { target: { value: 'new-owner' } });
  expect(patches.length).toBeGreaterThan(0);
});

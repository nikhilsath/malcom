import * as Switch from '@radix-ui/react-switch'
import { useDeveloperMode } from '../context/developer-mode-context'

export const DeveloperModeToggle = () => {
  const { developerMode, setDeveloperMode } = useDeveloperMode()

  return (
    <div id="developer-mode-toggle-container" className="flex items-center gap-3">
      <label id="developer-mode-toggle-label" htmlFor="topbar-developer-mode-toggle" className="text-sm font-medium text-slate-700">
        Developer mode
      </label>
      <Switch.Root
        id="topbar-developer-mode-toggle"
        checked={developerMode}
        onCheckedChange={setDeveloperMode}
        className="relative h-6 w-11 rounded-full border border-slate-300 bg-slate-200 data-[state=checked]:border-indigo-600 data-[state=checked]:bg-indigo-600"
        aria-label="Toggle developer mode"
      >
        <Switch.Thumb
          id="topbar-developer-mode-toggle-thumb"
          className="block h-5 w-5 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-[1.3rem]"
        />
      </Switch.Root>
      <span id="developer-mode-toggle-status" className="text-xs text-slate-500" aria-live="polite">
        {developerMode ? 'Mock data enabled' : 'Live mode'}
      </span>
    </div>
  )
}

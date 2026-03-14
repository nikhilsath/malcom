import * as Switch from '@radix-ui/react-switch'
import { useDeveloperMode } from '../context/DeveloperModeContext'

export const TopBar = () => {
  const { developerMode, setDeveloperMode } = useDeveloperMode()

  return (
    <header
      id="topbar-root"
      className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4"
    >
      <h1 id="topbar-project-title" className="text-sm font-semibold tracking-wide text-slate-900">
        Malcom Middleware Console
      </h1>

      <div id="topbar-controls" className="flex items-center gap-3">
        <span
          id="topbar-system-status"
          className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700"
        >
          System healthy
        </span>

        <div id="topbar-developer-mode-group" className="flex items-center gap-2">
          <label
            id="topbar-developer-mode-label"
            htmlFor="topbar-developer-mode-toggle"
            className="text-xs font-medium text-slate-700"
          >
            Developer mode
          </label>
          <Switch.Root
            id="topbar-developer-mode-toggle"
            checked={developerMode}
            onCheckedChange={setDeveloperMode}
            aria-label="Toggle developer mode"
            className="relative h-5 w-10 rounded-full border border-slate-300 bg-slate-200 transition data-[state=checked]:border-indigo-600 data-[state=checked]:bg-indigo-600"
          >
            <Switch.Thumb
              id="topbar-developer-mode-toggle-thumb"
              className="block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-[1.1rem]"
            />
          </Switch.Root>
          <span id="topbar-developer-mode-state" className="text-xs text-slate-500" aria-live="polite">
            {developerMode ? 'Mock' : 'Live'}
          </span>
        </div>
      </div>
    </header>
  )
}

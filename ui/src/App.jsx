import { DeveloperModeProvider } from './context/developer-mode-context'
import { DeveloperModeToggle } from './components/developer-mode-toggle'

const TopBar = () => {
  return (
    <header
      id="topbar-root"
      className="flex min-h-16 items-center justify-between border-b border-slate-200 bg-white px-4 py-3"
    >
      <h1 id="topbar-project-title" className="text-lg font-semibold text-slate-900">
        Malcom Middleware
      </h1>
      <div id="topbar-system-status" className="flex items-center gap-4">
        <span id="topbar-system-status-indicator" className="rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
          System healthy
        </span>
        <DeveloperModeToggle />
      </div>
    </header>
  )
}

export const App = () => {
  return (
    <DeveloperModeProvider>
      <div id="app-shell" className="min-h-screen bg-slate-50 text-slate-900">
        <TopBar />
        <main id="home-main-content" className="p-4">
          <section id="home-intro-panel" className="rounded border border-slate-200 bg-white p-4">
            <h2 id="home-intro-title" className="text-base font-semibold">
              UI Step 1: Developer Mode Toggle
            </h2>
            <p id="home-intro-description" className="mt-2 text-sm text-slate-600">
              This toggle is session-scoped and is intended for safe testing with mock data.
            </p>
          </section>
        </main>
      </div>
    </DeveloperModeProvider>
  )
}

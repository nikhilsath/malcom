import { TopBar } from './TopBar'
import { Sidebar } from './Sidebar'

export const AppShell = () => {
  return (
    <div id="app-shell" className="min-h-screen bg-slate-50 text-slate-900">
      <TopBar />
      <div id="app-shell-body" className="flex min-h-[calc(100vh-3.5rem)]">
        <Sidebar />
        <main id="app-main" className="flex-1 p-4">
          <section id="home-intro-panel" className="rounded border border-slate-200 bg-white p-4">
            <h2 id="home-intro-title" className="text-sm font-semibold text-slate-900">
              Middleware Operations Workspace
            </h2>
            <p id="home-intro-description" className="mt-2 text-sm text-slate-600">
              Use the Developer mode switch to choose mock or live behavior for this browser session.
            </p>
          </section>
        </main>
      </div>
    </div>
  )
}

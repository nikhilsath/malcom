export const Sidebar = () => {
  return (
    <aside
      id="sidebar-root"
      className="w-56 shrink-0 border-r border-slate-200 bg-slate-100/70 px-3 py-3"
      aria-label="Primary navigation"
    >
      <nav id="sidebar-nav" className="space-y-1">
        <a
          id="sidebar-nav-dashboard"
          href="#"
          className="block rounded border border-slate-300 bg-white px-2 py-1.5 text-xs font-medium text-slate-800"
        >
          Dashboard
        </a>
        <a id="sidebar-nav-agents" href="#" className="block rounded px-2 py-1.5 text-xs text-slate-600 hover:bg-slate-200">
          Agents
        </a>
        <a id="sidebar-nav-runs" href="#" className="block rounded px-2 py-1.5 text-xs text-slate-600 hover:bg-slate-200">
          Runs
        </a>
      </nav>
    </aside>
  )
}

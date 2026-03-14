import { DeveloperModeProvider } from './context/DeveloperModeContext'
import { AppShell } from './layout/AppShell'

export const App = () => {
  return (
    <DeveloperModeProvider>
      <AppShell />
    </DeveloperModeProvider>
  )
}

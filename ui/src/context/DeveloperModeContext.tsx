import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

type DeveloperModeContextValue = {
  developerMode: boolean
  setDeveloperMode: (enabled: boolean) => void
}

const STORAGE_KEY = 'developerMode'

const readInitialDeveloperMode = (): boolean => {
  if (typeof window === 'undefined') {
    return false
  }

  return window.sessionStorage.getItem(STORAGE_KEY) === 'true'
}

const DeveloperModeContext = createContext<DeveloperModeContextValue | undefined>(undefined)

type DeveloperModeProviderProps = {
  children: ReactNode
}

export const DeveloperModeProvider = ({ children }: DeveloperModeProviderProps) => {
  const [developerMode, setDeveloperMode] = useState<boolean>(readInitialDeveloperMode)

  useEffect(() => {
    window.sessionStorage.setItem(STORAGE_KEY, String(developerMode))
  }, [developerMode])

  const value = useMemo(
    () => ({
      developerMode,
      setDeveloperMode
    }),
    [developerMode]
  )

  return <DeveloperModeContext.Provider value={value}>{children}</DeveloperModeContext.Provider>
}

export const useDeveloperMode = (): DeveloperModeContextValue => {
  const context = useContext(DeveloperModeContext)

  if (!context) {
    throw new Error('useDeveloperMode must be used within a DeveloperModeProvider')
  }

  return context
}

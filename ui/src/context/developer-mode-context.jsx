import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const STORAGE_KEY = 'developerMode'

const readInitialDeveloperMode = () => {
  if (typeof window === 'undefined') {
    return false
  }

  return window.sessionStorage.getItem(STORAGE_KEY) === 'true'
}

const DeveloperModeContext = createContext({
  developerMode: false,
  setDeveloperMode: () => {}
})

export const DeveloperModeProvider = ({ children }) => {
  const [developerMode, setDeveloperMode] = useState(readInitialDeveloperMode)

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

export const useDeveloperMode = () => useContext(DeveloperModeContext)

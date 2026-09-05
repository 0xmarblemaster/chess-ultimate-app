'use client'

import { createContext, useContext } from 'react'

/**
 * Lets a full-screen page (currently the in-game /play screen) hide the mobile
 * app chrome — the top NavBar and the BottomNavigation — while it is active.
 * ClientShell provides the real setter; the default no-op keeps components that
 * consume the hook outside the provider (e.g. isolated tests) working.
 */
export interface ChromeVisibilityValue {
  setChromeHidden: (hidden: boolean) => void
}

const ChromeVisibilityContext = createContext<ChromeVisibilityValue>({
  setChromeHidden: () => {},
})

export const ChromeVisibilityProvider = ChromeVisibilityContext.Provider

export function useChromeVisibility(): ChromeVisibilityValue {
  return useContext(ChromeVisibilityContext)
}

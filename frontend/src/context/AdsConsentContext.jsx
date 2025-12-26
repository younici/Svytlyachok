import { createContext, useContext, useMemo, useState } from "react";

const AdsConsentContext = createContext({
  consent: null,
  accept: () => {},
  decline: () => {},
});

const STORAGE_KEY = "adsConsent";
const validValues = new Set(["granted", "denied"]);

function readInitialConsent() {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem(STORAGE_KEY);
  return validValues.has(stored) ? stored : null;
}

export function AdsConsentProvider({ children }) {
  const [consent, setConsent] = useState(() => readInitialConsent());

  const accept = () => {
    setConsent("granted");
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, "granted");
  };

  const decline = () => {
    setConsent("denied");
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, "denied");
  };

  const value = useMemo(
    () => ({
      consent,
      accept,
      decline,
    }),
    [consent]
  );

  return <AdsConsentContext.Provider value={value}>{children}</AdsConsentContext.Provider>;
}

export function useAdsConsent() {
  return useContext(AdsConsentContext);
}

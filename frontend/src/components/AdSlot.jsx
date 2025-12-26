import { useEffect, useRef } from "react";
import styles from "./AdSlot.module.css";

const ADSENSE_CLIENT = import.meta.env.VITE_ADSENSE_CLIENT || "ca-pub-2059432028788704";

let scriptInjected = false;

function ensureAdSenseScript() {
  if (scriptInjected || typeof document === "undefined") return;
  const script = document.createElement("script");
  script.async = true;
  script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT}`;
  script.crossOrigin = "anonymous";
  document.head.appendChild(script);
  scriptInjected = true;
}

function AdSlot({ slot, format = "auto", fullWidth = true, enabled = false }) {
  const initialized = useRef(false);

  useEffect(() => {
    if (!enabled || !slot || initialized.current) return;
    ensureAdSenseScript();

    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
      initialized.current = true;
    } catch (_) {
      /* ignore ad blocker errors */
    }
  }, [slot, enabled]);

  if (!slot || !enabled) return null;

  return (
    <div className={styles.container} aria-label="Рекламний блок">
      <span className={styles.label}>Реклама</span>
      <ins
        className={`adsbygoogle ${styles.slot}`}
        style={{ display: "block" }}
        data-ad-client={ADSENSE_CLIENT}
        data-ad-slot={slot}
        data-ad-format={format}
        data-full-width-responsive={fullWidth ? "true" : "false"}
      />
    </div>
  );
}

export default AdSlot;

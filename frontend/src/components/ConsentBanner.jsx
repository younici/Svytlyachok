import { useAdsConsent } from "../context/AdsConsentContext.jsx";
import styles from "./ConsentBanner.module.css";

const privacyHref = "/privacy";

function ConsentBanner() {
  const { consent, accept, decline } = useAdsConsent();
  const isOpen = consent === null;

  if (!isOpen) return null;

  return (
    <div className={styles.banner} role="dialog" aria-live="polite" aria-label="Налаштування реклами">
      <div className={styles.text}>
        <p className={styles.title}>Реклама Google</p>
        <p className={styles.copy}>
          Використовуємо cookie для показу оголошень Google AdSense. Ви можете прийняти або відхилити використання cookie для
          реклами. Деталі — у{" "}
          <a href={privacyHref} className={styles.link}>
            політиці приватності
          </a>
          .
        </p>
      </div>
      <div className={styles.actions}>
        <button type="button" className={styles.secondary} onClick={decline}>
          Відхилити
        </button>
        <button type="button" className={styles.primary} onClick={accept}>
          Прийняти Cookie
        </button>
      </div>
    </div>
  );
}

export default ConsentBanner;

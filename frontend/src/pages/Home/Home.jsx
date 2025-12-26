import { Link } from "react-router-dom";
import AdSlot from "../../components/AdSlot.jsx";
import { useAdsConsent } from "../../context/AdsConsentContext.jsx";
import styles from "./Home.module.css";

const homeAdSlot = import.meta.env.VITE_ADSENSE_SLOT_HOME;

const highlights = [
  {
    title: "Збір з офіційних джерел",
    body: "Беремо графік з сайту Житомиробленерго та приводимо його до зручного вигляду з півгодинними інтервалами.",
  },
  {
    title: "Сповіщення за годину",
    body: "Попереджаємо про планове відключення через push або Telegram-бота — без зайвого шуму.",
  },
  {
    title: "Перемикання режимів",
    body: "Дивіться повний графік по годинах або компактні проміжки без світла — обирайте, як вам зручніше.",
  },
  {
    title: "Прозорість даних",
    body: "Нагадуємо про можливі відхилення та показуємо час останнього оновлення, щоб ви знали, наскільки інформація свіжа.",
  },
];

const steps = [
  {
    title: "1. Оберіть свою чергу",
    body: "Дізнайтесь номер черги на сайті Житомиробленерго та збережіть його у виборі — ми пам’ятатимемо ваш вибір.",
  },
  {
    title: "2. Увімкніть сповіщення",
    body: "Додайте Telegram-бот або дозвольте вебсповіщення, щоб отримувати нагадування за годину до планового відключення.",
  },
  {
    title: "3. Контролюйте графік",
    body: "Перемикайтеся між видами графіка, дивіться відрізки без світла та оновлюйте дані у будь-який момент.",
  },
];

function Home() {
  const { consent } = useAdsConsent();
  const adsEnabled = consent === "granted";

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroText}>
          <p className={styles.eyebrow}>Онлайн-гід по стабілізаційних відключеннях</p>
          <h1 className={styles.title}>Likhtarychok допомагає підготуватися до планових відключень у Житомирі</h1>
          <p className={styles.lead}>
            Оновлюємо графік кожні 5 хвилин, показуємо його у двох режимах та нагадуємо про відключення завчасно.
            Усе заточено під швидку перевірку вашої черги.
          </p>
          <div className={styles.actions}>
            <Link className={styles.primary} to="/graph">
              Перейти до графіка
            </Link>
            <Link className={styles.secondary} to="/info">
              Як працює сервіс
            </Link>
          </div>
          <div className={styles.tags}>
            <span>Оновлення раз на 5 хв</span>
            <span>Push та Telegram</span>
            <span>Житомирська область</span>
          </div>
        </div>

        <div className={styles.heroPanel}>
          <div className={styles.panelHeader}>
            <p className={styles.panelLabel}>Що ви отримуєте</p>
            <span className={styles.pill}>Зроблено для повсякденного використання</span>
          </div>
          <div className={styles.panelGrid}>
            <div className={styles.panelCard}>
              <p className={styles.metricLabel}>Режими перегляду</p>
              <p className={styles.metricValue}>Графік / Інтервали</p>
              <p className={styles.metricCopy}>Перемикайтесь між деталізацією на день і короткими слотами без світла.</p>
            </div>
            <div className={styles.panelCard}>
              <p className={styles.metricLabel}>Актуальність</p>
              <p className={styles.metricValue}>кожні 5 хвилин</p>
              <p className={styles.metricCopy}>Синхронізуємося з офіційним сайтом Житомиробленерго протягом дня.</p>
            </div>
            <div className={styles.panelWide}>
              <p className={styles.metricLabel}>Прозора інформація</p>
              <p className={styles.metricCopy}>
                Вказуємо джерело, нагадуємо про можливі розбіжності та пропонуємо резервний канал — Telegram-бот для сповіщень,
                якщо браузер не підтримує web-push.
              </p>
            </div>
          </div>
        </div>
      </section>

      <AdSlot slot={homeAdSlot} enabled={adsEnabled} />

      <section className={styles.highlights}>
        {highlights.map((item) => (
          <div key={item.title} className={styles.card}>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </div>
        ))}
      </section>

      <section className={styles.steps}>
        <div className={styles.stepsIntro}>
          <p className={styles.eyebrow}>Як користуватись</p>
          <h2>Зібрали шлях користувача у три прості кроки</h2>
          <p>
            Від пошуку своєї черги до сповіщень про планове відключення — усе в одному місці.
          </p>
        </div>
        <div className={styles.stepsGrid}>
          {steps.map((step) => (
            <div key={step.title} className={styles.stepCard}>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default Home;

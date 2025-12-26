import { NavLink, Outlet, useLocation } from "react-router-dom";
import ConsentBanner from "./ConsentBanner.jsx";
import styles from "./Layout.module.css";

const navLinks = [
  { to: "/graph", label: "Графік" },
  { to: "/info", label: "Про сервіс" },
  { to: "/faq", label: "FAQ" },
];

function Layout() {
  const { pathname } = useLocation();

  return (
    <div className={styles.shell}>
      <div className={styles.ambient} aria-hidden />
      <header className={styles.header}>
        <NavLink to="/" className={styles.brand}>
          <div className={styles.logoMark}>
            <span />
          </div>
          <div className={styles.brandText}>
            <p className={styles.logoTitle}>Likhtarychok</p>
            <small className={styles.logoSubtitle}>Графік відключень у Житомирі</small>
          </div>
        </NavLink>

        <nav className={styles.nav}>
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.activeNav : ""}`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <NavLink
          to="/graph"
          className={`${styles.cta} ${pathname === "/graph" ? styles.ctaGhost : ""}`}
        >
          Дивитися графік
        </NavLink>
      </header>

      <main className={styles.main}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <div>
          <div className={styles.logoMarkSmall} aria-hidden />
          <p className={styles.footerTitle}>Likhtarychok</p>
          <p className={styles.footerCopy}>
            Онлайн-гід по стабілізаційних відключеннях з push-сповіщеннями.
          </p>
        </div>
        <div className={styles.footerLinks}>
          <div>
            <p className={styles.footerLabel}>Розділи</p>
            <NavLink to="/graph">Графік</NavLink>
            <NavLink to="/info">Про сервіс</NavLink>
            <NavLink to="/faq">FAQ</NavLink>
          </div>
          <div>
            <p className={styles.footerLabel}>Контакти</p>
            <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">
              Telegram-бот підтримки
            </a>
            <a href="mailto:kostantinreksha@gmail.com">kostantinreksha@gmail.com</a>
            <a href="https://t.me/younici" target="_blank" rel="noreferrer">
              Зворотний зв'язок
            </a>
            <NavLink to="/privacy">Політика приватності</NavLink>
          </div>
        </div>
        <div className={styles.footerMeta}>
          <span>© 2025 Likhtarychok</span>
          <span>Графік оновлюється кожні 5 хвилин</span>
        </div>
      </footer>

      <ConsentBanner />
    </div>
  );
}

export default Layout;

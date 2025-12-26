import styles from "./Privacy.module.css";

function Privacy() {
  return (
    <div className={styles.page}>
      <section className={styles.header}>
        <p className={styles.eyebrow}>Політика приватності</p>
        <h1>Як ми працюємо з даними та рекламою</h1>
        <p className={styles.lead}>
          Ми не збираємо персональні дані користувачів. Для показу оголошень Google AdSense можуть використовуватись файли
          cookie та ідентифікатори браузера. Ви можете прийняти або відхилити використання cookie для реклами.
        </p>
      </section>

      <section className={styles.grid}>
        <div className={styles.card}>
          <h3>Дані, які ми зберігаємо</h3>
          <ul>
            <li>Номер обраної черги та налаштування вигляду графіка — у локальному сховищі браузера.</li>
            <li>Підписка на сповіщення (якщо ви її підтвердили) — для надсилання web-push.</li>
          </ul>
        </div>
        <div className={styles.card}>
          <h3>Що не збираємо</h3>
          <ul>
            <li>Не просимо ім’я, email чи інші персональні дані для користування сайтом.</li>
            <li>Не продаємо та не передаємо інформацію третім сторонам, окрім сервісів Google для реклами.</li>
          </ul>
        </div>
        <div className={styles.card}>
          <h3>Реклама Google AdSense</h3>
          <ul>
            <li>Для показу оголошень Google може використовувати cookie або локальні ідентифікатори.</li>
            <li>Без вашої згоди реклама не завантажується. Ви можете змінити вибір у нижньому банері.</li>
            <li>Докладніше: <a href="https://policies.google.com/technologies/ads" target="_blank" rel="noreferrer">політика Google щодо реклами</a>.</li>
          </ul>
        </div>
        <div className={styles.card}>
          <h3>Як відкликати або змінити згоду</h3>
          <ul>
            <li>Скористайтеся банером згоди внизу сайту, щоб дозволити або відхилити рекламні cookie.</li>
            <li>Очистіть файли cookie/LocalStorage браузера, щоб скинути налаштування.</li>
          </ul>
        </div>
      </section>

      <section className={styles.note}>
        <div>
          <p className={styles.eyebrow}>Запитання</p>
          <h3>Потрібна допомога або видалення даних?</h3>
          <p>
            Напишіть нам на{" "}
            <a href="mailto:kostantinreksha@gmail.com" rel="noreferrer">
              kostantinreksha@gmail.com
            </a>{" "}
            або у <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">Telegram-бот підтримки</a>.
          </p>
        </div>
      </section>
    </div>
  );
}

export default Privacy;

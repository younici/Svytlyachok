import { Link } from "react-router-dom";
import styles from "./Info.module.css";

function Info() {
  return (
    <>
      <div className={styles.infoContainer}>
        <div className={styles.infoHead}>
          <h2 className={`${styles.infoTitle} ${styles.card}`}>Про сайт</h2>
          <Link className={`${styles.card} ${styles.cta}`} to="/graph">
            Перейти до графіку
          </Link>
        </div>
        <div className={styles.infoBody}>
          <div className={styles.card}>
            <h1>
              <Link to="/graph">Likhtarychok</Link> (Ліхтаричок) сайт створений для зручного показу
              графіку відключень світла по Житомирьскій області
            </h1>
          </div>
          <div className={styles.card}>
            Як дізнатися свою чергу? зайдіть на сайт{" "}
            <a href="https://www.ztoe.com.ua/unhooking-search.php" target="_blank" rel="noreferrer">
              Житомир обл. Енерго
            </a>{" "}
            та знайдіть свою чергу
          </div>
          <div className={styles.card}>
            <p>
              Графік береться з{" "}
              <a href="https://www.ztoe.com.ua/unhooking-search.php" target="_blank" rel="noreferrer">
                офіційного сайту Житомир обл. Енерго
              </a>
            </p>
          </div>
          <div className={styles.card}>
            Графік може бути не точним, так як самі працівникі Житомир обл. Енерго
            не завджи знають коли потрібно відключити світло а коли ні
          </div>
        </div>
      </div>
    </>
  );
}

export default Info;

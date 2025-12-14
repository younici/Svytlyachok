/* eslint-disable no-unused-vars */
import { useCallback, useEffect, useMemo, useState } from "react";
import styles from "./App.module.css";

const queueOptions = ["11", "12", "21", "22", "31", "32", "41", "42", "51", "52", "61", "62"];
const defaultStatuses = Array(48).fill(false);

const apiBase = import.meta.env.VITE_API_BASE

const timeSlots = [
  "00:00–01:00",
  "01:00–02:00",
  "02:00–03:00",
  "03:00–04:00",
  "04:00–05:00",
  "05:00–06:00",
  "06:00–07:00",
  "07:00–08:00",
  "08:00–09:00",
  "09:00–10:00",
  "10:00–11:00",
  "11:00–12:00",
  "12:00–13:00",
  "13:00–14:00",
  "14:00–15:00",
  "15:00–16:00",
  "16:00–17:00",
  "17:00–18:00",
  "18:00–19:00",
  "19:00–20:00",
  "20:00–21:00",
  "21:00–22:00",
  "22:00–23:00",
  "23:00–24:00",
];

const lampOffSvg = (
  <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M9 18h6" />
    <path d="M10 21h4" />
    <path d="M8 15a6 6 0 1 1 8 0l-1 1.5H9z" />
    <line x1="5" y1="5" x2="19" y2="19" />
  </svg>
);

function loadQueueFromStorage() {
  if (typeof window === "undefined") return queueOptions[0];
  const saved = localStorage.getItem("queueSelector") ?? queueOptions[0];
  if (saved === "1" || saved === "0") return `3${Number(saved) + 1}`;
  return queueOptions.includes(saved) ? saved : queueOptions[0];
}

function loadToggleFromStorage() {
  if (typeof window === "undefined") return false;
  return localStorage.getItem("queueToggle") === "true";
}

function normalizeStatuses(data = []) {
  const normalized = [];
  const len = data.length;

  for (let h = 0; h < 24; h += 1) {
    let left = false;
    let right = false;

    if (len >= 48) {
      left = Boolean(data[h * 2] ?? 0);
      right = Boolean(data[h * 2 + 1] ?? 0);
    } else if (len === 24) {
      const v = Boolean(data[h] ?? 0);
      left = v;
      right = v;
    } else if (len > 0) {
      left = Boolean(data[Math.min(h * 2, len - 1)] ?? 0);
      right = Boolean(data[Math.min(h * 2 + 1, len - 1)] ?? 0);
    }

    normalized.push(left);
    normalized.push(right);
  }

  return normalized;
}

function formatHalfHour(index) {
  if (index >= 48) return "24:00";
  const hours = Math.floor(index / 2);
  const minutes = index % 2 === 0 ? "00" : "30";
  return `${String(hours).padStart(2, "0")}:${minutes}`;
}

function collectOutageRanges(statuses) {
  const ranges = [];
  let start = null;

  for (let i = 0; i <= statuses.length; i += 1) {
    const off = statuses[i] ?? false;

    if (off && start === null) start = i;

    const isBoundary = !off || i === statuses.length;
    if (isBoundary && start !== null) {
      ranges.push({ start, end: i });
      start = null;
    }
  }

  return ranges.map(({ start, end }) => ({
    start: formatHalfHour(start),
    end: formatHalfHour(end),
  }));
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i += 1) outputArray[i] = rawData.charCodeAt(i);
  return outputArray;
}

function App() {
  const [queue, setQueue] = useState(() => loadQueueFromStorage());
  const [useOutageView, setUseOutageView] = useState(() => loadToggleFromStorage());
  const [statuses, setStatuses] = useState(defaultStatuses);
  const [outageRanges, setOutageRanges] = useState([]);
  const [hasData, setHasData] = useState(false);
  const [publicKey, setPublicKey] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [btnFinished, setBtnFinished] = useState(false);
  const [showBtnFinished, setShowBtnFinished] = useState(false);

  const queueLabel = `${queue[0]}.${queue[1]}`;

  useEffect(() => {
    localStorage.setItem("queueSelector", queue);
  }, [queue]);

  useEffect(() => {
    localStorage.setItem("queueToggle", useOutageView.toString());
  }, [useOutageView]);

  const ensurePublicKey = useCallback(async () => {
    try {
      const response = await fetch(`${apiBase}/vapid_public_key`);
      const data = await response.json();
      if (data?.key) setPublicKey(data.key);
      return data?.key ?? null;
    } catch (_) {
      return null;
    }
  }, []);

  const fetchStatuses = useCallback(async (selectedQueue) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${apiBase}/status?queue=${selectedQueue}`);
      const json = await response.json();
      const source = Array.isArray(json?.Status) ? json.Status : [];
      const normalized = normalizeStatuses(source);
      setStatuses(normalized);
      setHasData(source.length > 0);
      setOutageRanges(source.length > 0 ? collectOutageRanges(normalized) : []);
    } catch (_) {
      setStatuses(defaultStatuses);
      setHasData(false);
      setOutageRanges([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatuses(queue);
  }, [queue, fetchStatuses]);

  useEffect(() => {
    ensurePublicKey();
  }, [ensurePublicKey]);

  useEffect(() => {
    const timer1 = setTimeout(() => setBtnFinished(true), 3000);
    const timer2 = setTimeout(() => setShowBtnFinished(true), 3700);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, []);

  const statusRows = useMemo(
    () =>
      Array.from({ length: 24 }, (_, idx) => {
        const left = statuses[idx * 2] ?? false;
        const right = statuses[idx * 2 + 1] ?? false;
        return [left, right];
      }),
    [statuses]
  );

  async function subscribeViaSite() {
    if (!("Notification" in window) || !("serviceWorker" in navigator) || !("PushManager" in window)) {
      alert("На жаль в вашому браузері немає підтримки веб сповіщень, ви можете підписатися на сповіщення в телеграмі");
      return;
    }

    const key = publicKey ?? (await ensurePublicKey());
    if (!key) {
      alert("Не вдалося отримати ключ для підписки.");
      return;
    }

    try {
      const reg = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;

      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(key),
      });

      const payload = {
        queue,
        subscription,
      };

      const answer = await fetch(`${apiBase}/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      let result = null;
      try {
        result = await answer.json();
      } catch (_) {
        /* ignore */
      }

      const msg = result?.msg || (answer.ok ? "ok" : "Помилка підписки");
      alert(`${msg} ${queueLabel}`);
    } catch (_) {
      alert("На жаль в вашому браузері немає підтримки веб сповіщень, ви можете підписатися на сповіщення в телеграмі");
    } finally {
      setIsModalOpen(false);
    }
  }

  async function unsubscribe() {
    try {
      const reg = await navigator.serviceWorker.register(`${apiBase}/sw.js`);
      const sw = await navigator.serviceWorker.ready;
      const currentSub = await sw.pushManager.getSubscription();

      if (!currentSub) {
        alert("Підписка не знайдена на цьому пристрої.");
        return;
      }

      const payload = {
        subscription: currentSub.toJSON ? currentSub.toJSON() : currentSub,
      };

      try {
        const answer = await fetch(`${apiBase}/unsubscribe`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const result = await answer.json();
        alert(result?.msg || (result?.ok ? "Підписку скасовано" : "Помилка"));
      } catch (_) {
        alert("Не вдалося скасувати підписку.");
      }

      try {
        await currentSub.unsubscribe();
      } catch (_) {
        /* ignore */
      }
    } catch (_) {
      alert("Не вдалося скасувати підписку.");
    }
  }

  const outageContent = useMemo(() => {
    if (!hasData) {
      return <p className={styles.outageEmpty}>Немає даних по графіку</p>;
    }

    if (outageRanges.length === 0) {
      return <p className={styles.outageEmpty}>Сьогодні відключень не планується</p>;
    }

    return outageRanges.map(({ start, end }) => (
      <div key={`${start}-${end}`} className={styles.outageChip}>
        {start}–{end}
      </div>
    ));
  }, [hasData, outageRanges]);

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <div className={styles.mainElements}>
          <p>
            Якщо дозволите сповіщення то ми повідомимо про відключення світла за
            годину по графіку.
          </p>

          <div className={styles.buttonsDiv}>
            <button type="button" onClick={() => setIsModalOpen(true)}>
              Пiдписатись на сповіщення
            </button>
            <button type="button" onClick={unsubscribe}>
              Відписатись від сповіщень
            </button>
          </div>

          <p>Виберіть чергу</p>

          <select
            id="queueSelector"
            className={styles.queueSelector}
            value={queue}
            onChange={(e) => setQueue(e.target.value)}
          >
            {queueOptions.map((value) => (
              <option key={value} value={value}>
                {value[0]}.{value[1]}
              </option>
            ))}
          </select>

          <button type="button" className={styles.refreshQueue} onClick={() => fetchStatuses(queue)} disabled={isLoading}>
            {isLoading ? "Оновлюємо..." : "Оновити iнформацiю"}
          </button>
        </div>

        <div className={styles.toggleBlock}>
          <p>
            Переключити вигляд графіку
            <br />
            <br />
            Графік / Години
          </p>
          <label className={styles.switch}>
            <input type="checkbox" id="queueToggle" checked={useOutageView} onChange={(e) => setUseOutageView(e.target.checked)} />
            <span className={styles.slider}></span>
          </label>
        </div>

        <div className={`${styles.rowContainer} ${useOutageView ? styles.disp : ""}`}>
          <div className={styles.statusContainer}>
            {statusRows.map(([left, right], idx) => (
              <div key={`status-${idx}`} className={styles.statusElement}>
                <div className={`${styles.status} ${left ? styles.off : ""}`}>{left ? lampOffSvg : null}</div>
                <div className={`${styles.status} ${right ? styles.off : ""}`}>{right ? lampOffSvg : null}</div>
              </div>
            ))}
          </div>

          <div className={styles.timeContainer}>
            {timeSlots.map((slot) => (
              <p key={slot} className={styles.rowElement}>
                {slot}
              </p>
            ))}
          </div>
        </div>

        <div className={`${styles.outageSummary} ${useOutageView ? "" : styles.disp}`}>
          <p className={styles.outageTitle}>Години без світла</p>
          <div id="outageList" className={styles.outageList}>
            {outageContent}
          </div>
        </div>
      </div>

      <a className={`${styles.btnContainer} ${btnFinished ? styles.btnFinished : ""}`} href="/info">
        <span className={styles.infoText}>Інформація про сайт</span>
      </a>
      <a className={`${styles.showBtn} ${showBtnFinished ? styles.showBtnFinished : ""}`} href="/info" aria-label="Перейти до сторінки з інформацією про сайт">
        i
      </a>

      {isModalOpen && (
        <>
          <div className={styles.modal}>
            <p>Виберіть куди нам відсилати вам сповіщення</p>
            <button type="button" className={styles.closeModal} onClick={() => setIsModalOpen(false)}>
              X
            </button>
            <div className={styles.modalButtons}>
              <a className={styles.selectorBtn} href="https://t.me/likhtarychok_bot" target="_blank" rel="noreferrer">
                Телеграм Бот
              </a>
              <button type="button" className={styles.selectorBtn} onClick={subscribeViaSite}>
                Через сайт (Не у всіх працює)
              </button>
            </div>
          </div>
          <div className={styles.modalOverlay} onClick={() => setIsModalOpen(false)}></div>
        </>
      )}
    </main>
  );
}

export default App;

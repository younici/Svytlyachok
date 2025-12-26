import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import AdSlot from "../../components/AdSlot.jsx";
import { useAdsConsent } from "../../context/AdsConsentContext.jsx";
import styles from "./Graph.module.css";

const graphAdSlot = import.meta.env.VITE_ADSENSE_SLOT_GRAPH;

const queueOptions = ["11", "12", "21", "22", "31", "32", "41", "42", "51", "52", "61", "62"];
const defaultStatuses = Array(48).fill(false);

const apiBase =
  import.meta.env.API_BASE_PATH ||
  import.meta.env.VITE_API_BASE ||
  import.meta.env.VITE_API_BASE_PATH ||
  "";
const grpcStatusEndpoint = `${apiBase}/grpc/StatusService/GetStatus`;

const textEncoder = new TextEncoder();

function encodeVarint(value) {
  const bytes = [];
  let v = value >>> 0;
  while (v >= 0x80) {
    bytes.push((v & 0x7f) | 0x80);
    v >>>= 7;
  }
  bytes.push(v);
  return Uint8Array.from(bytes);
}

function decodeVarint(bytes, start = 0) {
  let result = 0;
  let shift = 0;
  let pos = start;

  while (pos < bytes.length) {
    const byte = bytes[pos];
    result |= (byte & 0x7f) << shift;
    pos += 1;
    if ((byte & 0x80) === 0) break;
    shift += 7;
  }

  return [result, pos - start];
}

function encodeStatusRequest(queue = "") {
  const queueBytes = textEncoder.encode(queue);
  const lenBytes = encodeVarint(queueBytes.length);
  const message = new Uint8Array(1 + lenBytes.length + queueBytes.length);
  message[0] = 0x0a; // field 1, wire type 2
  message.set(lenBytes, 1);
  message.set(queueBytes, 1 + lenBytes.length);
  return message;
}

function wrapGrpcWebMessage(messageBytes) {
  const buffer = new Uint8Array(5 + messageBytes.length);
  const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  buffer[0] = 0x00; // data frame
  view.setUint32(1, messageBytes.length, false);
  buffer.set(messageBytes, 5);
  return buffer;
}

function unwrapGrpcWebMessage(buffer) {
  const bytes = new Uint8Array(buffer);
  if (bytes.length < 5) throw new Error("Invalid gRPC-web response");

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const isDataFrame = bytes[0] === 0x00 || bytes[0] === 0x01;
  if (!isDataFrame) throw new Error("Unexpected gRPC-web frame");

  const msgLength = view.getUint32(1, false);
  const end = 5 + msgLength;
  if (end > bytes.length) throw new Error("Truncated gRPC-web payload");

  return bytes.slice(5, end);
}

function decodeStatusResponse(messageBytes) {
  const result = [];
  let pos = 0;

  while (pos < messageBytes.length) {
    const tag = messageBytes[pos];
    pos += 1;
    const field = tag >> 3;
    const wireType = tag & 0x07;

    if (field === 1 && wireType === 2) {
      const [length, lenBytes] = decodeVarint(messageBytes, pos);
      pos += lenBytes;
      const end = pos + length;
      while (pos < end) {
        const [val, read] = decodeVarint(messageBytes, pos);
        result.push(Boolean(val));
        pos += read;
      }
    } else if (wireType === 0) {
      const [, read] = decodeVarint(messageBytes, pos);
      pos += read;
    } else if (wireType === 2) {
      const [length, lenBytes] = decodeVarint(messageBytes, pos);
      pos += lenBytes + length;
    } else {
      break;
    }
  }

  return result;
}

async function fetchStatusGrpc(queue) {
  const message = encodeStatusRequest(queue ?? "");
  const payload = wrapGrpcWebMessage(message);

  const response = await fetch(grpcStatusEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/grpc-web+proto",
      "X-Grpc-Web": "1",
    },
    body: payload,
  });

  if (!response.ok) throw new Error(`gRPC request failed (${response.status})`);

  const buffer = await response.arrayBuffer();
  const messageBytes = unwrapGrpcWebMessage(buffer);
  return decodeStatusResponse(messageBytes);
}

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
  <svg
    viewBox="0 0 24 24"
    width="22"
    height="22"
    stroke="currentColor"
    fill="none"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
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

function Graph() {
  const [queue, setQueue] = useState(() => loadQueueFromStorage());
  const [useOutageView, setUseOutageView] = useState(() => loadToggleFromStorage());
  const [statuses, setStatuses] = useState(defaultStatuses);
  const [outageRanges, setOutageRanges] = useState([]);
  const [hasData, setHasData] = useState(false);
  const [publicKey, setPublicKey] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { consent } = useAdsConsent();
  const adsEnabled = consent === "granted";

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
      const source = await fetchStatusGrpc(selectedQueue);
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
    const intervalId = setInterval(() => fetchStatuses(queue), 5 * 60 * 1000);
    return () => clearInterval(intervalId);
  }, [queue, fetchStatuses]);

  useEffect(() => {
    ensurePublicKey();
  }, [ensurePublicKey]);

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
      alert("На жаль, ваш браузер не підтримує вебсповіщення. Ви можете підписатися на сповіщення в Telegram.");
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
      alert("На жаль, ваш браузер не підтримує вебсповіщення. Ви можете підписатися на сповіщення в Telegram.");
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
      return <p className={styles.outageEmpty}>Немає даних щодо графіка</p>;
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
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.heroText}>
          <p className={styles.eyebrow}>Графік для вашої черги</p>
          <h1>Контролюйте чергу {queueLabel} та отримуйте нагадування за годину</h1>
          <p className={styles.lead}>
            Перемикайтесь між виглядом «Графік» та «Години», оновлюйте дані вручну та підключайте push-сповіщення.
            Якщо потрібні деталі — зазирніть у <Link to="/faq">FAQ</Link>.
          </p>
          <div className={styles.meta}>
            <span>Оновлення кожні 5 хв</span>
            <span>Push + Telegram</span>
            <span>Житомирська область</span>
          </div>
        </div>

        <div className={styles.heroCard}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.label}>Ваша черга</p>
              <p className={styles.copy}>Зберігаємо вибір у браузері та не запитуємо персональні дані.</p>
            </div>
            <span className={styles.queuePill}>{queueLabel}</span>
          </div>

          <div className={styles.selectRow}>
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
              {isLoading ? "Оновлюємо..." : "Оновити"}
            </button>
          </div>

          <div className={styles.toggleRow}>
            <div>
              <p className={styles.label}>Перемкнути вигляд</p>
              <p className={styles.copy}>Графік або готові інтервали без світла.</p>
            </div>
            <label className={styles.switch}>
              <input
                type="checkbox"
                id="queueToggle"
                checked={useOutageView}
                onChange={(e) => setUseOutageView(e.target.checked)}
              />
              <span className={styles.switchLabel}>{useOutageView ? "Години" : "Графік"}</span>
            </label>
          </div>
        </div>
      </section>

      <section className={styles.actionsRow}>
        <div className={styles.actionCard}>
          <div>
            <p className={styles.label}>Сповіщення за годину</p>
            <p className={styles.copy}>
              Надішлемо нагадування перед плановим відключенням. Якщо web-push недоступний, використовуйте{" "}
              <a href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">Telegram-бот підтримки</a>.
            </p>
          </div>
          <div className={styles.actionButtons}>
            <button type="button" onClick={() => setIsModalOpen(true)}>
              Увімкнути сповіщення
            </button>
            <button type="button" className={styles.ghostButton} onClick={unsubscribe}>
              Скасувати підписку
            </button>
          </div>
        </div>

        <div className={styles.noteCard}>
          <p className={styles.label}>Нагадуємо</p>
          <p className={styles.copy}>
            Офіційний графік може змінюватися протягом дня. Якщо бачите розбіжності — перевірте повторно або зайдіть у Telegram-бот.
          </p>
        </div>
      </section>

      <AdSlot slot={graphAdSlot} enabled={adsEnabled} />

      <section className={styles.grid}>
        <div className={`${styles.card} ${useOutageView ? styles.collapsed : ""} ${isLoading ? styles.faded : ""}`}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.label}>Графік для черги {queueLabel}</p>
              <p className={styles.copy}>Оновлюємо кожні 5 хвилин. Натисніть «Оновити», якщо потрібна актуальність просто зараз.</p>
            </div>
            <div className={styles.legend}>
              <span className={styles.legendDot} />
              <span>Планове відключення</span>
            </div>
          </div>

          <div className={styles.schedule}>
            {statusRows.map(([left, right], idx) => (
              <div key={`status-${idx}`} className={styles.row}>
                <div className={styles.time}>{timeSlots[idx]}</div>
                <div className={`${styles.slot} ${left ? styles.off : ""}`}>{left ? lampOffSvg : null}</div>
                <div className={`${styles.slot} ${right ? styles.off : ""}`}>{right ? lampOffSvg : null}</div>
              </div>
            ))}
          </div>
        </div>

        <div className={`${styles.outageCard} ${useOutageView ? "" : styles.collapsed} ${isLoading ? styles.faded : ""}`}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.label}>Години без світла</p>
              <p className={styles.copy}>Список інтервалів для черги {queueLabel}</p>
            </div>
            <span className={styles.chip}>{useOutageView ? "Вигляд: Години" : "Вигляд: Графік"}</span>
          </div>
          <div className={styles.outageList}>{outageContent}</div>
          <Link className={styles.faqLink} to="/faq">
            Перейти до FAQ
          </Link>
        </div>
      </section>

      {isModalOpen && (
        <>
          <div className={styles.modal}>
            <p className={styles.label}>Куди надсилати сповіщення?</p>
            <p className={styles.copy}>Обирайте варіант, який підходить пристрою. Push працює не у всіх браузерах.</p>
            <button type="button" className={styles.closeModal} onClick={() => setIsModalOpen(false)}>
              ✕
            </button>
            <div className={styles.modalButtons}>
              <a className={styles.selectorBtn} href="https://t.me/likhtarychok_help_bot" target="_blank" rel="noreferrer">
                Telegram-бот підтримки
              </a>
              <button type="button" className={styles.selectorBtn} onClick={subscribeViaSite}>
                Через сайт (web-push)
              </button>
            </div>
          </div>
          <div className={styles.modalOverlay} onClick={() => setIsModalOpen(false)} />
        </>
      )}
    </div>
  );
}

export default Graph;

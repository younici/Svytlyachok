import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import styles from "../Graph/Graph.module.css"; // ті самі стилі, що й у графіка

// Ті самі константи з Graph.jsx
const queueOptions = ["11", "12", "21", "22", "31", "32", "41", "42", "51", "52", "61", "62"];

let apiBase =
  import.meta.env.API_BASE_PATH ||
  import.meta.env.VITE_API_BASE ||
  import.meta.env.VITE_API_BASE_PATH ||
  "";
apiBase = "https://likhtarychok.org/api"
const grpcStatusEndpoint = `${apiBase}/grpc/StatusService/GetStatus`;

// Копіюємо потрібні функції для gRPC (ті самі, що в Graph)
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
  message[0] = 0x0a;
  message.set(lenBytes, 1);
  message.set(queueBytes, 1 + lenBytes.length);
  return message;
}

function wrapGrpcWebMessage(messageBytes) {
  const buffer = new Uint8Array(5 + messageBytes.length);
  const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  buffer[0] = 0x00;
  view.setUint32(1, messageBytes.length, false);
  buffer.set(messageBytes, 5);
  return buffer;
}

function unwrapGrpcWebMessage(buffer) {
  const bytes = new Uint8Array(buffer);
  if (bytes.length < 5) throw new Error("Invalid gRPC-web response");
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
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

// Нормалізація та розрахунок інтервалів
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

// Завантаження черги з localStorage
function loadQueueFromStorage() {
  if (typeof window === "undefined") return queueOptions[0];
  const saved = localStorage.getItem("widgetQueueSelector") || localStorage.getItem("queueSelector") || queueOptions[0];
  return queueOptions.includes(saved) ? saved : queueOptions[0];
}

function Widget() {
  const [queue, setQueue] = useState(() => loadQueueFromStorage());
  const [statuses, setStatuses] = useState([]);
  const [outageRanges, setOutageRanges] = useState([]);
  const [hasData, setHasData] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const queueLabel = `${queue[0]}.${queue[1]}`;

  const fetchStatuses = useCallback(async (selectedQueue) => {
    setIsLoading(true);
    try {
      const source = await fetchStatusGrpc(selectedQueue);
      const normalized = normalizeStatuses(source);
      setStatuses(normalized);
      setHasData(source.length > 0);
      setOutageRanges(source.length > 0 ? collectOutageRanges(normalized) : []);
    } catch (err) {
      console.error(err);
      setStatuses([]);
      setHasData(false);
      setOutageRanges([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatuses(queue);
  }, [queue, fetchStatuses]);

  // Автооновлення кожні 5 хвилин
  useEffect(() => {
    const interval = setInterval(() => fetchStatuses(queue), 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [queue, fetchStatuses]);

  const outageContent = useMemo(() => {
    if (isLoading) {
      return <p className={styles.outageEmpty}>Завантаження...</p>;
    }
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
  }, [hasData, outageRanges, isLoading]);

  return (
    <>
      <div className={styles.widgetWrapper}> {/* можна додати свій стиль, якщо треба */}
        <div className={`${styles.outageCard} ${isLoading ? styles.faded : ""}`}>
          <div className={styles.cardHeader}>
            <div>
              <p className={styles.label}>Години без світла</p>
              <p className={styles.copy}>Черга {queueLabel}</p>
            </div>
          </div>

          <div className={styles.outageList}>{outageContent}</div>

          <div style={{ textAlign: "center", marginTop: "12px", fontSize: "0.85em" }}>
            <Link to="/graph" className={styles.faqLink}>
              Повний графік →
            </Link>
          </div>
        </div>
      </div>
      <script async="async" data-cfasync="false" src="https://pl28354173.effectivegatecpm.com/f756b89b922a64931ef1bbcf889211f7/invoke.js"></script>
    <div id="container-f756b89b922a64931ef1bbcf889211f7"></div>
    </>
  );
}

export default Widget;
/**
 * @typedef {Object} StatusResponse
 * @property {number[]} Status
 * @property {number} [Count]
 */

const container = document.getElementsByClassName("status-conainer")[0];
const timeContainer = document.getElementsByClassName("time-container")[0];
const queueSelector = document.getElementById("queueSelector");
const refreshQueue = document.getElementsByClassName("refresh-queue")[0];
const rowContainer = document.getElementsByClassName("row-container")[0];
const queueToggle = document.getElementById("queueToggle");
const outageList = document.getElementById("outageList");
const outageSummary = document.getElementsByClassName("outage-summary")[0];
const unsubscribeBtn = document.getElementById("unsubscribe");
const infoScrollBtn = document.getElementById("showInfo");
const scrollTopBtn = document.getElementById("scrollTopBtn");
const infoContainer = document.querySelector(".info-container");
const InfoBtnContainer = document.querySelector(".btn-container");

const lampOffSvg = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor"fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6" /><path d="M10 21h4" /><path d="M8 15a6 6 0 1 1 8 0l-1 1.5H9z" /><line x1="5" y1="5" x2="19" y2="19" /></svg>';

(async () => {
  displayOff();

  loadSettings();

  const publicKey = (await (await fetch(`/vapid_public_key`)).json()).key;

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
    return outputArray;
  }

  const button = document.getElementById("subscribe");
  if (button) {
    button.onclick = async () => {
      const reg = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;

      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });

      const payload  = {
        queue: queueSelector.value,
        subscription
      }

      const answer = await fetch(`/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const result = await answer.json();
      const msg = result?.msg || (result?.ok ? "ok" : "err");
      const value = queueSelector.value; 
      const Qvalue = value[0] + "." + value[1];
      alert(msg + " " + Qvalue);
    };
  }

  if (unsubscribeBtn) {
    unsubscribeBtn.onclick = async () => {
      const reg = await navigator.serviceWorker.register("/sw.js");
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
        const answer = await fetch(`/unsubscribe`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const result = await answer.json();
        alert(result?.msg || (result?.ok ? "Підписку скасовано" : "Помилка"));
      } catch (e) {
        alert("Не вдалося скасувати підписку.");
      }

      try {
        await currentSub.unsubscribe();
      } catch (_) {
        /* ignore */
      }
    };
  }

  if (queueToggle.checked) {
    enableAltDisplay();
  }
  else {
    displayOn();
  }

  await renderTable(queueSelector.value);

  queueSelector.addEventListener('change', async () => {
    saveSettings();
    await renderTable(queueSelector.value);
  });

  queueToggle.addEventListener('change', async () => {
    changeQueueType();
    saveSettings();
  });

  refreshQueue.addEventListener('click', async () => {
    await renderTable(queueSelector.value);
  });

  if (infoScrollBtn) {
    infoScrollBtn.addEventListener('click', () => {
      if (!infoContainer) return;
      infoContainer.scrollIntoView({ behavior: "smooth" });
    });
  }

  if (scrollTopBtn) {
    scrollTopBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  await sleep(3000);
  await InfoBtnAnim();

  async function InfoBtnAnim() {
    InfoBtnContainer.classList.add("finished");
    await sleep(700);
    infoScrollBtn.classList.add("finished");
  }

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async function getQueue(queue) {
    const result = await fetch(`/status?queue=${queue}`);
    /** @type {StatusResponse} */
    const json = await result.json();
  
    return Array.isArray(json.Status) ? json.Status : [];
  }

  async function renderTable(queue) {
    displaySvitcher();
    clearTable();
    const data = await getQueue(queue);

    let html = ``;
    const normalizedStatuses = [];
  
    const len = data.length;
    const hasData = len > 0;

    for (let h = 0; h < 24; h++) {
      let left = 0, right = 0;
  
      if (len >= 48) {
        left = Number(Boolean(data[h * 2] ?? 0));
        right = Number(Boolean(data[h * 2 + 1] ?? 0));
      } else if (len === 24) {
        const v = Number(Boolean(data[h] ?? 0));
        left = v; right = v;
      } else if (len > 0) {
        left = Number(Boolean(data[Math.min(h * 2, len - 1)] ?? 0));
        right = Number(Boolean(data[Math.min(h * 2 + 1, len - 1)] ?? 0));
      }
  
      const cellL = `<div class="status ${left === 1 ? "off" : ""}">${left === 1 ? lampOffSvg : ""}</div>`;
      const cellR = `<div class="status ${right === 1 ? "off" : ""}">${right === 1 ? lampOffSvg : ""}</div>`;
      html += `<div class="status-element">${cellL}${cellR}</div>`;

      normalizedStatuses.push(left === 1);
      normalizedStatuses.push(right === 1);
    }
  
    container.innerHTML = html;
    renderOutageSummary(hasData ? normalizedStatuses : []);
    displaySvitcher();
  }

  function clearTable() {
    if (!queueToggle.checked) {
      container.innerHTML = "";
    }
    else {
      outageList.innerHTML = "";
    }
  }

  /**
   * @param {boolean[]} statuses
   */
  function renderOutageSummary(statuses) {
    if (!outageList) return;
    if (!Array.isArray(statuses) || statuses.length === 0) {
      outageList.innerHTML = `<p class="outage-empty">Немає даних по графіку</p>`;
      return;
    }

    const ranges = collectOutageRanges(statuses);

    if (ranges.length === 0) {
      outageList.innerHTML = `<p class="outage-empty">Сьогодні відключень не планується</p>`;
      return;
    }

    const items = ranges
      .map(({ start, end }) => `<div class="outage-chip">${start}–${end}</div>`)
      .join("");

    outageList.innerHTML = items;
  }

  /**
   * @param {boolean[]} statuses
   * @returns {{start: string, end: string}[]}
   */
  function collectOutageRanges(statuses) {
    /** @type {{start: number, end: number}[]} */
    const ranges = [];
    let start = null;

    for (let i = 0; i <= statuses.length; i++) {
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

  function formatHalfHour(index) {
    if (index >= 48) return "24:00";
    const hours = Math.floor(index / 2);
    const minutes = index % 2 === 0 ? "00" : "30";
    return `${String(hours).padStart(2, "0")}:${minutes}`;
  }

  function displaySvitcher() {
    if (!queueToggle.checked) {
      rowContainer.classList.toggle("disp");
    }
    else {
      outageSummary.classList.toggle("disp");
    }
  }

  function displayOff() {
    if (!queueToggle.checked) {
      rowContainer.classList.add("disp");
    }
    else {
      outageSummary.classList.add("disp");
    }
  }

  function displayOn() {
    if (!queueToggle.checked) {
      rowContainer.classList.remove("disp");
    }
    else {
      outageSummary.classList.remove("disp");
    }
  }

  function changeQueueType() {
    rowContainer.classList.toggle("disp");
    outageSummary.classList.toggle("disp");
  }

  function enableAltDisplay() {
    outageSummary.classList.remove("disp");
    if (!rowContainer.classList.contains("disp")) {
      rowContainer.classList.add("disp");
    }
  }

  function loadSettings() {
    let temp = localStorage.getItem("queueSelector") ?? "0";
    
    if (temp == "1" || temp == "0") {
      queueSelector.value = `3${Number(temp)+1}`;
    }
    else {
      queueSelector.value = temp;
    }

    const toggleValue = localStorage.getItem("queueToggle");
    queueToggle.checked = toggleValue === "true"; 
  }
  
  function saveSettings() {
    localStorage.setItem("queueSelector", queueSelector.value);
    localStorage.setItem("queueToggle", queueToggle.checked.toString());
  }
})();

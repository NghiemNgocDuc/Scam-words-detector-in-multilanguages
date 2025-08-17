// static/js/main.js

// 1) SpeechRecognition setup
if (!("SpeechRecognition" in window) && !("webkitSpeechRecognition" in window)) {
  alert("Trình duyệt của bạn không hỗ trợ Web Speech API.");
}

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();
recognition.lang = "vi-VN";
recognition.continuous = true;
recognition.interimResults = false;

// 2) Rolling conversation buffer
let conversationBuffer = [];

// 3) Web Audio API for dynamic beeps (with volume control)
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playBeep({ freq = 600, duration = 200, volume = 0.33 } = {}) {
  // create oscillator
  const oscillator = audioCtx.createOscillator();
  oscillator.type = "sine";
  oscillator.frequency.value = freq;

  // create gain node and set volume
  const gainNode = audioCtx.createGain();
  gainNode.gain.value = volume; // 1.0 = full volume, 0.33 ~ 1/3 volume

  // wire it up: oscillator → gain → speakers
  oscillator.connect(gainNode);
  gainNode.connect(audioCtx.destination);

  // play & stop
  oscillator.start();
  setTimeout(() => {
    oscillator.stop();
    oscillator.disconnect();
    gainNode.disconnect();
  }, duration);
}

// 4) DOM refs & state
const tbody = document.getElementById("risk-table-body");
const toggleButton = document.getElementById("toggle-button");
let listening = false;

// 5) Toggle listening on click
toggleButton.addEventListener("click", () =>
  listening ? stopListening() : startListening()
);

function startListening() {
  recognition.start();
  listening = true;
  toggleButton.textContent = "Stop Listening";
  toggleButton.classList.replace("btn-primary", "btn-danger");
}

function stopListening() {
  recognition.stop();
  listening = false;
  toggleButton.textContent = "Start Listening";
  toggleButton.classList.replace("btn-danger", "btn-primary");
}

// 6) Handle speech results
recognition.onresult = (event) => {
  for (let i = event.resultIndex; i < event.results.length; i++) {
    if (event.results[i].isFinal) {
      const snippet = event.results[i][0].transcript.trim();
      conversationBuffer.push(snippet);
      const mergedText = conversationBuffer.join(" ");
      fetch("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: mergedText, lang: "vi" })
      })
        .then((r) => r.json())
        .then(updateTable)
        .catch(console.error);
    }
  }
};

recognition.onerror = (err) => {
  console.error("SpeechRecognition error:", err);
  stopListening();
};

// 7) Update the table and trigger beep
function updateTable({ text, score, label, reasons }) {
  const status = label.toLowerCase();
  const badgeClass = {
    safe: "badge-success",
    caution: "badge-warning",
    scam: "badge-danger"
  }[status] || "badge-secondary";

  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${text}</td>
    <td>${score}</td>
    <td><span class="badge ${badgeClass}">${label}</span></td>
    <td>${reasons.join(", ")}</td>
  `;
  tbody.prepend(tr);

  if (status === "scam") {
    playBeep({ freq: 600, duration: 200, volume: 0.1 });
  }
}

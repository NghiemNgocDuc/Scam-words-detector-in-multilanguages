import time
import unicodedata
from collections import deque
import numpy as np

try:
    import librosa
except ImportError:
    librosa = None

from rules import rules_by_lang  # External rules file

def normalize_text(text: str) -> str:
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

def score_text(text: str, lang: str):
    norm_text = normalize_text(text)
    score = 0
    reasons = []

    if lang not in rules_by_lang:
        lang = "en"

    rules = rules_by_lang[lang]
    weights = {"HIGH": 40, "MED": 15, "NEG": -20}
    matched = []

    # Match keywords
    for level in ["HIGH", "MED", "NEG"]:
        for kw in rules[level]:
            norm_kw = normalize_text(kw)
            if norm_kw in norm_text:
                score += weights[level]
                matched.append((level, kw, weights[level]))

    # Guard phrases (contextual safety)
    guard_phrases = ["meeting", "agenda", "calendar", "as discussed"]
    for phrase in guard_phrases:
        if normalize_text(phrase) in norm_text:
            score -= 10
            matched.append(("GUARD", phrase, -10))

    score = max(0, min(score, 100))  # Clamp between 0 and 100

    # Keep top 1–2 reasons
    matched.sort(key=lambda x: abs(x[2]), reverse=True)
    reasons = [f"{lvl}: '{kw}'" for lvl, kw, _ in matched[:2]]

    return score, reasons

def heuristic_spoof_prob(audio_path: str) -> float:
    """Heuristic spoof detection based on spectral flatness + HF energy."""
    if librosa is None:
        return 0.05

    try:
        y, sr = librosa.load(audio_path, sr=None)
        S = np.abs(librosa.stft(y))
        flatness = librosa.feature.spectral_flatness(S=S)
        mean_flatness = float(np.mean(flatness))

        fft = np.fft.rfft(y)
        freqs = np.fft.rfftfreq(len(y), 1 / sr)
        hf_energy = np.sum(np.abs(fft)[freqs > 3000])
        total_energy = np.sum(np.abs(fft))
        hf_ratio = hf_energy / (total_energy + 1e-6)

        if mean_flatness > 0.3 and hf_ratio > 0.2:
            return 0.75
        else:
            return 0.05
    except Exception:
        return 0.05

class RiskService:
    def __init__(self):
        self.last_alert_ts = 0
        self.alert_window_sec = 10
        self.event_queue = deque()
        self.partial_buffer = []

    def on_transcript_event(self, text: str, lang: str, is_final: bool = False, audio_path: str = None):
        self.partial_buffer.append(text)
        merged_text = " ".join(self.partial_buffer)

        score, reasons = score_text(merged_text, lang)

        spoof_prob = 0.0
        if audio_path:
            spoof_prob = heuristic_spoof_prob(audio_path)
            if spoof_prob > 0.7:
                score = min(100, score + 20)
                reasons.append(f"ANTI-SPOOF: spoof_prob={spoof_prob:.2f}")

        if score >= 60:
            label = "Scam"
        elif score >= 30:
            label = "Caution"
        else:
            label = "Safe"

        if is_final:
            self.partial_buffer.clear()

        now = time.time()
        if label != "Safe" and (now - self.last_alert_ts) >= self.alert_window_sec:
            self.last_alert_ts = now
            self.emit_risk_event(merged_text, lang, score, label, reasons, is_final)

    def emit_risk_event(self, text, lang, score, label, reasons, is_final):
        status = "FINAL" if is_final else "PARTIAL"
        print(f"[{status} RISK ALERT] lang={lang} score={score} label={label}")
        for reason in reasons:
            print(f"Reason: → {reason}")
        print(f"Text: {text}\n")

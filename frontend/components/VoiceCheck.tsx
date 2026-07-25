"use client";

import { useEffect, useRef, useState } from "react";
import type { ComprehensionResult, DAGNode } from "@/types/dag";

interface Props {
  node: DAGNode;
  sessionId: string;
  onResult: (result: ComprehensionResult) => void;
  onClose: () => void;
}

type Phase = "idle" | "speaking-question" | "recording" | "scoring" | "done";

export default function VoiceCheck({ node, sessionId, onResult, onClose }: Props) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<ComprehensionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [transcribedText, setTranscribedText] = useState<string>("");
  const [manualText, setManualText] = useState<string>("");
  const [showTextInput, setShowTextInput] = useState<boolean>(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recognitionRef = useRef<any>(null);
  const liveTranscriptRef = useRef<string>("");

  const elevenKey = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY ?? "";
  const voiceId = process.env.NEXT_PUBLIC_ELEVENLABS_VOICE_ID ?? "21m00Tcm4TlvDq8ikWAM";

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch {}
      }
    };
  }, []);

  async function speakQuestion() {
    setPhase("speaking-question");
    setError(null);
    const question = `Explain the following in your own words: ${node.success_criteria}`;

    if (elevenKey) {
      try {
        const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
          method: "POST",
          headers: { "xi-api-key": elevenKey, "Content-Type": "application/json" },
          body: JSON.stringify({
            text: question,
            model_id: "eleven_multilingual_v2",
            voice_settings: { stability: 0.5, similarity_boost: 0.75 },
          }),
        });
        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.onended = () => { URL.revokeObjectURL(url); startRecording(); };
          await audio.play();
          return;
        }
      } catch {
        // ElevenLabs TTS failed — fall through to recording
      }
    }

    // No ElevenLabs key or TTS failed — skip straight to recording
    startRecording();
  }

  async function startRecording() {
    setError(null);
    liveTranscriptRef.current = "";
    setTranscribedText("");
    chunksRef.current = [];

    // Web Speech API browser fallback if available
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = "en-US";
        rec.onresult = (event: any) => {
          let current = "";
          for (let i = 0; i < event.results.length; i++) {
            current += event.results[i][0].transcript + " ";
          }
          liveTranscriptRef.current = current.trim();
          setTranscribedText(current.trim());
        };
        rec.start();
        recognitionRef.current = rec;
      } catch (err) {
        console.warn("Web Speech API initialization warning:", err);
      }
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setPhase("recording");

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4")
        ? "audio/mp4"
        : "";

      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        if (recognitionRef.current) {
          try { recognitionRef.current.stop(); } catch {}
        }
        transcribeAndScore();
      };

      // Request data every 100ms to ensure chunks arrive
      recorder.start(100);
    } catch (err) {
      console.error("Microphone access error:", err);
      setError(
        "Microphone access was denied or unavailable. Please allow microphone access in your browser " +
        "(look for the mic icon in the address bar) or type your answer below."
      );
      setShowTextInput(true);
      setPhase("idle");
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  }

  async function transcribeAndScore(overrideText?: string) {
    setPhase("scoring");
    setError(null);

    let finalAnswer = overrideText !== undefined ? overrideText : "";

    if (!finalAnswer) {
      // 1. Try ElevenLabs STT API if audio chunks were captured
      if (elevenKey && chunksRef.current.length > 0) {
        try {
          const mimeType = (mediaRecorderRef.current as any)?.mimeType || "audio/webm";
          const audioBlob = new Blob(chunksRef.current, { type: mimeType });

          const form = new FormData();
          // ElevenLabs STT expects parameter "file", not "audio"
          form.append("file", audioBlob, mimeType.includes("mp4") ? "answer.mp4" : "answer.webm");
          form.append("model_id", "scribe_v1");

          const sttRes = await fetch("https://api.elevenlabs.io/v1/speech-to-text", {
            method: "POST",
            headers: { "xi-api-key": elevenKey },
            body: form,
          });

          if (sttRes.ok) {
            const sttData = await sttRes.json();
            if (sttData.text) {
              finalAnswer = sttData.text.trim();
            }
          } else {
            const errBody = await sttRes.text();
            console.error("ElevenLabs STT HTTP error:", sttRes.status, errBody);
          }
        } catch (err) {
          console.error("ElevenLabs STT fetch exception:", err);
        }
      }

      // 2. Fallback to Web Speech API live transcript if ElevenLabs yielded empty
      if (!finalAnswer && liveTranscriptRef.current) {
        finalAnswer = liveTranscriptRef.current;
      }
    }

    setTranscribedText(finalAnswer);

    if (!finalAnswer && !showTextInput) {
      setShowTextInput(true);
      setError("No spoken answer was detected. Please type your explanation below or try recording again.");
      setPhase("idle");
      return;
    }

    try {
      const scoreRes = await fetch("/api/comprehension/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          node_id: node.id,
          success_criteria: node.success_criteria,
          transcribed_answer: finalAnswer,
          session_id: sessionId,
        }),
      });

      if (!scoreRes.ok) {
        throw new Error(`Backend returned ${scoreRes.status}`);
      }

      const comprehension: ComprehensionResult = await scoreRes.json();
      setResult(comprehension);
      setPhase("done");
      onResult(comprehension);

      // Post-step: speak feedback aloud
      if (elevenKey && comprehension.feedback) {
        try {
          const ttsRes = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
            method: "POST",
            headers: { "xi-api-key": elevenKey, "Content-Type": "application/json" },
            body: JSON.stringify({
              text: comprehension.feedback,
              model_id: "eleven_multilingual_v2",
              voice_settings: { stability: 0.5, similarity_boost: 0.75 },
            }),
          });
          if (ttsRes.ok) {
            const fb = await ttsRes.blob();
            const url = URL.createObjectURL(fb);
            const audio = new Audio(url);
            audio.onended = () => URL.revokeObjectURL(url);
            audio.play();
          }
        } catch {}
      }
    } catch (err) {
      console.error("Comprehension score request failed:", err);
      setError("Could not reach the scoring server. Make sure the backend is running on port 8000.");
      setPhase("idle");
    }
  }

  function resetCheck() {
    setPhase("idle");
    setResult(null);
    setError(null);
    setTranscribedText("");
    setManualText("");
    setShowTextInput(false);
    chunksRef.current = [];
    liveTranscriptRef.current = "";
  }

  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
      }}
    >
      <div style={{
        background: "#1e293b", borderRadius: 14, padding: 32, maxWidth: 480,
        width: "90%", color: "#f1f5f9", position: "relative",
      }}>
        <button
          onClick={onClose}
          style={{
            position: "absolute", top: 14, right: 14, background: "none",
            border: "none", color: "#64748b", fontSize: 22, cursor: "pointer",
            lineHeight: 1, padding: 4, borderRadius: 4,
          }}
          title="Close"
        >
          ✕
        </button>

        <h2 style={{ marginBottom: 6, fontSize: 20, fontWeight: 700 }}>Comprehension Check</h2>
        <p style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>{node.title}</p>

        <div style={{
          background: "#0f172a", borderRadius: 8, padding: "12px 16px",
          marginBottom: 24, borderLeft: "3px solid #3b82f6",
        }}>
          <strong style={{
            fontSize: 11, color: "#64748b", display: "block",
            marginBottom: 6, letterSpacing: 1, textTransform: "uppercase",
          }}>
            Question
          </strong>
          <p style={{ fontSize: 14, lineHeight: 1.7, margin: 0 }}>{node.success_criteria}</p>
        </div>

        {error && (
          <div style={{
            background: "#ef444422", border: "1px solid #ef444466",
            borderRadius: 8, padding: "10px 14px", marginBottom: 16,
            fontSize: 13, color: "#fca5a5", lineHeight: 1.5,
          }}>
            {error}
          </div>
        )}

        {transcribedText && phase !== "idle" && (
          <div style={{
            background: "#0f172a", borderRadius: 8, padding: "10px 14px",
            marginBottom: 16, border: "1px solid #334155",
          }}>
            <strong style={{ fontSize: 11, color: "#94a3b8", display: "block", marginBottom: 4 }}>
              Transcribed Answer:
            </strong>
            <p style={{ fontSize: 13, color: "#e2e8f0", margin: 0, fontStyle: "italic" }}>
              "{transcribedText}"
            </p>
          </div>
        )}

        {showTextInput && phase === "idle" && (
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 6 }}>
              Type your explanation:
            </label>
            <textarea
              value={manualText}
              onChange={(e) => setManualText(e.target.value)}
              rows={3}
              placeholder="Type your explanation here..."
              style={{
                width: "100%", padding: 10, borderRadius: 8, background: "#0f172a",
                border: "1px solid #334155", color: "#f8fafc", fontSize: 14, resize: "vertical",
                marginBottom: 10, outline: "none",
              }}
            />
            <button
              onClick={() => transcribeAndScore(manualText)}
              disabled={!manualText.trim()}
              style={{
                ...btnStyle(manualText.trim() ? "#10b981" : "#475569"),
                width: "100%", cursor: manualText.trim() ? "pointer" : "not-allowed",
              }}
            >
              Submit Typed Answer
            </button>
          </div>
        )}

        {phase === "idle" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <button onClick={speakQuestion} style={btnStyle("#3b82f6")}>
              {elevenKey ? "🎙 Start Voice Check" : "🎙 Start Recording"}
            </button>
            {!showTextInput && (
              <button
                onClick={() => setShowTextInput(true)}
                style={{
                  background: "transparent", color: "#94a3b8", border: "1px solid #334155",
                  borderRadius: 8, padding: "8px 16px", cursor: "pointer", fontSize: 13,
                }}
              >
                ✏️ Or type answer manually
              </button>
            )}
          </div>
        )}

        {phase === "speaking-question" && (
          <div style={{ color: "#f59e0b", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20 }}>🔊</span>
            <span>Reading question aloud… speak your answer once it finishes.</span>
          </div>
        )}

        {phase === "recording" && (
          <div>
            <div style={{
              color: "#ef4444", marginBottom: 16,
              display: "flex", alignItems: "center", gap: 10,
            }}>
              <span style={{ fontSize: 16 }}>●</span>
              <span>Recording — speak clearly, then click Stop when done.</span>
            </div>
            <button onClick={stopRecording} style={btnStyle("#ef4444")}>
              ■ Stop Recording
            </button>
          </div>
        )}

        {phase === "scoring" && (
          <p style={{ color: "#f59e0b", display: "flex", alignItems: "center", gap: 8 }}>
            <span>⏳</span> Scoring your answer…
          </p>
        )}

        {phase === "done" && result && (
          <div>
            <div style={{
              padding: "14px 16px", borderRadius: 8, marginBottom: 16,
              background: result.verdict === "pass" ? "#10b98122" : "#f59e0b22",
              border: `1px solid ${result.verdict === "pass" ? "#10b98155" : "#f59e0b55"}`,
            }}>
              <strong style={{ color: result.verdict === "pass" ? "#10b981" : "#f59e0b" }}>
                {result.verdict === "pass" ? "✓ Pass" : "⟳ Needs Review"}
              </strong>
              <p style={{ marginTop: 8, fontSize: 14, lineHeight: 1.6, margin: "8px 0 0" }}>
                {result.feedback}
              </p>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              {result.verdict === "needs_review" && (
                <button onClick={resetCheck} style={btnStyle("#3b82f6")}>
                  Try Again
                </button>
              )}
              <button onClick={onClose} style={btnStyle("#475569")}>
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function btnStyle(color: string): React.CSSProperties {
  return {
    background: color, color: "#fff", border: "none", borderRadius: 8,
    padding: "10px 20px", cursor: "pointer", fontSize: 14, fontWeight: 600,
  };
}

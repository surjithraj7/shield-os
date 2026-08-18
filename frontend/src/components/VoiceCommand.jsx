/**
 * FORGE3D Innovation #12: Voice Command Interface
 * Hands-free TBM parameter queries and navigation using Web Speech API
 */
import { useState, useEffect, useRef, useCallback } from "react";

const COMMANDS = {
  // Navigation
  "open twin": { action: "navigate", target: "win-twin", response: "Opening Digital Twin..." },
  "open dashboard": { action: "navigate", target: "win-dashboard", response: "Opening TBM Dashboard..." },
  "open settlement": { action: "navigate", target: "win-settlement", response: "Opening Settlement Chart..." },
  "open alerts": { action: "navigate", target: "win-alerts", response: "Opening Alerts Log..." },
  "open shm": { action: "navigate", target: "win-shm", response: "Opening SHM Monitor..." },
  "open anomaly": { action: "navigate", target: "win-anomaly", response: "Opening Anomaly Engine..." },
  "open geology": { action: "navigate", target: "win-geology", response: "Opening Geological View..." },
  "open cutter": { action: "navigate", target: "win-cutter", response: "Opening Cutter Wear AI..." },
  "open gis": { action: "navigate", target: "win-gis", response: "Opening GIS Map..." },
  "open ai": { action: "navigate", target: "win-ai", response: "Opening AI Assistant..." },
  "open autodrive": { action: "navigate", target: "win-autodrive", response: "Opening Autodrive..." },

  // Data queries
  "current ring": { action: "query", endpoint: "ring", response: "Retrieving current ring data..." },
  "current settlement": { action: "query", endpoint: "settlement", response: "Retrieving settlement data..." },
  "thrust force": { action: "query", endpoint: "thrust", response: "Retrieving thrust force..." },
  "torque": { action: "query", endpoint: "torque", response: "Retrieving torque data..." },
  "advance speed": { action: "query", endpoint: "advance", response: "Retrieving advance speed..." },
  "face pressure": { action: "query", endpoint: "face_pressure", response: "Retrieving face pressure..." },

  // System
  "help": { action: "help", response: "Available commands: open [twin/dashboard/settlement/alerts/shm/anomaly/geology/cutter/gis/ai/autodrive], current ring, current settlement, thrust force, torque, advance speed, face pressure, status, help, stop listening" },
  "status": { action: "status", response: "System status check..." },
  "stop listening": { action: "stop", response: "Voice command deactivated." },
};

export default function VoiceCommand({ onNavigate, onQuery, onToast }) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [lastCommand, setLastCommand] = useState(null);
  const [lastResponse, setLastResponse] = useState("");
  const [supported, setSupported] = useState(true);
  const recognitionRef = useRef(null);

  useEffect(() => {
    // Check Speech Recognition support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += t;
        } else {
          interimTranscript += t;
        }
      }

      setTranscript(interimTranscript || finalTranscript);

      if (finalTranscript) {
        processCommand(finalTranscript.trim().toLowerCase());
      }
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      if (event.error !== "no-speech") {
        setIsListening(false);
      }
    };

    recognition.onend = () => {
      // Restart if still supposed to be listening
      if (recognitionRef.current && isListening) {
        try {
          recognition.start();
        } catch (e) {
          // Already started
        }
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, []);

  const processCommand = useCallback((text) => {
    // Find matching command
    let matched = null;
    for (const [key, cmd] of Object.entries(COMMANDS)) {
      if (text.includes(key)) {
        matched = { key, ...cmd };
        break;
      }
    }

    if (matched) {
      setLastCommand(matched.key);
      setLastResponse(matched.response);

      if (matched.action === "navigate" && onNavigate) {
        onNavigate(matched.target);
      } else if (matched.action === "query" && onQuery) {
        onQuery(matched.endpoint);
      } else if (matched.action === "stop") {
        stopListening();
      } else if (matched.action === "help" || matched.action === "status") {
        // Response already set
      }

      if (onToast) onToast(`VOICE: ${matched.response}`, "ok");
    } else {
      setLastCommand(text);
      setLastResponse(`Unknown command: "${text}". Say "help" for options.`);
    }
  }, [onNavigate, onQuery, onToast]);

  const startListening = () => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.start();
      setIsListening(true);
      setLastResponse("Voice command activated. Say a command...");
      if (onToast) onToast("VOICE COMMAND ACTIVE", "ok");
    } catch (e) {
      console.error("Failed to start recognition:", e);
    }
  };

  const stopListening = () => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (e) {}
    setIsListening(false);
    setLastResponse("Voice command deactivated.");
    if (onToast) onToast("VOICE COMMAND DEACTIVATED", "ok");
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  if (!supported) {
    return (
      <div style={{ padding: "8px", color: "#ff4444", fontSize: "11px" }}>
        Voice commands not supported in this browser. Use Chrome or Edge.
      </div>
    );
  }

  return (
    <div className="voice-command" style={{ padding: "4px" }}>
      <div className="twin-hud">
        <div className="twin-hud-title">VOICE COMMANDS</div>
        <button
          onClick={toggleListening}
          style={{
            width: "100%",
            padding: "10px",
            background: isListening ? "#ff0044" : "#00cc66",
            color: "#fff",
            border: "none",
            cursor: "pointer",
            fontFamily: "Courier New",
            fontWeight: "bold",
            marginBottom: "8px",
          }}
        >
          {isListening ? "STOP LISTENING" : "START VOICE COMMANDS"}
        </button>

        {transcript && (
          <div className="twin-hud-row" style={{ fontStyle: "italic", color: "#aaa" }}>
            <span>HEARING:</span>
            <b>{transcript}</b>
          </div>
        )}

        {lastCommand && (
          <div className="twin-hud-row">
            <span>COMMAND:</span>
            <b style={{ color: "#ff00ff" }}>{lastCommand}</b>
          </div>
        )}

        {lastResponse && (
          <div className="twin-hud-row">
            <span>RESPONSE:</span>
            <b style={{ color: "#00ffff", fontSize: "10px" }}>{lastResponse}</b>
          </div>
        )}

        <div style={{ marginTop: "8px", fontSize: "9px", color: "#666", lineHeight: "1.5" }}>
          <div>SAY: "open twin" "open geology" "current ring"</div>
          <div>SAY: "thrust force" "settlement" "help"</div>
        </div>
      </div>
    </div>
  );
}

"use client";

import React from "react";
import {
  CastlingRights,
  EditorPieces,
  PRESET_POSITIONS,
  getEnPassantOptions,
  computeCastlingAvailability,
} from "@/lib/chess/fenEditor";

interface EditorControlsProps {
  turn: "w" | "b";
  castling: CastlingRights;
  enPassant: string;
  pieces: EditorPieces;
  onTurnChange: (turn: "w" | "b") => void;
  onCastlingChange: (castling: CastlingRights) => void;
  onEnPassantChange: (ep: string) => void;
  onPreset: (fen: string) => void;
  onStartingPosition: () => void;
  onClearBoard: () => void;
  onFlipBoard: () => void;
  onAnalysisBoard: () => void;
  onContinueFromHere: () => void;
  onStudy: () => void;
}

const sectionStyle: React.CSSProperties = {
  marginBottom: "12px",
};

const labelStyle: React.CSSProperties = {
  color: "#aaa",
  fontSize: "12px",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: "6px",
  display: "block",
};

const btnStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 12px",
  marginBottom: "6px",
  border: "1px solid #555",
  borderRadius: "4px",
  backgroundColor: "#333",
  color: "#ddd",
  fontSize: "13px",
  cursor: "pointer",
  textAlign: "center",
  fontWeight: 500,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  transition: "background-color 0.15s",
};

const selectStyle: React.CSSProperties = {
  width: "100%",
  padding: "6px 8px",
  backgroundColor: "#333",
  color: "#ddd",
  border: "1px solid #555",
  borderRadius: "4px",
  fontSize: "13px",
  marginBottom: "4px",
};

export default function EditorControls({
  turn,
  castling,
  enPassant,
  pieces,
  onTurnChange,
  onCastlingChange,
  onEnPassantChange,
  onPreset,
  onStartingPosition,
  onClearBoard,
  onFlipBoard,
  onAnalysisBoard,
  onContinueFromHere,
  onStudy,
}: EditorControlsProps) {
  const epOptions = getEnPassantOptions(pieces, turn);
  const castlingAvail = computeCastlingAvailability(pieces);

  return (
    <div
      style={{
        padding: "12px",
        backgroundColor: "#1e1e1e",
        borderRadius: "6px",
        border: "1px solid #333",
        minWidth: "220px",
      }}
    >
      {/* Set the board */}
      <div style={sectionStyle}>
        <label style={labelStyle}>Set the board</label>
        <select
          style={selectStyle}
          onChange={(e) => {
            const fen = PRESET_POSITIONS[e.target.value];
            if (fen) onPreset(fen);
          }}
          defaultValue=""
        >
          <option value="" disabled>
            Choose a position...
          </option>
          {Object.keys(PRESET_POSITIONS).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {/* Variant */}
      <div style={sectionStyle}>
        <label style={labelStyle}>Variant</label>
        <select style={selectStyle} value="standard" disabled>
          <option value="standard">Standard</option>
        </select>
      </div>

      {/* Color to play */}
      <div style={sectionStyle}>
        <label style={labelStyle}>Color to play</label>
        <div style={{ display: "flex", gap: "12px" }}>
          <label
            style={{
              color: "#ddd",
              fontSize: "13px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <input
              type="radio"
              name="turn"
              checked={turn === "w"}
              onChange={() => onTurnChange("w")}
            />
            White
          </label>
          <label
            style={{
              color: "#ddd",
              fontSize: "13px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <input
              type="radio"
              name="turn"
              checked={turn === "b"}
              onChange={() => onTurnChange("b")}
            />
            Black
          </label>
        </div>
      </div>

      {/* Castling */}
      <div style={sectionStyle}>
        <label style={labelStyle}>Castling</label>

        {/* White castling */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginBottom: "4px",
          }}
        >
          <span style={{ color: "#999", fontSize: "12px", width: "40px" }}>
            White
          </span>
          <label
            style={{
              color: castlingAvail.whiteOOPossible ? "#ddd" : "#666",
              fontSize: "13px",
              cursor: castlingAvail.whiteOOPossible ? "pointer" : "default",
              display: "flex",
              alignItems: "center",
              gap: "3px",
            }}
          >
            <input
              type="checkbox"
              checked={castling.whiteOO}
              disabled={!castlingAvail.whiteOOPossible}
              onChange={(e) =>
                onCastlingChange({ ...castling, whiteOO: e.target.checked })
              }
            />
            O-O
          </label>
          <label
            style={{
              color: castlingAvail.whiteOOOPossible ? "#ddd" : "#666",
              fontSize: "13px",
              cursor: castlingAvail.whiteOOOPossible ? "pointer" : "default",
              display: "flex",
              alignItems: "center",
              gap: "3px",
            }}
          >
            <input
              type="checkbox"
              checked={castling.whiteOOO}
              disabled={!castlingAvail.whiteOOOPossible}
              onChange={(e) =>
                onCastlingChange({ ...castling, whiteOOO: e.target.checked })
              }
            />
            O-O-O
          </label>
        </div>

        {/* Black castling */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span style={{ color: "#999", fontSize: "12px", width: "40px" }}>
            Black
          </span>
          <label
            style={{
              color: castlingAvail.blackOOPossible ? "#ddd" : "#666",
              fontSize: "13px",
              cursor: castlingAvail.blackOOPossible ? "pointer" : "default",
              display: "flex",
              alignItems: "center",
              gap: "3px",
            }}
          >
            <input
              type="checkbox"
              checked={castling.blackOO}
              disabled={!castlingAvail.blackOOPossible}
              onChange={(e) =>
                onCastlingChange({ ...castling, blackOO: e.target.checked })
              }
            />
            O-O
          </label>
          <label
            style={{
              color: castlingAvail.blackOOOPossible ? "#ddd" : "#666",
              fontSize: "13px",
              cursor: castlingAvail.blackOOOPossible ? "pointer" : "default",
              display: "flex",
              alignItems: "center",
              gap: "3px",
            }}
          >
            <input
              type="checkbox"
              checked={castling.blackOOO}
              disabled={!castlingAvail.blackOOOPossible}
              onChange={(e) =>
                onCastlingChange({ ...castling, blackOOO: e.target.checked })
              }
            />
            O-O-O
          </label>
        </div>
      </div>

      {/* En passant */}
      <div style={sectionStyle}>
        <label style={labelStyle}>En passant</label>
        <select
          style={selectStyle}
          value={enPassant}
          onChange={(e) => onEnPassantChange(e.target.value)}
        >
          <option value="-">-</option>
          {epOptions.map((sq) => (
            <option key={sq} value={sq}>
              {sq}
            </option>
          ))}
        </select>
      </div>

      {/* Action buttons */}
      <div style={{ marginTop: "16px" }}>
        <button
          style={btnStyle}
          onClick={onStartingPosition}
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor = "#444")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor = "#333")
          }
        >
          Starting Position
        </button>
        <button
          style={btnStyle}
          onClick={onClearBoard}
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor = "#444")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor = "#333")
          }
        >
          Clear Board
        </button>
        <button
          style={btnStyle}
          onClick={onFlipBoard}
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor = "#444")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor = "#333")
          }
        >
          Flip Board
        </button>
        <button
          style={{
            ...btnStyle,
            backgroundColor: "#1b5e20",
            borderColor: "#2e7d32",
          }}
          onClick={onAnalysisBoard}
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor = "#2e7d32")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor = "#1b5e20")
          }
        >
          Analysis Board &rarr;
        </button>
        <button
          style={{
            ...btnStyle,
            backgroundColor: "#0d47a1",
            borderColor: "#1565c0",
          }}
          onClick={onContinueFromHere}
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor = "#1565c0")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor = "#0d47a1")
          }
        >
          Continue from here &rarr;
        </button>
        <button
          style={{
            ...btnStyle,
            backgroundColor: "#4a148c",
            borderColor: "#6a1b9a",
          }}
          onClick={onStudy}
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor = "#6a1b9a")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor = "#4a148c")
          }
        >
          Study &rarr;
        </button>
      </div>
    </div>
  );
}

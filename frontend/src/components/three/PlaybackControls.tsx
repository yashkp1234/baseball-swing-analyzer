import { useCallback, useRef, useState } from "react";
import { Slider } from "@/components/ui/Slider";

interface PlaybackControlsProps {
  currentFrame: number;
  totalFrames: number;
  fps: number;
  isPlaying: boolean;
  speed: number;
  onFrameSelect: (frame: number) => void;
  onPlayPause: () => void;
  onSpeedChange: (speed: number) => void;
  phaseLabels: string[];
  contactFrame: number;
}

const SPEEDS = [0.25, 0.5, 1, 2];

export function PlaybackControls({
  currentFrame,
  totalFrames,
  fps,
  isPlaying,
  speed,
  onFrameSelect,
  onPlayPause,
  onSpeedChange,
  phaseLabels,
  contactFrame,
}: PlaybackControlsProps) {
  const currentPhase = phaseLabels[currentFrame] ?? "";
  const timeSeconds = (currentFrame / fps).toFixed(2);

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 space-y-3">
      <div className="flex items-center gap-4">
        <button
          onClick={onPlayPause}
          className="w-10 h-10 rounded-full bg-[var(--color-accent)] text-[var(--color-bg)] flex items-center justify-center font-bold text-lg hover:brightness-110 transition-all"
        >
          {isPlaying ? "⏸" : "▶"}
        </button>

        <div className="flex-1">
          <Slider
            min={0}
            max={totalFrames - 1}
            value={currentFrame}
            onChange={onFrameSelect}
          />
        </div>

        <span className="text-sm font-mono text-[var(--color-text-dim)] min-w-[80px] text-right">
          {timeSeconds}s / {(totalFrames / fps).toFixed(1)}s
        </span>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--color-text-dim)]">Speed:</span>
          {SPEEDS.map((s) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={`px-2 py-0.5 rounded text-xs ${
                speed === s
                  ? "bg-[var(--color-accent)] text-[var(--color-bg)]"
                  : "bg-[var(--color-surface-2)] text-[var(--color-text-dim)]"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 text-xs text-[var(--color-text-dim)]">
          <span>Frame {currentFrame}/{totalFrames - 1}</span>
          <span
            className="px-2 py-0.5 rounded-full"
            style={{
              backgroundColor: {
                stance: "#4A90D9", load: "#00CC6A", stride: "#D4A017",
                swing: "#00FF87", contact: "#FFD700", follow_through: "#FF8A00",
              }[currentPhase] || "#555",
              color: "#000",
            }}
          >
            {currentPhase}
          </span>
        </div>
      </div>
    </div>
  );
}
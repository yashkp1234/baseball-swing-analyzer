import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

interface VideoPlayerProps {
  src: string;
  fps: number;
  selectedFrame?: number;
  onFrameChange?: (frame: number) => void;
  className?: string;
}

export interface VideoPlayerHandle {
  seekToSeconds: (seconds: number) => void;
}

function frameToTime(frame: number, fps: number): number {
  if (fps <= 0) return 0;
  return Math.max(frame, 0) / fps;
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(function VideoPlayer(
  { src, fps, selectedFrame, onFrameChange, className },
  ref,
) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const lastAppliedFrameRef = useRef<number | null>(null);
  const lastReportedFrameRef = useRef<number | null>(null);

  useImperativeHandle(ref, () => ({
    seekToSeconds(seconds: number) {
      const video = videoRef.current;
      if (!video || !Number.isFinite(seconds)) return;
      video.currentTime = Math.max(0, seconds);
    },
  }));

  useEffect(() => {
    const video = videoRef.current;
    if (!video || selectedFrame === undefined || fps <= 0) return;

    const nextTime = frameToTime(selectedFrame, fps);
    const timeDelta = Math.abs(video.currentTime - nextTime);
    const tolerance = 0.5 / fps;

    if (timeDelta <= tolerance && lastAppliedFrameRef.current === selectedFrame) {
      return;
    }

    if (video.readyState > 0) {
      video.currentTime = nextTime;
      lastAppliedFrameRef.current = selectedFrame;
    }
  }, [fps, selectedFrame]);

  return (
    <video
      ref={videoRef}
      src={src}
      controls
      onLoadedMetadata={() => {
        const video = videoRef.current;
        if (!video || selectedFrame === undefined || fps <= 0) return;
        video.currentTime = frameToTime(selectedFrame, fps);
        lastAppliedFrameRef.current = selectedFrame;
      }}
      onTimeUpdate={() => {
        const video = videoRef.current;
        if (!video || fps <= 0) return;
        const frame = Math.max(0, Math.round(video.currentTime * fps));
        if (lastReportedFrameRef.current === frame) return;
        lastReportedFrameRef.current = frame;
        onFrameChange?.(frame);
      }}
      className={`w-full rounded-lg bg-black ${className ?? ""}`}
      style={{ maxHeight: "480px" }}
    />
  );
});

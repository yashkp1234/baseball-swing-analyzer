import { useRef } from "react";

interface VideoPlayerProps {
  src: string;
  className?: string;
}

export function VideoPlayer({ src, className }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  return (
    <video
      ref={videoRef}
      src={src}
      controls
      className={`w-full rounded-lg bg-black ${className ?? ""}`}
      style={{ maxHeight: "480px" }}
    />
  );
}

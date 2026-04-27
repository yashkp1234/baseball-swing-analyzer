import { useRef, useState, type DragEvent } from "react";
import { ArrowUpFromLine, Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  isUploading: boolean;
}

export function UploadZone({ onFileSelected, isUploading }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (event: DragEvent) => {
    event.preventDefault();
    setIsDragOver(false);
    const file = event.dataTransfer.files[0];
    if (file && file.type.startsWith("video/")) {
      onFileSelected(file);
    }
  };

  const handleDragOver = (event: DragEvent) => {
    event.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => setIsDragOver(false);
  const handleClick = () => inputRef.current?.click();

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) onFileSelected(file);
  };

  return (
    <div
      onClick={handleClick}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={cn(
        "group flex min-h-72 cursor-pointer flex-col items-center justify-center gap-5 rounded-[28px] border-2 border-dashed p-10 text-center transition-all duration-200 md:min-h-80 md:p-14",
        isDragOver
          ? "border-[var(--color-accent)] bg-[var(--color-accent)]/8 shadow-[0_0_0_1px_rgba(0,255,135,0.15)]"
          : "border-[var(--color-border)] bg-[var(--color-surface)]/75 hover:border-[var(--color-accent)]/55 hover:bg-[var(--color-surface)]",
        isUploading && "pointer-events-none opacity-60",
      )}
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-accent)] transition-transform duration-200 group-hover:scale-105">
        {isUploading ? <Upload className="h-7 w-7 animate-pulse" /> : <ArrowUpFromLine className="h-7 w-7" />}
      </div>

      <div>
        <p className="text-2xl font-semibold text-[var(--color-text)] md:text-3xl">
          {isUploading ? "Uploading your swing..." : "Drop your swing video here"}
        </p>
        <p className="mt-2 text-sm leading-6 text-[var(--color-text-dim)] md:text-base">
          Drag and drop or click to browse. MP4, MOV, and AVI clips work well.
        </p>
      </div>

      <div className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-4 py-2 text-xs font-medium text-[var(--color-text-dim)]">
        Full-body side view works best
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        onChange={handleChange}
        className="hidden"
      />
    </div>
  );
}

import { useRef, useState, type DragEvent } from "react";
import { Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  isUploading: boolean;
}

export function UploadZone({ onFileSelected, isUploading }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("video/")) {
      onFileSelected(file);
    }
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => setIsDragOver(false);

  const handleClick = () => inputRef.current?.click();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
  };

  return (
    <div
      onClick={handleClick}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-12 cursor-pointer transition-all duration-200",
        isDragOver
          ? "border-[var(--color-accent)] bg-[var(--color-accent)]/5"
          : "border-[var(--color-border)] hover:border-[var(--color-text-dim)]",
        isUploading && "pointer-events-none opacity-50"
      )}
    >
      <Upload className="h-10 w-10 text-[var(--color-text-dim)]" />
      <div className="text-center">
        <p className="text-lg font-medium text-[var(--color-text)]">
          {isUploading ? "Uploading..." : "Drop your swing video here"}
        </p>
        <p className="text-sm text-[var(--color-text-dim)] mt-1">
          or click to browse — MP4, MOV, AVI supported
        </p>
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
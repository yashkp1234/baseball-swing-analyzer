interface SliderComponentProps {
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
}

export function Slider({ min, max, value, onChange }: SliderComponentProps) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className="relative h-2 w-full cursor-pointer" onClick={(e) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      onChange(Math.round(min + x * (max - min)));
    }}>
      <div className="absolute inset-0 rounded-full bg-[var(--color-surface-2)]" />
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-[var(--color-accent)]"
        style={{ width: `${pct}%` }}
      />
      <div
        className="absolute top-1/2 w-3 h-3 rounded-full bg-white border-2 border-[var(--color-accent)]"
        style={{ left: `${pct}%`, transform: `translate(-50%, -50%)` }}
      />
    </div>
  );
}
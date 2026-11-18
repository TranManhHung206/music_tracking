export interface SegmentedOption<T extends string> {
  id: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
  size?: 'sm' | 'md';
  className?: string;
}

/** Bộ chuyển lựa chọn dạng tab chuẩn WAI-ARIA tablist. */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
  size = 'md',
  className = '',
}: SegmentedControlProps<T>) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={`inline-flex items-center p-1 rounded-xl bg-obsidian-bg border border-obsidian-border ${className}`}
    >
      {options.map((opt) => {
        const isActive = opt.id === value;
        return (
          <button
            key={opt.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => {
              if (opt.id !== value) {
                onChange(opt.id);
              }
            }}
            className={`rounded-lg font-bold transition-all cursor-pointer flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green ${
              size === 'sm' ? 'h-7 px-2.5 text-xs' : 'h-7 px-3 sm:px-3.5 text-xs'
            } ${
              isActive
                ? 'bg-spotify-green text-black shadow-md shadow-spotify-green/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

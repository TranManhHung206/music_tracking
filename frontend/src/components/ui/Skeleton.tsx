import React from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-lg bg-slate-800/75 ${className}`}
    />
  );
};

export const ChartCardSkeleton: React.FC<{ heightClass?: string }> = ({
  heightClass = 'h-64',
}) => {
  return (
    <div className="w-full space-y-4" aria-busy="true" aria-label="Đang tải dữ liệu biểu đồ">
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-2 flex-1">
          <Skeleton className="h-5 w-48 max-w-full" />
          <Skeleton className="h-3.5 w-64 max-w-full opacity-70" />
        </div>
        <Skeleton className="h-6 w-24 rounded-full shrink-0" />
      </div>
      <Skeleton className={`w-full ${heightClass} rounded-xl`} />
    </div>
  );
};

export const ListCardSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Đang tải danh sách">
      {Array.from({ length: rows }).map((_, idx) => (
        <div
          key={idx}
          className="flex items-center justify-between p-3 rounded-xl bg-obsidian-bg/50 border border-obsidian-border/60"
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Skeleton className="w-11 h-11 rounded-lg shrink-0" />
            <div className="space-y-1.5 flex-1 min-w-0">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2 opacity-70" />
            </div>
          </div>
          <Skeleton className="h-5 w-14 shrink-0 ml-3" />
        </div>
      ))}
    </div>
  );
};

export const PersonaCardSkeleton: React.FC = () => {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Đang tải hồ sơ cá tính AI">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-obsidian-border">
        <div className="flex items-center gap-3">
          <Skeleton className="w-12 h-12 rounded-2xl shrink-0" />
          <div className="space-y-2">
            <Skeleton className="h-3.5 w-32" />
            <Skeleton className="h-6 w-56 max-w-full" />
          </div>
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-28 rounded-xl" />
          <Skeleton className="h-9 w-32 rounded-xl" />
        </div>
      </div>
      <Skeleton className="h-20 w-full rounded-2xl" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-28 w-full rounded-xl" />
      </div>
    </div>
  );
};

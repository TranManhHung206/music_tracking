import React from 'react';
import { AlertTriangle, Inbox, RotateCcw } from 'lucide-react';
import { Button } from './Button';

interface SectionErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

/** Khối báo lỗi cục bộ cho từng thẻ dữ liệu, kèm nút thử lại. */
export const SectionErrorState: React.FC<SectionErrorStateProps> = ({
  title = 'Không thể tải dữ liệu mục này',
  message,
  onRetry,
}) => {
  return (
    <div
      role="alert"
      className="py-8 px-4 rounded-xl bg-rose-950/25 border border-rose-500/30 flex flex-col items-center justify-center text-center space-y-3"
    >
      <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/25 flex items-center justify-center text-rose-400">
        <AlertTriangle className="w-5 h-5" />
      </div>
      <div className="space-y-1 max-w-md">
        <p className="text-sm font-semibold text-rose-100">{title}</p>
        <p className="text-xs text-rose-200/80 leading-relaxed">{message}</p>
      </div>
      {onRetry && (
        <Button
          variant="danger"
          size="sm"
          onClick={onRetry}
          leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
        >
          Thử lại
        </Button>
      )}
    </div>
  );
};

interface SectionEmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  compact?: boolean;
}

/** Khối hiển thị trạng thái rỗng hoặc chưa đủ dữ liệu thống nhất giữa các khu vực. */
export const SectionEmptyState: React.FC<SectionEmptyStateProps> = ({
  title,
  description,
  icon,
  action,
  compact = false,
}) => {
  return (
    <div
      className={`${
        compact ? 'py-7 px-4' : 'py-10 px-4'
      } rounded-xl bg-obsidian-bg/45 border border-obsidian-border/70 flex flex-col items-center justify-center text-center space-y-2.5`}
    >
      <div className="w-10 h-10 rounded-xl bg-slate-800/70 border border-slate-700/60 flex items-center justify-center text-slate-400">
        {icon || <Inbox className="w-5 h-5" />}
      </div>
      <div className="space-y-1 max-w-sm">
        <p className="text-sm font-semibold text-slate-200">{title}</p>
        {description && (
          <p className="text-xs text-text-muted leading-relaxed">{description}</p>
        )}
      </div>
      {action && <div className="pt-1">{action}</div>}
    </div>
  );
};

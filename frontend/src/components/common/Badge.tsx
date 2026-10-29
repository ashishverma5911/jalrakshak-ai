import React from 'react';
import { RiskLevel } from '../../types';

interface BadgeProps {
  label: string;
  variant?: 'cyan' | 'amber' | 'emerald' | 'rose' | 'slate' | 'risk';
  riskLevel?: RiskLevel;
  className?: string;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  label,
  variant = 'cyan',
  riskLevel,
  className = '',
  dot = false,
}) => {
  let colorStyles = 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';

  if (riskLevel) {
    switch (riskLevel) {
      case 'high':
        colorStyles = 'bg-rose-500/15 text-rose-300 border-rose-500/40';
        break;
      case 'moderate':
        colorStyles = 'bg-amber-500/15 text-amber-300 border-amber-500/40';
        break;
      case 'low':
        colorStyles = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40';
        break;
      case 'nodata':
      default:
        colorStyles = 'bg-slate-700/30 text-slate-400 border-slate-600/40';
        break;
    }
  } else {
    switch (variant) {
      case 'amber':
        colorStyles = 'bg-amber-500/15 text-amber-300 border-amber-500/40';
        break;
      case 'emerald':
        colorStyles = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40';
        break;
      case 'rose':
        colorStyles = 'bg-rose-500/15 text-rose-300 border-rose-500/40';
        break;
      case 'slate':
        colorStyles = 'bg-slate-700/40 text-slate-300 border-slate-600/50';
        break;
      case 'cyan':
      default:
        colorStyles = 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
        break;
    }
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorStyles} ${className}`}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
      {label}
    </span>
  );
};

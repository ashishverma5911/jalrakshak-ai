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
  let colorStyles = 'bg-sky-50 text-sky-800 border-sky-200';

  if (riskLevel) {
    switch (riskLevel) {
      case 'high':
        colorStyles = 'bg-rose-50 text-rose-700 border-rose-200';
        break;
      case 'moderate':
        colorStyles = 'bg-amber-50 text-amber-800 border-amber-200';
        break;
      case 'low':
        colorStyles = 'bg-emerald-50 text-emerald-800 border-emerald-200';
        break;
      case 'nodata':
      default:
        colorStyles = 'bg-slate-100 text-slate-600 border-slate-200';
        break;
    }
  } else {
    switch (variant) {
      case 'amber':
        colorStyles = 'bg-amber-50 text-amber-800 border-amber-200';
        break;
      case 'emerald':
        colorStyles = 'bg-emerald-50 text-emerald-800 border-emerald-200';
        break;
      case 'rose':
        colorStyles = 'bg-rose-50 text-rose-700 border-rose-200';
        break;
      case 'slate':
        colorStyles = 'bg-slate-100 text-slate-600 border-slate-200';
        break;
      case 'cyan':
      default:
        colorStyles = 'bg-sky-50 text-sky-800 border-sky-200';
        break;
    }
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorStyles} ${className}`}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            riskLevel === 'high' || variant === 'rose'
              ? 'bg-rose-500'
              : riskLevel === 'moderate' || variant === 'amber'
              ? 'bg-amber-500'
              : riskLevel === 'low' || variant === 'emerald'
              ? 'bg-emerald-500'
              : variant === 'slate'
              ? 'bg-slate-400'
              : 'bg-sky-500'
          }`}
        />
      )}
      {label}
    </span>
  );
};

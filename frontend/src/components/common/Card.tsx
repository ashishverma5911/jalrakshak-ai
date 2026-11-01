import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'default' | 'flood' | 'drought' | 'subtle';
  hoverEffect?: boolean;
  className?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  hoverEffect = false,
  className = '',
  ...props
}) => {
  let variantStyle = 'glass-panel';
  if (variant === 'flood') variantStyle = 'glass-panel-flood';
  if (variant === 'drought') variantStyle = 'glass-panel-drought';
  if (variant === 'subtle') variantStyle = 'bg-slate-50/80 border border-slate-200/90';

  const hoverStyle = hoverEffect
    ? 'transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md cursor-pointer'
    : '';

  return (
    <div className={`rounded-xl p-5 ${variantStyle} ${hoverStyle} ${className}`} {...props}>
      {children}
    </div>
  );
};

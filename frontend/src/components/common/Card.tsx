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
  if (variant === 'subtle') variantStyle = 'bg-navy-900/60 border border-navy-800/80 backdrop-blur-md';

  const hoverStyle = hoverEffect
    ? 'transition-all duration-300 hover:-translate-y-1 hover:shadow-card-hover cursor-pointer'
    : '';

  return (
    <div className={`rounded-2xl p-5 ${variantStyle} ${hoverStyle} ${className}`} {...props}>
      {children}
    </div>
  );
};

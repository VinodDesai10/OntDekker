import React from 'react';

export interface DropdownItem {
  id: string;
  label: string;
  icon?: React.ComponentType<{
    size?: number;
    strokeWidth?: number;
    className?: string;
    'aria-hidden'?: boolean | 'true' | 'false';
  }>;
  destructive?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

export interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
  className?: string;
}

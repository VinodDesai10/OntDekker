'use client';

import React, { useState, useRef, useEffect, useId } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import type { DropdownProps } from './Dropdown.types';

export default function Dropdown({
  trigger,
  items,
  align = 'left',
  className,
}: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const uid = useId();
  const menuId = `dropdown-menu-${uid}`;

  // Close on click outside
  useEffect(() => {
    function handleMouseDown(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleMouseDown);
    return () => document.removeEventListener('mousedown', handleMouseDown);
  }, []);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  function handleItemClick(onClick: () => void) {
    onClick();
    setIsOpen(false);
  }

  return (
    <div ref={containerRef} className={`relative inline-block${className ? ` ${className}` : ''}`}>
      {/* Trigger wrapper — renders trigger as-is, adds ARIA on the wrapping button */}
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls={menuId}
        onClick={() => setIsOpen((prev) => !prev)}
        className="inline-flex focus:outline-none"
      >
        {trigger}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            id={menuId}
            role="menu"
            aria-orientation="vertical"
            initial={{ opacity: 0, scale: 0.95, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -4 }}
            transition={{
              duration: 0.15,
              ease: [0, 0, 0.2, 1],
            }}
            className={`absolute top-full mt-1.5 z-50 ${
              align === 'right' ? 'right-0' : 'left-0'
            } bg-white rounded-2xl shadow-md border border-gray-100 py-1 min-w-[160px] overflow-hidden`}
          >
            {items.map((item) => {
              const Icon = item.icon;

              const baseClasses =
                'w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left';
              const stateClasses = item.disabled
                ? 'opacity-40 cursor-not-allowed pointer-events-none'
                : item.destructive
                  ? 'text-red-600 hover:bg-red-50'
                  : 'text-charcoal hover:bg-gray-50 hover:text-ink';

              return (
                <button
                  key={item.id}
                  role="menuitem"
                  type="button"
                  disabled={item.disabled}
                  onClick={() => handleItemClick(item.onClick)}
                  className={`${baseClasses} ${stateClasses}`}
                >
                  {Icon && (
                    <Icon
                      size={15}
                      strokeWidth={1.75}
                      aria-hidden="true"
                    />
                  )}
                  {item.label}
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

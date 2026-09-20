'use client';

import { motion } from 'motion/react';
import { MapPin, CheckCircle2, Circle } from 'lucide-react';
import type { TimelineProps, TimelineEntry } from './Timeline.types';

// Formats 'HH:MM:SS' → 'HH:MM'
function formatTime(time: string): string {
  return time.slice(0, 5);
}

interface LeftColumnProps {
  entry: TimelineEntry;
}

function LeftColumn({ entry }: LeftColumnProps) {
  if (entry.dayNumber !== undefined) {
    return (
      <div className="flex flex-col items-center gap-1">
        <span className="text-[10px] font-mono uppercase tracking-wider text-muted-slate leading-none">
          Day {entry.dayNumber}
        </span>
        <Circle size={8} className="text-gray-300 fill-gray-300 mt-0.5" />
      </div>
    );
  }

  if (entry.time != null) {
    return (
      <span className="text-[10px] font-mono text-muted-slate leading-none pt-0.5">
        {formatTime(entry.time)}
      </span>
    );
  }

  return <Circle size={8} className="text-gray-300 fill-gray-300 mt-1" />;
}

export default function Timeline({ entries, className }: TimelineProps) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-slate text-center py-8">
        No itinerary planned yet.
      </p>
    );
  }

  return (
    <div className={className}>
      {entries.map((entry, i) => {
        const isLast = i === entries.length - 1;

        return (
          <motion.div
            key={entry.id}
            className="flex flex-row"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05, duration: 0.25 }}
          >
            {/* Left column */}
            <div className="relative w-14 shrink-0 flex flex-col items-center">
              {/* Day / time / dot */}
              <div className="flex flex-col items-center pt-1">
                <LeftColumn entry={entry} />
              </div>

              {/* Connecting line (hidden for last item) */}
              {!isLast && (
                <div className="absolute top-6 bottom-0 left-1/2 -translate-x-1/2 w-px bg-gray-100" />
              )}
            </div>

            {/* Right column — card */}
            <div
              className={[
                'relative flex-1 bg-white border rounded-2xl p-4 mb-4 ml-3',
                entry.isCompleted
                  ? 'border-green-100 bg-green-50/30'
                  : 'border-gray-100',
              ].join(' ')}
            >
              {/* Completed checkmark */}
              {entry.isCompleted && (
                <CheckCircle2
                  size={15}
                  className="absolute top-3 right-3 text-green-500"
                />
              )}

              {/* Title */}
              <p className="text-sm font-semibold text-ink pr-5">
                {entry.title}
              </p>

              {/* Location */}
              {entry.location != null && (
                <div className="flex items-center gap-1 mt-0.5">
                  <MapPin size={11} className="text-muted-slate shrink-0" />
                  <span className="text-xs text-muted-slate">
                    {entry.location}
                  </span>
                </div>
              )}

              {/* Description */}
              {entry.description != null && (
                <p className="text-xs text-charcoal mt-1.5 leading-relaxed">
                  {entry.description}
                </p>
              )}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

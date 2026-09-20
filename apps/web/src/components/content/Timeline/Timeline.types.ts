export interface TimelineEntry {
  id: string;
  dayNumber?: number;
  time?: string | null; // 'HH:MM:SS' or null
  title: string;
  description?: string | null;
  location?: string | null;
  isCompleted?: boolean;
}

export interface TimelineProps {
  entries: TimelineEntry[];
  className?: string;
}

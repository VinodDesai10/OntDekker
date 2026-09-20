export interface TabItem {
  id: string;
  label: string;
  /** Optional Lucide icon component */
  icon?: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  /** Badge count shown on the tab */
  count?: number;
  /** Whether the tab is disabled */
  disabled?: boolean;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTabId: string;
  onChange: (id: string) => void;
  /** Additional Tailwind classes for the outer wrapper */
  className?: string;
}

import type { GearItem, GearCategory, PackWeightClassification } from '@/types';
export type { GearItem, GearCategory, PackWeightClassification };

export interface GearPlannerProps {
  items: GearItem[];
  onTogglePacked?: (itemId: string, isPacked: boolean) => void;
  readOnly?: boolean;
  className?: string;
}

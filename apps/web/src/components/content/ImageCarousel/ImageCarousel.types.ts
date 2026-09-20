export interface CarouselImage {
  id: string;
  url: string;
  caption?: string | null;
  alt?: string;
}

export interface ImageCarouselProps {
  images: CarouselImage[];
  aspectRatio?: '16/9' | '4/3' | '1/1' | '3/2';
  className?: string;
  showCaptions?: boolean;
}

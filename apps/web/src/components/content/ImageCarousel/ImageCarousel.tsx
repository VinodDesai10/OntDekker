"use client";

/**
 * OntDekker ImageCarousel
 *
 * Multi-image carousel for expedition logs, story posts, and guide galleries.
 *
 * Features (per 05-component-library.md § Image Carousel):
 *   - Animated slide transitions via Framer Motion (motion/react)
 *   - Prev / Next chevron buttons (hidden for single image)
 *   - Dot indicators with active-pill style
 *   - Frame counter (e.g. "2 / 5") in top-right corner
 *   - Optional caption overlay (showCaptions prop)
 *   - Keyboard navigation (← →)
 *   - Pointer (touch/mouse) swipe support, threshold 50px
 *   - Configurable aspect ratio: 16/9 | 4/3 | 1/1 | 3/2
 *
 * Motion (06-motion-design.md):
 *   Slide : x direction*100% → 0 → -direction*100%
 *          duration 0.3s ease standard [0,0,0.2,1]
 */

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { ImageCarouselProps } from "./ImageCarousel.types";

// ---------------------------------------------------------------------------
// Motion variants
// ---------------------------------------------------------------------------

const EASE_STANDARD: [number, number, number, number] = [0, 0, 0.2, 1];

function slideVariants(direction: 1 | -1) {
  return {
    enter: {
      x: `${direction * 100}%`,
      opacity: 0,
    },
    center: {
      x: "0%",
      opacity: 1,
      transition: { duration: 0.3, ease: EASE_STANDARD },
    },
    exit: {
      x: `${-direction * 100}%`,
      opacity: 0,
      transition: { duration: 0.3, ease: EASE_STANDARD },
    },
  };
}

// ---------------------------------------------------------------------------
// Aspect-ratio Tailwind class map
// ---------------------------------------------------------------------------

const ASPECT_CLASS: Record<NonNullable<ImageCarouselProps["aspectRatio"]>, string> = {
  "16/9": "aspect-video",
  "4/3": "aspect-[4/3]",
  "1/1": "aspect-square",
  "3/2": "aspect-[3/2]",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ImageCarousel({
  images,
  aspectRatio = "16/9",
  className = "",
  showCaptions = false,
}: ImageCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);

  // Pointer-swipe tracking
  const pointerStartX = useRef<number | null>(null);

  // ------------------------------------------------------------------
  // Navigation helpers
  // ------------------------------------------------------------------

  function goTo(nextIndex: number, dir: 1 | -1) {
    setDirection(dir);
    setCurrentIndex(nextIndex);
  }

  function goPrev() {
    const nextIndex = (currentIndex - 1 + images.length) % images.length;
    goTo(nextIndex, -1);
  }

  function goNext() {
    const nextIndex = (currentIndex + 1) % images.length;
    goTo(nextIndex, 1);
  }

  // ------------------------------------------------------------------
  // Keyboard support
  // ------------------------------------------------------------------

  useEffect(() => {
    if (images.length <= 1) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex, images.length]);

  // ------------------------------------------------------------------
  // Early returns
  // ------------------------------------------------------------------

  if (images.length === 0) return null;

  const currentImage = images[currentIndex];

  // Single image — no controls needed
  if (images.length === 1) {
    return (
      <div
        className={[
          "relative overflow-hidden rounded-2xl bg-gray-100",
          ASPECT_CLASS[aspectRatio],
          className,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={currentImage.url}
          alt={currentImage.alt ?? currentImage.caption ?? ""}
          className="object-cover w-full h-full"
          loading="lazy"
        />
        {showCaptions && currentImage.caption && (
          <p className="absolute bottom-3 left-0 right-0 text-center text-xs text-white/80 px-4 font-medium drop-shadow">
            {currentImage.caption}
          </p>
        )}
      </div>
    );
  }

  // ------------------------------------------------------------------
  // Swipe handlers
  // ------------------------------------------------------------------

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    pointerStartX.current = e.clientX;
  }

  function handlePointerUp(e: React.PointerEvent<HTMLDivElement>) {
    if (pointerStartX.current === null) return;
    const deltaX = e.clientX - pointerStartX.current;
    pointerStartX.current = null;

    if (Math.abs(deltaX) > 50) {
      if (deltaX < 0) {
        goNext();
      } else {
        goPrev();
      }
    }
  }

  // ------------------------------------------------------------------
  // Full carousel render
  // ------------------------------------------------------------------

  return (
    <div
      role="region"
      aria-label="Image carousel"
      className={[
        "relative overflow-hidden rounded-2xl bg-gray-100 select-none",
        ASPECT_CLASS[aspectRatio],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
    >
      {/* ----------------------------------------------------------------
          Slides
      ---------------------------------------------------------------- */}
      <AnimatePresence initial={false} custom={direction}>
        <motion.div
          key={currentImage.id}
          custom={direction}
          variants={slideVariants(direction)}
          initial="enter"
          animate="center"
          exit="exit"
          className="absolute inset-0"
          aria-hidden={false}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={currentImage.url}
            alt={currentImage.alt ?? currentImage.caption ?? `Image ${currentIndex + 1} of ${images.length}`}
            className="object-cover w-full h-full"
            loading="lazy"
            draggable={false}
          />
        </motion.div>
      </AnimatePresence>

      {/* ----------------------------------------------------------------
          Counter — top-right
      ---------------------------------------------------------------- */}
      <span
        aria-live="polite"
        aria-atomic="true"
        className="absolute top-3 right-3 text-[10px] font-mono text-white/80 bg-black/30 px-2 py-0.5 rounded-full z-10 pointer-events-none"
      >
        {currentIndex + 1} / {images.length}
      </span>

      {/* ----------------------------------------------------------------
          Caption — above dot indicators
      ---------------------------------------------------------------- */}
      {showCaptions && currentImage.caption && (
        <p className="absolute bottom-8 left-0 right-0 text-center text-xs text-white/80 px-4 font-medium drop-shadow z-10 pointer-events-none">
          {currentImage.caption}
        </p>
      )}

      {/* ----------------------------------------------------------------
          Dot indicators — bottom-center
      ---------------------------------------------------------------- */}
      <div
        role="tablist"
        aria-label="Carousel slides"
        className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5 z-10"
      >
        {images.map((image, i) => (
          <button
            key={image.id}
            role="tab"
            type="button"
            aria-label={`Go to image ${i + 1}`}
            aria-selected={i === currentIndex}
            onClick={() => goTo(i, i > currentIndex ? 1 : -1)}
            className={[
              "h-1.5 rounded-full transition-all duration-200",
              i === currentIndex
                ? "w-3 bg-white"
                : "w-1.5 bg-white/50 hover:bg-white/75",
            ].join(" ")}
          />
        ))}
      </div>

      {/* ----------------------------------------------------------------
          Prev button
      ---------------------------------------------------------------- */}
      <button
        type="button"
        aria-label="Previous image"
        onClick={goPrev}
        className="
          absolute left-2 top-1/2 -translate-y-1/2 z-10
          w-8 h-8 rounded-full
          bg-black/40 hover:bg-black/60
          text-white
          flex items-center justify-center
          transition-colors duration-150
          focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white
        "
      >
        <ChevronLeft size={16} strokeWidth={2.5} aria-hidden="true" />
      </button>

      {/* ----------------------------------------------------------------
          Next button
      ---------------------------------------------------------------- */}
      <button
        type="button"
        aria-label="Next image"
        onClick={goNext}
        className="
          absolute right-2 top-1/2 -translate-y-1/2 z-10
          w-8 h-8 rounded-full
          bg-black/40 hover:bg-black/60
          text-white
          flex items-center justify-center
          transition-colors duration-150
          focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white
        "
      >
        <ChevronRight size={16} strokeWidth={2.5} aria-hidden="true" />
      </button>
    </div>
  );
}

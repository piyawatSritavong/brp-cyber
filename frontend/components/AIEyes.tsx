"use client";

import { useEffect, useRef } from "react";

export function AIEyes() {
  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const left = leftRef.current!;
    const right = rightRef.current!;
    if (!leftRef.current || !rightRef.current) return;

    let currentZone = "center";
    const squintTimers: Record<string, ReturnType<typeof setTimeout> | null> = {
      left: null,
      right: null,
    };
    const canSquintInZone: Record<string, boolean> = { left: true, right: true };

    function triggerSquint(eyeEl: HTMLDivElement, zoneName: string) {
      canSquintInZone[zoneName] = false;
      eyeEl.classList.add("ai-eye-suspicious");
      if (squintTimers[zoneName]) clearTimeout(squintTimers[zoneName]!);
      squintTimers[zoneName] = setTimeout(() => {
        eyeEl.classList.remove("ai-eye-suspicious");
      }, 1200);
    }

    function handleMouseMove(e: MouseEvent) {
      const ww = window.innerWidth;
      const wh = window.innerHeight;
      const cx = ww / 2;
      const cy = wh / 2;
      const vertDist = Math.abs(e.clientY - cy);
      const isHLevel = vertDist < 250;
      const diffRatio = (e.clientX - cx) / (ww / 2);

      let newZone = "center";
      if (isHLevel) {
        if (diffRatio < -0.45) newZone = "left";
        else if (diffRatio > 0.45) newZone = "right";
      }
      if (newZone !== currentZone) {
        if (newZone === "center") {
          canSquintInZone.left = true;
          canSquintInZone.right = true;
        }
        currentZone = newZone;
      }

      [left, right].forEach((eye) => {
        const rect = eye.parentElement!.getBoundingClientRect();
        const eyeCX = rect.left + rect.width / 2;
        const eyeCY = rect.top + rect.height / 2;
        const angle = Math.atan2(e.clientY - eyeCY, e.clientX - eyeCX);
        const dist = Math.min(28, Math.hypot(e.clientX - eyeCX, e.clientY - eyeCY) / 15);
        eye.style.transform = `translate(${Math.cos(angle) * dist}px, ${Math.sin(angle) * dist}px)`;
      });

      if (currentZone === "left" && canSquintInZone.left) triggerSquint(right, "left");
      else if (currentZone === "right" && canSquintInZone.right) triggerSquint(left, "right");
    }

    document.addEventListener("mousemove", handleMouseMove);

    let blinkTimer: ReturnType<typeof setTimeout>;
    function randomBlink() {
      left.classList.add("ai-eye-blink");
      right.classList.add("ai-eye-blink");
      blinkTimer = setTimeout(() => {
        left.classList.remove("ai-eye-blink");
        right.classList.remove("ai-eye-blink");
        blinkTimer = setTimeout(randomBlink, Math.random() * 5000 + 2000);
      }, 100);
    }
    randomBlink();

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      clearTimeout(blinkTimer);
      if (squintTimers.left) clearTimeout(squintTimers.left);
      if (squintTimers.right) clearTimeout(squintTimers.right);
    };
  }, []);

  return (
    <div className="ai-eyes-wrapper">
      <div className="ai-eye-container">
        <div ref={leftRef} className="ai-eye" />
      </div>
      <div className="ai-eye-container">
        <div ref={rightRef} className="ai-eye" />
      </div>
    </div>
  );
}

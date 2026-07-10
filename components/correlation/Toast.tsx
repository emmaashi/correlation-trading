"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface ToastProps {
  message: string;
  type: "error" | "success";
  onClose: () => void;
  duration?: number;
}

export default function Toast({ message, type, onClose, duration = 4000 }: ToastProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onClose, 200);
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const borderColor = type === "error" ? "rgba(239,68,68,0.3)" : "rgba(34,197,94,0.3)";
  const bgColor = type === "error" ? "rgba(239,68,68,0.08)" : "rgba(34,197,94,0.08)";
  const textColor = type === "error" ? "#fca5a5" : "#86efac";
  const icon = type === "error" ? "✕" : "✓";

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.2 }}
          className="fixed top-6 left-1/2 -translate-x-1/2 z-[100] max-w-md w-full px-4"
        >
          <div
            className="flex items-center gap-3 rounded-xl px-4 py-3 backdrop-blur-xl border"
            style={{ backgroundColor: bgColor, borderColor }}
          >
            <span
              className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold"
              style={{ backgroundColor: borderColor, color: textColor }}
            >
              {icon}
            </span>
            <span className="text-sm" style={{ color: textColor }}>
              {message}
            </span>
            <button
              onClick={() => { setVisible(false); setTimeout(onClose, 200); }}
              className="ml-auto text-neutral-500 hover:text-neutral-300 transition-colors text-sm flex-shrink-0"
            >
              Dismiss
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

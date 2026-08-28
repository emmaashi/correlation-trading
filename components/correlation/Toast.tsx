"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X, XCircle } from "lucide-react";

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
  const StatusIcon = type === "error" ? XCircle : Check;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, x: 12, y: 8 }}
          animate={{ opacity: 1, x: 0, y: 0 }}
          exit={{ opacity: 0, x: 12, y: 8 }}
          transition={{ duration: 0.2 }}
          className="fixed bottom-4 left-4 right-4 z-[100] sm:left-auto sm:w-[22rem]"
        >
          <div
            role="alert"
            aria-live="assertive"
            className="flex items-center gap-2 rounded-md border px-3 py-2 shadow-lg backdrop-blur-xl"
            style={{ backgroundColor: bgColor, borderColor }}
          >
            <span
              className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full"
              style={{ backgroundColor: borderColor }}
            >
              <StatusIcon aria-hidden="true" className="h-3 w-3" style={{ color: textColor }} />
            </span>
            <span className="min-w-0 flex-1 text-xs leading-5" style={{ color: textColor }}>
              {message}
            </span>
            <button
              type="button"
              aria-label="Dismiss notification"
              title="Dismiss notification"
              onClick={() => { setVisible(false); setTimeout(onClose, 200); }}
              className="flex h-6 w-6 flex-shrink-0 items-center justify-center text-neutral-500 transition-colors hover:text-neutral-200"
            >
              <X aria-hidden="true" className="h-3.5 w-3.5" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

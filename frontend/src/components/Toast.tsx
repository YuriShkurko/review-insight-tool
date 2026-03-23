"use client";

import { useEffect, useState } from "react";

interface ToastProps {
  message: string;
  type?: "success" | "error";
  duration?: number;
  onDone: () => void;
}

export default function Toast({ message, type = "success", duration = 4000, onDone }: ToastProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setVisible(false), duration - 300);
    const t2 = setTimeout(onDone, duration);
    return () => {
      clearTimeout(t);
      clearTimeout(t2);
    };
  }, [duration, onDone]);

  const bg = type === "success" ? "bg-green-600" : "bg-red-600";

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 ${bg} text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium transition-all duration-300 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
      }`}
    >
      {message}
    </div>
  );
}

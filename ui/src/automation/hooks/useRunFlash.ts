import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";

export const useRunFlash = () => {
  const [runCompletedFlash, setRunCompletedFlash] = useState(false);
  const runCompletedFlashTimeoutRef = useRef<number | null>(null);

  const clearRunCompletedFlashTimeout = () => {
    if (runCompletedFlashTimeoutRef.current !== null) {
      window.clearTimeout(runCompletedFlashTimeoutRef.current);
      runCompletedFlashTimeoutRef.current = null;
    }
  };

  const resetRunCompletedFlash = () => {
    clearRunCompletedFlashTimeout();
    setRunCompletedFlash(false);
  };

  const scheduleRunCompletedFlash = (duration = 1500) => {
    clearRunCompletedFlashTimeout();
    setRunCompletedFlash(true);
    runCompletedFlashTimeoutRef.current = window.setTimeout(() => {
      setRunCompletedFlash(false);
      runCompletedFlashTimeoutRef.current = null;
    }, duration);
  };

  useEffect(() => () => {
    if (runCompletedFlashTimeoutRef.current !== null) {
      window.clearTimeout(runCompletedFlashTimeoutRef.current);
      runCompletedFlashTimeoutRef.current = null;
    }
  }, []);

  return {
    runCompletedFlash,
    setRunCompletedFlash,
    clearRunCompletedFlashTimeout,
    resetRunCompletedFlash,
    scheduleRunCompletedFlash
  } as const;
};

export default useRunFlash;
import { useEffect, useRef, useState } from "react";

export const useRunFlash = () => {
  const [runCompletedFlash, setRunCompletedFlash] = useState(false);
  const runCompletedFlashTimeoutRef = useRef<number | null>(null);

  const clearRunCompletedFlashTimeout = () => {
    if (runCompletedFlashTimeoutRef.current !== null) {
      window.clearTimeout(runCompletedFlashTimeoutRef.current);
      runCompletedFlashTimeoutRef.current = null;
    }
  };

  const resetRunCompletedFlash = () => {
    clearRunCompletedFlashTimeout();
    setRunCompletedFlash(false);
  };

  useEffect(() => () => {
    if (runCompletedFlashTimeoutRef.current !== null) {
      window.clearTimeout(runCompletedFlashTimeoutRef.current);
      runCompletedFlashTimeoutRef.current = null;
    }
  }, []);

  return {
    runCompletedFlash,
    setRunCompletedFlash,
    runCompletedFlashTimeoutRef,
    clearRunCompletedFlashTimeout,
    resetRunCompletedFlash
  };
};

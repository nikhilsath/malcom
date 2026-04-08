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
    clearRunCompletedFlashTimeout,
    resetRunCompletedFlash
  };
};

export default useRunFlash;

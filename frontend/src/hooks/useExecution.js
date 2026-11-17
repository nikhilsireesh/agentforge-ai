import { Api } from "../services/api";
import { ACTIVE_STATUSES } from "../utils/format";
import { useApi } from "./useApi";
import { useState } from "react";

/** Execution detail that polls every 2 s while the workflow is active. */
export function useExecutionDetail(executionId) {
  const [active, setActive] = useState(true);
  const result = useApi(
    async () => {
      const detail = await Api.getExecution(executionId);
      setActive(ACTIVE_STATUSES.includes(detail.status));
      return detail;
    },
    [executionId],
    { enabled: Boolean(executionId), interval: active ? 2000 : null },
  );
  return result;
}

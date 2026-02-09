import { publicProcedure, router } from "../_core/trpc";
import { z } from "zod";
import fs from "fs";
import path from "path";
import { ZHUWEI_CONFIG } from "../../config/zhuwei";

const REPORT_PATH = ZHUWEI_CONFIG.PATHS.BRAIN_REPORTS;

export const reportRouter = router({
  submitReport: publicProcedure
    .input(z.object({
      aiName: z.enum(["Claude", "Cursor", "Windsurf", "Qianxun"]),
      taskName: z.string(),
      status: z.enum(["completed", "blocked", "warning"]),
      summary: z.string(),
      changes: z.array(z.string()),
      nextSteps: z.string(),
    }))
    .mutation(({ input }) => {
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const fileName = `${timestamp}-${input.aiName}-${input.taskName}.json`;

      if (!fs.existsSync(REPORT_PATH)) fs.mkdirSync(REPORT_PATH, { recursive: true });

      fs.writeFileSync(
        path.join(REPORT_PATH, fileName),
        JSON.stringify({ ...input, timestamp: new Date().toLocaleString() }, null, 2)
      );

      return { success: true, message: "回報已提交至築未指揮中心" };
    }),
});

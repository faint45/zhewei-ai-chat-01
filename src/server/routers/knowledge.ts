import { publicProcedure, router } from "../_core/trpc";
import { z } from "zod";
import fs from "fs";
import path from "path";
import { ZHUWEI_CONFIG } from "../../config/zhuwei";

const BRAIN_PATH = ZHUWEI_CONFIG.PATHS.BRAIN_HISTORY;

export const knowledgeRouter = router({
  saveChatHistory: publicProcedure
    .input(z.object({
      title: z.string(),
      content: z.string(),
      category: z.enum(["architecture", "logic", "career", "code"]),
    }))
    .mutation(({ input }) => {
      const fileName = `${new Date().toISOString().split("T")[0]}-${input.title}.md`;
      const filePath = path.join(BRAIN_PATH, fileName);

      const fileContent = `---
date: ${new Date().toLocaleString()}
category: ${input.category}
---
# ${input.title}

${input.content}
`;

      if (!fs.existsSync(BRAIN_PATH)) fs.mkdirSync(BRAIN_PATH, { recursive: true });
      fs.writeFileSync(filePath, fileContent);
      return { success: true, path: filePath };
    }),

  getHistoryList: publicProcedure.query(() => {
    if (!fs.existsSync(BRAIN_PATH)) return [];
    return fs
      .readdirSync(BRAIN_PATH)
      .map((file) => ({
        name: file,
        date: file.split("-")[0],
      }))
      .reverse();
  }),
});

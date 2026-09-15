/** 根据 FastAPI OpenAPI 文档生成只读 TypeScript 类型。 */

import { mkdir, writeFile } from "node:fs/promises";
import process from "node:process";

import openapiTS, { astToString } from "openapi-typescript";

const schemaUrl =
  process.env.FASTAPI_OPENAPI_URL ?? "http://127.0.0.1:8000/openapi.json";
const outputPath = new URL("../src/types/api.generated.ts", import.meta.url);

try {
  const nodes = await openapiTS(new URL(schemaUrl));
  const banner =
    "/** 此文件由 FastAPI /openapi.json 自动生成，请勿手工编辑。 */\n\n";
  await mkdir(new URL("../src/types/", import.meta.url), { recursive: true });
  await writeFile(outputPath, banner + astToString(nodes), "utf8");
  process.stdout.write(`接口类型已更新：${schemaUrl}\n`);
} catch (error) {
  process.stderr.write(
    `无法生成接口类型，请确认 FastAPI 已启动：${schemaUrl}\n`,
  );
  throw error;
}

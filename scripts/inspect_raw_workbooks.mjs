import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const paths = process.argv.slice(2);
for (const path of paths) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table,formula",
    maxChars: 12000,
    tableMaxRows: 8,
    tableMaxCols: 12,
    options: { maxResults: 100 },
  });
  process.stdout.write(`\n--- ${path} ---\n${summary.ndjson}\n`);
}

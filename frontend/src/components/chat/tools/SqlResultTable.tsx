"use client";

import { useState } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCell } from "@/lib/format";
import type { CompiledColumn } from "@/lib/types";

interface SqlResultTableProps {
  columns: CompiledColumn[];
  rows: Array<Record<string, unknown>>;
  sql?: string;
  maxRowsDefault?: number;
}

export function SqlResultTable({
  columns,
  rows,
  sql,
  maxRowsDefault = 25,
}: SqlResultTableProps) {
  const [showAll, setShowAll] = useState(false);
  const visibleRows = showAll ? rows : rows.slice(0, maxRowsDefault);

  if (rows.length === 0) {
    return (
      <div className="rounded-md border bg-muted/30 px-3 py-6 text-center text-xs text-muted-foreground">
        No rows.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-md border">
        <Table className="text-[13px]">
          <TableHeader>
            <TableRow className="bg-muted/40">
              {columns.map((c) => (
                <TableHead
                  key={c.name}
                  className="whitespace-nowrap font-medium"
                >
                  {c.label}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleRows.map((row, i) => (
              <TableRow key={i}>
                {columns.map((c) => {
                  const isNum =
                    c.format !== "string" && typeof row[c.name] === "number";
                  return (
                    <TableCell
                      key={c.name}
                      className={
                        isNum
                          ? "whitespace-nowrap text-right tabular-nums"
                          : "whitespace-nowrap"
                      }
                    >
                      {formatCell(row[c.name], c.format)}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {rows.length > maxRowsDefault && (
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          className="text-[11px] text-muted-foreground underline underline-offset-2 hover:text-foreground"
        >
          {showAll
            ? `Show first ${maxRowsDefault}`
            : `Show all ${rows.length} rows`}
        </button>
      )}

      {sql && (
        <details className="rounded-md border bg-muted/20 text-[11px]">
          <summary className="cursor-pointer px-2 py-1 text-muted-foreground">
            SQL
          </summary>
          <pre className="overflow-x-auto p-2 font-mono">{sql}</pre>
        </details>
      )}
    </div>
  );
}

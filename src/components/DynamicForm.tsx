import { useState, useEffect } from 'react';
import { Plus, Trash2 } from 'lucide-react';

interface Column { id: string; label: string; type: string; }
interface Schema { title: string; columns: Column[]; default_rows: Record<string, unknown>[]; }

export const DynamicForm = ({ schema, onDataChange }: { schema: Schema; onDataChange: (data: unknown[]) => void }) => {
  const [rows, setRows] = useState(schema.default_rows);
  const [editCell, setEditCell] = useState<{ row: number; col: string } | null>(null);

  useEffect(() => { onDataChange(rows); }, [rows]);

  const addRow = () => {
    const newRow = schema.columns.reduce((acc, col) => ({ ...acc, [col.id]: '' }), {} as Record<string, unknown>);
    setRows([...rows, newRow]);
  };

  const deleteRow = (index: number) => setRows(rows.filter((_, i) => i !== index));

  const updateCell = (rowIndex: number, colId: string, value: string) => {
    const updated = [...rows];
    updated[rowIndex] = { ...updated[rowIndex], [colId]: value };
    setRows(updated);
  };

  return (
    <div className="p-4 border border-zhuwei-emerald-200 rounded-lg shadow-sm bg-white">
      <table className="w-full border-collapse border border-zhuwei-emerald-200">
        <thead className="bg-zhuwei-emerald-50">
          <tr>
            {schema.columns.map(col => <th key={col.id} className="border border-zhuwei-emerald-200 p-2 text-sm text-zhuwei-emerald-800">{col.label}</th>)}
            <th className="border border-zhuwei-emerald-200 p-2 w-12 text-center">
              <Plus size={18} className="cursor-pointer text-zhuwei-emerald-600 mx-auto" onClick={addRow} />
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rIdx) => (
            <tr key={rIdx} className="hover:bg-zhuwei-emerald-50">
              {schema.columns.map(col => (
                <td
                  key={col.id}
                  className="border border-zhuwei-emerald-200 p-2 text-sm min-w-[120px]"
                  onDoubleClick={() => setEditCell({ row: rIdx, col: col.id })}
                >
                  {editCell?.row === rIdx && editCell?.col === col.id ? (
                    <input
                      autoFocus
                      className="w-full outline-none bg-zhuwei-emerald-50 border border-zhuwei-emerald-300 rounded px-1"
                      value={String(row[col.id] ?? '')}
                      onBlur={() => setEditCell(null)}
                      onChange={(e) => updateCell(rIdx, col.id, e.target.value)}
                    />
                  ) : (
                    <div className="min-h-[20px]">{row[col.id] ? String(row[col.id]) : <span className="text-zhuwei-emerald-300">雙擊編輯...</span>}</div>
                  )}
                </td>
              ))}
              <td className="border border-zhuwei-emerald-200 p-2 text-center">
                <Trash2 size={16} className="cursor-pointer text-red-500 mx-auto" onClick={() => deleteRow(rIdx)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

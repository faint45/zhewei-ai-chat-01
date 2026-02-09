import React, { useState, useEffect } from 'react';
import { PageLayout, Card, Loading, ApiStatus, Button } from '../components/zhuwei';
import { DynamicForm } from '../components/DynamicForm';
import { fetchHealth, fetchSchema } from '../api/client';
import formSchema from '../templates/formSchema.json';

interface SchemaType {
  title: string;
  columns: { id: string; label: string; type: string }[];
  default_rows: Record<string, unknown>[];
}

export const HomePage: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle');
  const [apiMessage, setApiMessage] = useState<string>('');
  const [schema, setSchema] = useState<SchemaType | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setApiStatus('loading');
    fetchHealth()
      .then((data) => {
        if (cancelled) return;
        setApiStatus(data?.ok ? 'ok' : 'error');
        setApiMessage(data?.status || (data?.ok ? '' : '連線失敗'));
      })
      .catch(() => {
        if (!cancelled) {
          setApiStatus('error');
          setApiMessage('無法連線');
        }
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setSchemaLoading(true);
    fetchSchema()
      .then((data) => {
        if (cancelled) return;
        setSchema((data as SchemaType) || null);
      })
      .catch(() => {
        if (!cancelled) setSchema(null);
      })
      .finally(() => {
        if (!cancelled) setSchemaLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const activeSchema = schema ?? (formSchema as SchemaType);
  const handleDataChange = (data: unknown[]) => {
    console.log('表單資料變更:', data);
  };

  return (
    <PageLayout title="築未科技 — 工程拍照記錄表">
      <div className="max-w-4xl mx-auto space-y-4">
        <Card title="系統狀態">
          <div className="flex items-center justify-between">
            <ApiStatus status={apiStatus} message={apiMessage} />
            <Button variant="outline" onClick={() => window.location.reload()}>重新整理</Button>
          </div>
        </Card>
        <Card title={activeSchema?.title ?? '工程拍照記錄表'}>
          {schemaLoading ? (
            <Loading message="載入表單結構..." />
          ) : (
            <DynamicForm schema={activeSchema} onDataChange={handleDataChange} />
          )}
        </Card>
      </div>
    </PageLayout>
  );
};

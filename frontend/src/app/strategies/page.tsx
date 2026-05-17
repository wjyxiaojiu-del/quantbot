"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { strategyApi } from "@/lib/api";

interface Strategy {
  id: string;
  name: string;
  description?: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
  code?: string;
  params?: Record<string, any>;
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Strategy | null>(null);
  const [form, setForm] = useState({ name: "", description: "", code: "" });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const loadStrategies = useCallback(async () => {
    try {
      const res = await strategyApi.list();
      setStrategies(res.data || []);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => { loadStrategies(); }, [loadStrategies]);

  const handleCreate = async () => {
    if (!form.name || !form.code) return;
    setLoading(true);
    try {
      await strategyApi.create(form);
      setShowCreate(false);
      setForm({ name: "", description: "", code: "" });
      loadStrategies();
      setMessage("策略创建成功");
    } catch (err: any) {
      setMessage("创建失败: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    if (!editing) return;
    setLoading(true);
    try {
      await strategyApi.update(editing.id, form);
      setEditing(null);
      setForm({ name: "", description: "", code: "" });
      loadStrategies();
      setMessage("策略更新成功");
    } catch (err: any) {
      setMessage("更新失败: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除该策略？")) return;
    try {
      await strategyApi.delete(id);
      loadStrategies();
      setMessage("已删除");
    } catch (err: any) {
      setMessage("删除失败: " + (err.response?.data?.detail || err.message));
    }
  };

  const openEdit = (s: Strategy) => {
    setEditing(s);
    setForm({ name: s.name, description: s.description || "", code: s.code || "" });
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="border-b bg-white dark:bg-slate-900 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <h1 className="text-lg font-bold">策略管理</h1>
          <Link href="/" className="text-sm text-slate-500 hover:text-blue-600">← 返回首页</Link>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex justify-between items-center mb-6">
          <p className="text-sm text-slate-500">共 {strategies.length} 个策略</p>
          <button
            onClick={() => { setShowCreate(true); setForm({ name: "", description: "", code: "" }); }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
          >
            + 新建策略
          </button>
        </div>

        {message && (
          <div className="mb-4 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm">{message}</div>
        )}

        {strategies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {strategies.map(s => (
              <div key={s.id} className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold">{s.name}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    s.status === "active" ? "bg-green-100 text-green-700" :
                    s.status === "archived" ? "bg-slate-100 text-slate-500" :
                    "bg-blue-100 text-blue-700"
                  }`}>
                    {s.status === "active" ? "启用" : s.status === "archived" ? "归档" : "草稿"}
                  </span>
                </div>
                <p className="text-sm text-slate-500 mb-3 line-clamp-2">
                  {s.description || "暂无描述"}
                </p>
                <div className="text-xs text-slate-400 mb-3">
                  v{s.version} · {new Date(s.updated_at).toLocaleDateString("zh-CN")}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => openEdit(s)}
                    className="flex-1 py-1.5 border rounded-lg text-xs hover:bg-slate-50 dark:hover:bg-slate-800"
                  >
                    编辑
                  </button>
                  <Link
                    href={`/backtest?strategy=${s.id}`}
                    className="flex-1 py-1.5 bg-blue-600 text-white rounded-lg text-xs text-center hover:bg-blue-700"
                  >
                    回测
                  </Link>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="px-3 py-1.5 border border-red-200 text-red-600 rounded-lg text-xs hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white dark:bg-slate-900 rounded-xl border p-12 text-center text-slate-400">
            还没有策略，点击「新建策略」开始创建
          </div>
        )}
      </div>

      {/* 创建/编辑弹窗 */}
      {(showCreate || editing) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-900 rounded-xl border p-6 w-[600px] max-h-[80vh] overflow-y-auto">
            <h3 className="font-bold text-lg mb-4">{editing ? "编辑策略" : "新建策略"}</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-500">策略名称</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="text-xs text-slate-500">描述</label>
                <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="text-xs text-slate-500">策略代码</label>
                <textarea
                  value={form.code}
                  onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                  rows={12}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-xs font-mono resize-none dark:bg-slate-800 dark:border-slate-700"
                  spellCheck={false}
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => { setShowCreate(false); setEditing(null); }}
                className="flex-1 py-2 border rounded-lg text-sm">取消</button>
              <button onClick={editing ? handleUpdate : handleCreate} disabled={loading}
                className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium">
                {loading ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

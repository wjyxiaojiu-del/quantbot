"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      if (mode === "login") {
        const res = await api.post("/auth/login", {
          username: form.username,
          password: form.password,
        });
        localStorage.setItem("token", res.data.access_token);
        router.push("/");
      } else {
        await api.post("/auth/register", form);
        // 注册成功后自动登录
        const res = await api.post("/auth/login", {
          username: form.username,
          password: form.password,
        });
        localStorage.setItem("token", res.data.access_token);
        router.push("/");
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
      <div className="bg-white dark:bg-slate-900 rounded-xl border p-8 w-96">
        <div className="text-center mb-6">
          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-3">
            <span className="text-white font-bold text-xl">Q</span>
          </div>
          <h1 className="text-xl font-bold">QuantBot</h1>
          <p className="text-sm text-slate-500 mt-1">
            {mode === "login" ? "登录你的账户" : "创建新账户"}
          </p>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-slate-500">用户名</label>
            <input
              value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
              className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
              placeholder="输入用户名"
            />
          </div>
          {mode === "register" && (
            <div>
              <label className="text-xs text-slate-500">邮箱</label>
              <input
                type="email"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                placeholder="输入邮箱"
              />
            </div>
          )}
          <div>
            <label className="text-xs text-slate-500">密码</label>
            <input
              type="password"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
              placeholder="输入密码"
              onKeyDown={e => e.key === "Enter" && handleSubmit()}
            />
          </div>
        </div>

        {error && (
          <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 text-red-600 text-sm rounded-lg">{error}</div>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full mt-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg font-medium transition-colors"
        >
          {loading ? "处理中..." : mode === "login" ? "登录" : "注册"}
        </button>

        <div className="mt-4 text-center text-sm text-slate-500">
          {mode === "login" ? (
            <>还没有账户？<button onClick={() => setMode("register")} className="text-blue-600 hover:underline ml-1">注册</button></>
          ) : (
            <>已有账户？<button onClick={() => setMode("login")} className="text-blue-600 hover:underline ml-1">登录</button></>
          )}
        </div>

        <Link href="/" className="block mt-4 text-center text-xs text-slate-400 hover:text-blue-600">
          ← 返回首页
        </Link>
      </div>
    </main>
  );
}

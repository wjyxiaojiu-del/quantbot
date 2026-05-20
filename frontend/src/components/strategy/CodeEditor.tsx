"use client";

import { useState, useRef, useEffect, useCallback } from "react";

interface Props {
  value: string;
  onChange: (value: string) => void;
  height?: number;
  readOnly?: boolean;
}

// 策略代码片段
const CODE_SNIPPETS: Record<string, string> = {
  "generate_signals": `def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """生成交易信号
    signal: 1=买入, -1=卖出, 0=持有
    """
    df["signal"] = 0
    return df`,
  "ma_cross": `    # 均线交叉
    short = params.get("short_window", 5)
    long = params.get("long_window", 20)
    df["ma_short"] = df["close"].rolling(short).mean()
    df["ma_long"] = df["close"].rolling(long).mean()
    df["signal"] = 0
    df.loc[df["ma_short"] > df["ma_long"], "signal"] = 1
    df.loc[df["ma_short"] < df["ma_long"], "signal"] = -1`,
  "rsi": `    # RSI 超买超卖
    period = params.get("period", 14)
    overbought = params.get("overbought", 70)
    oversold = params.get("oversold", 30)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["signal"] = 0
    df.loc[df["rsi"] < oversold, "signal"] = 1
    df.loc[df["rsi"] > overbought, "signal"] = -1`,
  "bollinger": `    # 布林带
    period = params.get("period", 20)
    std_dev = params.get("std_dev", 2)
    df["ma"] = df["close"].rolling(period).mean()
    df["std"] = df["close"].rolling(period).std()
    df["upper"] = df["ma"] + std_dev * df["std"]
    df["lower"] = df["ma"] - std_dev * df["std"]
    df["signal"] = 0
    df.loc[df["close"] < df["lower"], "signal"] = 1
    df.loc[df["close"] > df["upper"], "signal"] = -1`,
};

export default function CodeEditor({
  value,
  onChange,
  height = 400,
  readOnly = false,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineCountRef = useRef<HTMLDivElement>(null);
  const [showSnippets, setShowSnippets] = useState(false);

  // 行号同步
  const syncLineNumbers = useCallback(() => {
    if (!textareaRef.current || !lineCountRef.current) return;
    const lines = value.split("\n").length;
    lineCountRef.current.innerHTML = Array.from(
      { length: lines },
      (_, i) => `<div class="text-right pr-2 leading-5 text-xs">${i + 1}</div>`
    ).join("");
  }, [value]);

  useEffect(() => {
    syncLineNumbers();
  }, [syncLineNumbers]);

  // Tab 缩进
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = value.substring(0, start) + "    " + value.substring(end);
      onChange(newValue);

      requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 4;
      });
    }
  };

  // 插入代码片段
  const insertSnippet = (snippet: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const newValue = value.substring(0, start) + "\n" + snippet + value.substring(start);
    onChange(newValue);
    setShowSnippets(false);

    requestAnimationFrame(() => {
      textarea.focus();
      textarea.selectionStart = textarea.selectionEnd = start + snippet.length + 1;
    });
  };

  return (
    <div className="relative border rounded-lg overflow-hidden bg-white dark:bg-slate-900">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b bg-slate-50 dark:bg-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Python</span>
          <span className="text-xs text-slate-400">|</span>
          <span className="text-xs text-slate-400">{value.split("\n").length} 行</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSnippets(!showSnippets)}
            className="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50"
          >
            代码片段
          </button>
        </div>
      </div>

      {/* 代码片段面板 */}
      {showSnippets && (
        <div className="absolute right-2 top-10 z-20 w-64 bg-white dark:bg-slate-800 border rounded-lg shadow-lg max-h-64 overflow-y-auto">
          {Object.entries(CODE_SNIPPETS).map(([name, code]) => (
            <button
              key={name}
              onClick={() => insertSnippet(code)}
              className="w-full text-left px-3 py-2 text-xs hover:bg-slate-100 dark:hover:bg-slate-700 border-b last:border-0"
            >
              <div className="font-medium text-slate-700 dark:text-slate-300">
                {name.replace(/_/g, " ")}
              </div>
              <div className="text-slate-400 truncate mt-0.5">
                {code.split("\n")[0].trim()}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* 编辑区域 */}
      <div className="flex" style={{ height }}>
        {/* 行号 */}
        <div
          ref={lineCountRef}
          className="w-10 flex-shrink-0 bg-slate-50 dark:bg-slate-800 border-r overflow-hidden py-2 select-none"
          style={{ fontFamily: "monospace" }}
        />

        {/* 代码输入 */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onScroll={(e) => {
            if (lineCountRef.current) {
              lineCountRef.current.scrollTop = (e.target as HTMLTextAreaElement).scrollTop;
            }
          }}
          readOnly={readOnly}
          className="flex-1 p-2 text-xs font-mono resize-none bg-transparent focus:outline-none dark:text-slate-200 leading-5"
          spellCheck={false}
          style={{ tabSize: 4 }}
        />
      </div>

      {/* 底部提示 */}
      <div className="px-3 py-1.5 border-t bg-slate-50 dark:bg-slate-800 text-xs text-slate-400">
        Tab 插入缩进 · 代码片段快速生成模板
      </div>
    </div>
  );
}

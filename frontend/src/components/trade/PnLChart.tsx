"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
  LineData,
  LineStyle,
} from "lightweight-charts";

interface Position {
  id?: string;
  symbol: string;
  quantity: number;
  avg_cost: number;
  market_value?: number;
  current_price?: number;
}

interface Props {
  positions: Position[];
  initialCash: number;
  currentCash: number;
  height?: number;
}

export default function PnLChart({
  positions,
  initialCash,
  currentCash,
  height = 300,
}: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [pnlData, setPnlData] = useState<
    { symbol: string; pnl: number; pnlPct: number }[]
  >([]);

  // 计算持仓盈亏
  useEffect(() => {
    const data = positions.map((p) => {
      const currentPrice = p.current_price || p.avg_cost;
      const pnl = (currentPrice - p.avg_cost) * p.quantity;
      const pnlPct =
        p.avg_cost > 0
          ? ((currentPrice - p.avg_cost) / p.avg_cost) * 100
          : 0;
      return { symbol: p.symbol, pnl, pnlPct };
    });
    setPnlData(data);
  }, [positions]);

  // 绘制盈亏柱状图
  useEffect(() => {
    if (!chartContainerRef.current || pnlData.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#f1f5f9" },
        horzLines: { color: "#f1f5f9" },
      },
      rightPriceScale: {
        borderColor: "#e2e8f0",
      },
      timeScale: {
        borderColor: "#e2e8f0",
        visible: false,
      },
      height,
    });

    // 用柱状图展示各持仓盈亏
    const histogramSeries = chart.addHistogramSeries({
      color: "#3b82f6",
      priceFormat: { type: "price", precision: 0, minMove: 1 },
    });

    // 这里简化处理，用数字作为时间轴
    const histogramData = pnlData.map((d, i) => ({
      time: (i + 1) as unknown as any,
      value: d.pnl,
      color: d.pnl >= 0 ? "rgba(239,68,68,0.8)" : "rgba(34,197,94,0.8)",
    }));

    histogramSeries.setData(histogramData as any);

    // 零线
    const zeroSeries = chart.addLineSeries({
      color: "#94a3b8",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      lastValueVisible: false,
      priceLineVisible: false,
    });
    zeroSeries.setData(
      pnlData.map((_, i) => ({
        time: (i + 1) as unknown as any,
        value: 0,
      })) as any
    );

    chartRef.current = chart;
    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [pnlData, height]);

  const totalPnl = pnlData.reduce((sum, d) => sum + d.pnl, 0);
  const totalMarketValue = positions.reduce(
    (sum, p) => sum + (p.market_value || 0),
    0
  );
  const totalEquity = currentCash + totalMarketValue;
  const totalReturn = ((totalEquity - initialCash) / initialCash) * 100;

  return (
    <div className="space-y-4">
      {/* 总体盈亏概览 */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
          <div className="text-xs text-slate-500">总资产</div>
          <div className="text-lg font-bold">
            ¥{totalEquity.toLocaleString()}
          </div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
          <div className="text-xs text-slate-500">持仓盈亏</div>
          <div
            className={`text-lg font-bold ${
              totalPnl >= 0 ? "text-red-600" : "text-green-600"
            }`}
          >
            {totalPnl >= 0 ? "+" : ""}¥{totalPnl.toLocaleString()}
          </div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
          <div className="text-xs text-slate-500">总收益率</div>
          <div
            className={`text-lg font-bold ${
              totalReturn >= 0 ? "text-red-600" : "text-green-600"
            }`}
          >
            {totalReturn >= 0 ? "+" : ""}
            {totalReturn.toFixed(2)}%
          </div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
          <div className="text-xs text-slate-500">可用现金</div>
          <div className="text-lg font-bold">
            ¥{currentCash.toLocaleString()}
          </div>
        </div>
      </div>

      {/* 各持仓盈亏柱状图 */}
      {pnlData.length > 0 && (
        <div>
          <div className="flex items-center gap-4 mb-2">
            <h4 className="text-sm font-medium">持仓盈亏分布</h4>
            <div className="flex gap-3 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-red-500 rounded-sm" /> 盈利
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 bg-green-500 rounded-sm" /> 亏损
              </span>
            </div>
          </div>
          <div ref={chartContainerRef} className="w-full" />

          {/* 详细列表 */}
          <div className="mt-3 space-y-1">
            {pnlData.map((d) => (
              <div
                key={d.symbol}
                className="flex items-center justify-between py-1.5 px-3 text-xs bg-slate-50 dark:bg-slate-800 rounded"
              >
                <span className="font-medium">{d.symbol}</span>
                <div className="flex items-center gap-4">
                  <span
                    className={
                      d.pnl >= 0 ? "text-red-600" : "text-green-600"
                    }
                  >
                    {d.pnl >= 0 ? "+" : ""}¥{d.pnl.toLocaleString()}
                  </span>
                  <span
                    className={
                      d.pnlPct >= 0 ? "text-red-600" : "text-green-600"
                    }
                  >
                    {d.pnlPct >= 0 ? "+" : ""}
                    {d.pnlPct.toFixed(2)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {pnlData.length === 0 && (
        <div className="text-center text-slate-400 py-8 text-sm">
          暂无持仓数据
        </div>
      )}
    </div>
  );
}

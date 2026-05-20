"use client";

import { useEffect, useRef, useCallback } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  LineData,
  HistogramData,
  CrosshairMode,
} from "lightweight-charts";

interface KLineData {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface TradeSignal {
  trade_date: string;
  action: "buy" | "sell";
  price: number;
}

interface Props {
  data: KLineData[];
  signals?: TradeSignal[];
  showMA?: boolean;
  maPeriods?: number[];
  height?: number;
}

const MA_COLORS = ["#f59e0b", "#3b82f6", "#8b5cf6", "#ec4899"];

export default function KLineChart({
  data,
  signals = [],
  showMA = true,
  maPeriods = [5, 20, 60],
  height = 500,
}: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const maRefs = useRef<ISeriesApi<"Line">[]>([]);

  // 计算均线
  const calcMA = useCallback(
    (period: number): LineData[] => {
      const result: LineData[] = [];
      for (let i = period - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = 0; j < period; j++) {
          sum += data[i - j].close;
        }
        result.push({
          time: data[i].trade_date.replace(/-/g, "-") as any,
          value: sum / period,
        });
      }
      return result;
    },
    [data]
  );

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#f1f5f9" },
        horzLines: { color: "#f1f5f9" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { labelBackgroundColor: "#3b82f6" },
        horzLine: { labelBackgroundColor: "#3b82f6" },
      },
      rightPriceScale: {
        borderColor: "#e2e8f0",
        scaleMargins: { top: 0.1, bottom: 0.25 },
      },
      timeScale: {
        borderColor: "#e2e8f0",
        timeVisible: false,
      },
      height,
    });

    // K 线主图
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: "#ef4444",
      downColor: "#22c55e",
      borderUpColor: "#ef4444",
      borderDownColor: "#22c55e",
      wickUpColor: "#ef4444",
      wickDownColor: "#22c55e",
    });

    // 成交量图
    const volumeSeries = chart.addHistogramSeries({
      color: "#94a3b8",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    // 均线
    const maSeries: ISeriesApi<"Line">[] = [];
    if (showMA) {
      maPeriods.forEach((period, idx) => {
        const ma = chart.addLineSeries({
          color: MA_COLORS[idx % MA_COLORS.length],
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          title: `MA${period}`,
        });
        maSeries.push(ma);
      });
    }

    chartRef.current = chart;
    candlestickRef.current = candlestickSeries;
    volumeRef.current = volumeSeries;
    maRefs.current = maSeries;

    // 响应式
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [height, showMA, maPeriods]);

  // 更新数据
  useEffect(() => {
    if (!candlestickRef.current || !volumeRef.current || data.length === 0)
      return;

    const candleData: CandlestickData[] = data.map((item) => ({
      time: item.trade_date.replace(/-/g, "-") as any,
      open: Number(item.open),
      high: Number(item.high),
      low: Number(item.low),
      close: Number(item.close),
    }));

    const volumeData: HistogramData[] = data.map((item) => ({
      time: item.trade_date.replace(/-/g, "-") as any,
      value: Number(item.volume),
      color:
        Number(item.close) >= Number(item.open)
          ? "rgba(239,68,68,0.5)"
          : "rgba(34,197,94,0.5)",
    }));

    candlestickRef.current.setData(candleData);
    volumeRef.current.setData(volumeData);

    // 更新均线
    if (showMA && maRefs.current.length > 0) {
      maPeriods.forEach((period, idx) => {
        if (maRefs.current[idx]) {
          maRefs.current[idx].setData(calcMA(period));
        }
      });
    }

    // 添加买卖信号标记
    if (signals.length > 0 && candlestickRef.current) {
      const markers = signals
        .map((s) => ({
          time: s.trade_date.replace(/-/g, "-") as any,
          position: s.action === "buy" ? "belowBar" as const : "aboveBar" as const,
          color: s.action === "buy" ? "#ef4444" : "#22c55e",
          shape: s.action === "buy" ? "arrowUp" as const : "arrowDown" as const,
          text: s.action === "buy" ? "B" : "S",
        }))
        .sort((a, b) => (a.time as string).localeCompare(b.time as string));

      candlestickRef.current.setMarkers(markers);
    }

    chartRef.current?.timeScale().fitContent();
  }, [data, signals, showMA, maPeriods, calcMA]);

  return (
    <div className="relative">
      {/* 图例 */}
      {showMA && (
        <div className="absolute top-2 left-2 z-10 flex gap-3 text-xs">
          {maPeriods.map((period, idx) => (
            <span
              key={period}
              style={{ color: MA_COLORS[idx % MA_COLORS.length] }}
            >
              MA{period}
            </span>
          ))}
        </div>
      )}
      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
}

"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
  LineData,
} from "lightweight-charts";

interface EquityPoint {
  date: string;
  equity: number;
}

interface BenchmarkPoint {
  date: string;
  equity: number;
}

interface Props {
  data: EquityPoint[];
  benchmark?: BenchmarkPoint[];
  height?: number;
}

export default function EquityChart({
  data,
  benchmark = [],
  height = 300,
}: Props) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

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
        mode: 0,
      },
      rightPriceScale: {
        borderColor: "#e2e8f0",
      },
      timeScale: {
        borderColor: "#e2e8f0",
        timeVisible: false,
      },
      height,
    });

    // 策略曲线
    const strategySeries = chart.addLineSeries({
      color: "#3b82f6",
      lineWidth: 2,
      title: "策略",
    });

    const strategyData: LineData[] = data.map((d) => ({
      time: d.date.replace(/-/g, "-") as any,
      value: d.equity,
    }));
    strategySeries.setData(strategyData);

    // 基准曲线
    if (benchmark.length > 0) {
      const benchmarkSeries = chart.addLineSeries({
        color: "#94a3b8",
        lineWidth: 1,
        lineStyle: 2,
        title: "基准",
      });

      const benchmarkData: LineData[] = benchmark.map((d) => ({
        time: d.date.replace(/-/g, "-") as any,
        value: d.equity,
      }));
      benchmarkSeries.setData(benchmarkData);
    }

    chartRef.current = chart;

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

    chart.timeScale().fitContent();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, benchmark, height]);

  return <div ref={chartContainerRef} className="w-full" />;
}

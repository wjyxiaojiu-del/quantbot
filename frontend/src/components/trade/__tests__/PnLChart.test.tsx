import { render, screen } from "@testing-library/react";
import PnLChart from "../PnLChart";

jest.mock("lightweight-charts", () => ({
  createChart: jest.fn(() => ({
    addHistogramSeries: jest.fn(() => ({ setData: jest.fn() })),
    addLineSeries: jest.fn(() => ({ setData: jest.fn() })),
    timeScale: jest.fn(() => ({ fitContent: jest.fn() })),
    remove: jest.fn(),
  })),
  ColorType: { Solid: "solid" },
  LineStyle: { Dashed: 2 },
}));

describe("PnLChart", () => {
  const baseProps = {
    positions: [
      { symbol: "000001.SZ", quantity: 1000, avg_cost: 15.0, market_value: 16000, current_price: 16.0 },
      { symbol: "600519.SH", quantity: 100, avg_cost: 1800.0, market_value: 175000, current_price: 1750.0 },
    ],
    initialCash: 1000000,
    currentCash: 809000,
  };

  it("renders summary cards", () => {
    render(<PnLChart {...baseProps} />);
    expect(screen.getByText("总资产")).toBeInTheDocument();
    expect(screen.getByText("持仓盈亏")).toBeInTheDocument();
    expect(screen.getByText("总收益率")).toBeInTheDocument();
    expect(screen.getByText("可用现金")).toBeInTheDocument();
  });

  it("calculates total equity correctly", () => {
    render(<PnLChart {...baseProps} />);
    expect(screen.getByText("¥1,000,000")).toBeInTheDocument();
  });

  it("shows profit for positive PnL", () => {
    const props = {
      ...baseProps,
      positions: [
        { symbol: "000001.SZ", quantity: 1000, avg_cost: 10.0, market_value: 15000, current_price: 15.0 },
      ],
    };
    render(<PnLChart {...props} />);
    // pnl = (15 - 10) * 1000 = 5000 — appears in both summary and detail
    const matches = screen.getAllByText(/5,000/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("shows loss for negative PnL", () => {
    const props = {
      ...baseProps,
      positions: [
        { symbol: "000001.SZ", quantity: 1000, avg_cost: 20.0, market_value: 15000, current_price: 15.0 },
      ],
    };
    render(<PnLChart {...props} />);
    const matches = screen.getAllByText(/5,000/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders position list", () => {
    render(<PnLChart {...baseProps} />);
    expect(screen.getByText("000001.SZ")).toBeInTheDocument();
    expect(screen.getByText("600519.SH")).toBeInTheDocument();
  });

  it("shows empty state when no positions", () => {
    render(<PnLChart {...baseProps} positions={[]} />);
    expect(screen.getByText("暂无持仓数据")).toBeInTheDocument();
  });

  it("renders profit/loss legend", () => {
    render(<PnLChart {...baseProps} />);
    expect(screen.getByText("盈利")).toBeInTheDocument();
    expect(screen.getByText("亏损")).toBeInTheDocument();
  });

  it("calculates return percentage", () => {
    const props = {
      ...baseProps,
      initialCash: 1000000,
      currentCash: 500000,
      positions: [
        { symbol: "X", quantity: 100, avg_cost: 100, market_value: 600000, current_price: 120 },
      ],
    };
    render(<PnLChart {...props} />);
    expect(screen.getByText("+10.00%")).toBeInTheDocument();
  });
});

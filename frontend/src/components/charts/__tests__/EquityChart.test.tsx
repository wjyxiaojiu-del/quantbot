import { render } from "@testing-library/react";
import EquityChart from "../EquityChart";

// lightweight-charts 需要 canvas，在 jsdom 中不可用，mock 掉
jest.mock("lightweight-charts", () => ({
  createChart: jest.fn(() => ({
    addLineSeries: jest.fn(() => ({
      setData: jest.fn(),
    })),
    timeScale: jest.fn(() => ({
      fitContent: jest.fn(),
    })),
    remove: jest.fn(),
    applyOptions: jest.fn(),
  })),
  ColorType: { Solid: "solid" },
}));

describe("EquityChart", () => {
  it("renders container div", () => {
    const { container } = render(
      <EquityChart data={[{ date: "2026-01-01", equity: 100000 }]} />
    );
    expect(container.querySelector("div")).toBeInTheDocument();
  });

  it("renders with empty data", () => {
    const { container } = render(<EquityChart data={[]} />);
    expect(container.querySelector("div")).toBeInTheDocument();
  });

  it("renders with benchmark data", () => {
    const { container } = render(
      <EquityChart
        data={[{ date: "2026-01-01", equity: 100000 }]}
        benchmark={[{ date: "2026-01-01", equity: 100000 }]}
      />
    );
    expect(container.querySelector("div")).toBeInTheDocument();
  });

  it("accepts custom height", () => {
    const { container } = render(
      <EquityChart data={[{ date: "2026-01-01", equity: 100000 }]} height={500} />
    );
    expect(container.querySelector("div")).toBeInTheDocument();
  });
});

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import Home from "../page";

// Mock next/link
jest.mock("next/link", () => {
  const MockLink = ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
  MockLink.displayName = "MockLink";
  return MockLink;
});

// Mock api modules
jest.mock("@/lib/api", () => ({
  dashboardApi: { get: jest.fn() },
  marketApi: { syncStocks: jest.fn() },
}));

import { dashboardApi, marketApi } from "@/lib/api";
const mockedDashboard = dashboardApi as any;
const mockedMarket = marketApi as any;

const mockDashboardData = {
  data: {
    market: {
      stock_count: 5000,
      kline_count: 1000000,
      latest_synced: [
        { symbol: "000001.SZ", date: "2026-05-19" },
        { symbol: "600519.SH", date: "2026-05-19" },
      ],
    },
    strategy: { total: 5, active: 3 },
    backtest: { total: 10, best_return: 25.5, best_name: "均线策略" },
    portfolio: {
      count: 2,
      total_cash: 500000,
      total_equity: 800000,
      items: [
        { id: "1", name: "主策略", equity: 600000, return_pct: 12.5 },
        { id: "2", name: "测试", equity: 200000, return_pct: -3.2 },
      ],
    },
    recent_orders: [
      { id: "o1", symbol: "000001.SZ", side: "buy", price: 15.5, quantity: 1000, created_at: "2026-05-19" },
    ],
  },
};

describe("Home page (Dashboard)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Storage.prototype.getItem = jest.fn((key) => key === "token" ? "fake-token" : null);
  });

  it("shows loading spinner initially", () => {
    mockedDashboard.get.mockImplementation(() => new Promise(() => {}));
    render(<Home />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    const spinner = document.querySelector(".animate-spin");
    expect(spinner).toBeInTheDocument();
  });

  it("shows login prompt when not authenticated", () => {
    Storage.prototype.getItem = jest.fn(() => null);
    render(<Home />);
    expect(screen.getByText("请先登录后查看 Dashboard")).toBeInTheDocument();
    expect(screen.getByText("去登录")).toBeInTheDocument();
  });

  it("renders dashboard data on success", async () => {
    mockedDashboard.get.mockResolvedValueOnce(mockDashboardData);
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText("5,000")).toBeInTheDocument();
    });
    expect(screen.getByText("1,000,000")).toBeInTheDocument();
    expect(screen.getByText("5 / 3 活跃")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("最佳 25.5%")).toBeInTheDocument();
  });

  it("renders portfolio section", async () => {
    mockedDashboard.get.mockResolvedValueOnce(mockDashboardData);
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText("800,000")).toBeInTheDocument();
    });
    expect(screen.getByText("500,000")).toBeInTheDocument();
    expect(screen.getByText("主策略")).toBeInTheDocument();
    expect(screen.getByText("+12.5%")).toBeInTheDocument();
    expect(screen.getByText("-3.2%")).toBeInTheDocument();
  });

  it("renders recent orders", async () => {
    mockedDashboard.get.mockResolvedValueOnce(mockDashboardData);
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText("买")).toBeInTheDocument();
    });
    // symbol and quantity are in child elements — use textContent match
    expect(screen.getByText("1000股 @15.5")).toBeInTheDocument();
  });

  it("shows error state on API failure", async () => {
    mockedDashboard.get.mockRejectedValueOnce({ response: { status: 500 } });
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText("加载失败，请检查后端是否运行")).toBeInTheDocument();
    });
    expect(screen.getByText("重试")).toBeInTheDocument();
  });

  it("renders quick links", async () => {
    mockedDashboard.get.mockResolvedValueOnce(mockDashboardData);
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText("行情中心")).toBeInTheDocument();
    });
    expect(screen.getByText("策略管理")).toBeInTheDocument();
    expect(screen.getByText("策略回测")).toBeInTheDocument();
    expect(screen.getByText("模拟交易")).toBeInTheDocument();
  });

  it("handles sync button click", async () => {
    mockedDashboard.get.mockResolvedValueOnce(mockDashboardData);
    mockedMarket.syncStocks.mockResolvedValueOnce({ data: { message: "同步成功" } });
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText("同步股票列表")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("同步股票列表"));

    await waitFor(() => {
      expect(screen.getByText("同步成功")).toBeInTheDocument();
    });
  });

  it("shows latest synced stocks", async () => {
    mockedDashboard.get.mockResolvedValueOnce(mockDashboardData);
    render(<Home />);

    await waitFor(() => {
      expect(screen.getByText("最近同步")).toBeInTheDocument();
    });
    // Stock symbols are in monospace font spans — check parent container
    const syncSection = screen.getByText("最近同步").closest("div");
    expect(syncSection?.textContent).toContain("000001.SZ");
    expect(syncSection?.textContent).toContain("600519.SH");
  });
});

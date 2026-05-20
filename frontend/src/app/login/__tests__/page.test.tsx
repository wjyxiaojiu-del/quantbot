import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "../page";

// Mock next/navigation
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock next/link
jest.mock("next/link", () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
});

// Mock api
jest.mock("@/lib/api", () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

import api from "@/lib/api";
const mockedApi = api as jest.Mocked<typeof api>;

describe("LoginPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Storage.prototype.setItem = jest.fn();
  });

  it("renders login form by default", () => {
    render(<LoginPage />);
    expect(screen.getByText("QuantBot")).toBeInTheDocument();
    expect(screen.getByText("登录你的账户")).toBeInTheDocument();
    expect(screen.getByText("登录")).toBeInTheDocument();
  });

  it("switches to register mode", () => {
    render(<LoginPage />);
    fireEvent.click(screen.getByText("注册"));
    expect(screen.getByText("创建新账户")).toBeInTheDocument();
    expect(screen.getByText("邮箱")).toBeInTheDocument();
  });

  it("shows username and password fields", () => {
    render(<LoginPage />);
    expect(screen.getByPlaceholderText("输入用户名")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("输入密码")).toBeInTheDocument();
  });

  it("calls login API on submit", async () => {
    mockedApi.post.mockResolvedValueOnce({ data: { access_token: "tok123" } });
    render(<LoginPage />);

    fireEvent.change(screen.getByPlaceholderText("输入用户名"), {
      target: { value: "testuser" },
    });
    fireEvent.change(screen.getByPlaceholderText("输入密码"), {
      target: { value: "pass123" },
    });
    fireEvent.click(screen.getByText("登录"));

    await waitFor(() => {
      expect(mockedApi.post).toHaveBeenCalledWith("/auth/login", {
        username: "testuser",
        password: "pass123",
      });
    });
  });

  it("displays error on API failure", async () => {
    mockedApi.post.mockRejectedValueOnce({
      response: { data: { detail: "用户名或密码错误" } },
    });
    render(<LoginPage />);

    fireEvent.change(screen.getByPlaceholderText("输入用户名"), {
      target: { value: "bad" },
    });
    fireEvent.change(screen.getByPlaceholderText("输入密码"), {
      target: { value: "bad" },
    });
    fireEvent.click(screen.getByText("登录"));

    await waitFor(() => {
      expect(screen.getByText("用户名或密码错误")).toBeInTheDocument();
    });
  });

  it("shows loading state during submit", async () => {
    mockedApi.post.mockImplementation(() => new Promise(() => {})); // never resolves
    render(<LoginPage />);

    fireEvent.change(screen.getByPlaceholderText("输入用户名"), {
      target: { value: "u" },
    });
    fireEvent.change(screen.getByPlaceholderText("输入密码"), {
      target: { value: "p" },
    });
    fireEvent.click(screen.getByText("登录"));

    await waitFor(() => {
      expect(screen.getByText("处理中...")).toBeInTheDocument();
    });
  });

  it("has link back to home", () => {
    render(<LoginPage />);
    expect(screen.getByText("← 返回首页")).toHaveAttribute("href", "/");
  });
});

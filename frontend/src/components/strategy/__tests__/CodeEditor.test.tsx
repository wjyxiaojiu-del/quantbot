import { render, screen, fireEvent } from "@testing-library/react";
import CodeEditor from "../CodeEditor";

describe("CodeEditor", () => {
  it("renders with initial value", () => {
    render(<CodeEditor value="print('hello')" onChange={() => {}} />);
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveValue("print('hello')");
  });

  it("displays line count in toolbar", () => {
    const value = `line1
line2
line3`;
    render(<CodeEditor value={value} onChange={() => {}} />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("calls onChange when typing", () => {
    const onChange = jest.fn();
    render(<CodeEditor value="" onChange={onChange} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "new code" } });
    expect(onChange).toHaveBeenCalledWith("new code");
  });

  it("shows Python label", () => {
    render(<CodeEditor value="" onChange={() => {}} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  it("toggles snippet panel", () => {
    render(<CodeEditor value="" onChange={() => {}} />);
    const snippetBtn = screen.getByText("代码片段");
    fireEvent.click(snippetBtn);
    expect(screen.getByText("generate signals")).toBeInTheDocument();
  });

  it("renders in readOnly mode", () => {
    render(<CodeEditor value="readonly code" onChange={() => {}} readOnly />);
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveAttribute("readonly");
  });

  it("shows tab hint at bottom", () => {
    render(<CodeEditor value="" onChange={() => {}} />);
    expect(screen.getByText(/Tab 插入缩进/)).toBeInTheDocument();
  });
});

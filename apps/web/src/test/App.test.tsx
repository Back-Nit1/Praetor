import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { ApiError, createClient, type Client } from "../api";

const fixture = createClient("fixture");
const mount = (over: Partial<Client> = {}) => render(<App client={{ ...fixture, ...over }} />);

describe("dashboard (fixture mode)", () => {
  it("shows SIMULATION labeling, five attackers, eight domains and the financial disclaimer", async () => {
    mount();
    await screen.findByRole("region", { name: "Simulated attackers" });
    expect(screen.getByText(/Fictional persona with reserved example data/)).toBeInTheDocument();
    expect(screen.getAllByText(/SIMULATION/).length).toBeGreaterThan(0);
    expect(screen.getByText("FIXTURE MODE (offline)")).toBeInTheDocument();
    const attackers = within(screen.getByRole("region", { name: "Simulated attackers" })).getAllByRole("listitem");
    expect(attackers).toHaveLength(5);
    expect(within(screen.getByRole("region", { name: "Damage by domain" })).getAllByRole("listitem")).toHaveLength(8);
    expect(screen.getAllByText(/not financial advice/).length).toBeGreaterThan(0);
    expect(screen.getByRole("img", { name: /Risk radar/ })).toBeInTheDocument();
  });

  it("never renders credential or free-text inputs", async () => {
    const { container } = mount();
    await screen.findByRole("region", { name: "Public digital twin" });
    expect(container.querySelector("input")).toBeNull();
    expect(container.querySelector("textarea")).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("physical path shows severity and defenses, not attack steps", async () => {
    mount();
    await userEvent.click(await screen.findByRole("button", { name: /Physical path/ }));
    const panel = screen.getByRole("region", { name: "Selected attack timeline" });
    expect(within(panel).getByText(/severity and defenses only/)).toBeInTheDocument();
    expect(within(panel).getByText("High")).toBeInTheDocument();
    expect(within(panel).getByText(/Optout · broker_peoplesearch/)).toBeInTheDocument();
    expect(within(panel).queryByText(/Home address exposed/)).toBeNull();
    expect(panel.querySelector("ol")).toBeNull();
  });

  it("pretext template is watermarked SIMULATION and uses placeholders", async () => {
    mount();
    await userEvent.click(await screen.findByRole("button", { name: /Fraud path/ }));
    const fig = screen.getByRole("figure");
    expect(within(fig).getAllByText(/SIMULATION/).length).toBeGreaterThan(0);
    expect(within(fig).getByText(/\{\{FIRST_NAME\}\}/)).toBeInTheDocument();
  });

  it("ledger drawer shows the empty state and closes on Escape", async () => {
    mount();
    await userEvent.click(await screen.findByRole("button", { name: "Ledger" }));
    const dlg = await screen.findByRole("dialog", { name: "Data-flow ledger" });
    expect(await within(dlg).findByText("No outbound calls recorded.")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("empty and error states", () => {
  it("renders every empty state when nothing is found", async () => {
    mount({
      attack: async () => ({ paths: [], findings: [] }),
      remediate: async () => ({ fixes: [], paths_before: 0, paths_after: 0, method: "greedy", residual_notes: "" }),
      league: async () => [],
    });
    expect(await screen.findByText("No fixes needed — no attack paths were found.")).toBeInTheDocument();
    expect(screen.getAllByText("Failed — no viable path")).toHaveLength(5);
    expect(screen.getByText(/No attack path selected/)).toBeInTheDocument();
    expect(screen.getByText(/No league rounds yet/)).toBeInTheDocument();
    expect(screen.getByText("No financial exposure found")).toBeInTheDocument();
  });

  it("shows no personas empty state", async () => {
    mount({ personas: async () => [] });
    expect(await screen.findByText("No synthetic personas available.")).toBeInTheDocument();
  });

  it("shows loading, then an error with retry and no substituted data", async () => {
    const twin = vi.fn().mockRejectedValueOnce(new ApiError(502, "upstream down")).mockImplementation(fixture.twin);
    mount({ twin });
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("upstream down");
    expect(screen.queryByRole("region", { name: "Public digital twin" })).toBeNull();
    await userEvent.click(within(alert).getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("region", { name: "Public digital twin" })).toBeInTheDocument();
    expect(twin).toHaveBeenCalledTimes(2);
  });

  it("ledger failure is shown in the drawer", async () => {
    mount({ ledger: async () => { throw new ApiError(500, "ledger offline"); } });
    await userEvent.click(await screen.findByRole("button", { name: "Ledger" }));
    expect(await screen.findByText("ledger offline")).toBeInTheDocument();
  });
});
